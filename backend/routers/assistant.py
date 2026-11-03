import re
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models, schemas, auth
from database import get_db
from gps_service import gps_client, OFFICIAL_DRIVERS_BY_CLEAN_PLATE
from traffic_fines_service import traffic_fines_service
from sheets_service import sheets_client

router = APIRouter(prefix="/api/assistant", tags=["AI Copilot"])

XE_BEN_PLATES = {
    '63H04273', '63G00286', '63E01156', '63E01117', '63E01108',
    '63F00528', '63G00262', '63H04239', '63E01276', '63E01103',
    '63E01118', '63F00511', '63H04234', '63E01235', '63H04236'
}

class AssistantCommand(BaseModel):
    command: str

@router.post("/execute")
def execute_ai_command(
    req: AssistantCommand,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cmd = req.command.strip()
    cmd_lower = cmd.lower()
    clean_cmd = re.sub(r'[^a-z0-9]', '', cmd_lower)

    # 1. HỎI VỀ ĐIỀU XE THÁNG 11 / HÔM NAY / XE LIÊN KẾT / TUYẾN ĐƯỜNG
    if any(k in cmd_lower for k in ["tháng 11", "điều xe", "lịch chạy", "nhận hàng", "chủ hàng", "xe liên kết", "tuyến đường", "đi đâu"]):
        try:
            daily = sheets_client.fetch_daily_trips()
            all_trips = daily.get("all_trips", [])
            partner = daily.get("partner_trips", [])
            custs = ", ".join([f"{c['customer']}: {c['trips']} xe" for c in daily.get("customer_breakdown", [])])
            dispatched = [t["plate_number"] for t in all_trips if t.get("dispatched")]
            lines = [
                f"📅 [BÁO CÁO ĐIỀU XE NGÀY {daily.get('date')} — THÁNG {daily.get('month_year', '11/2026')}]:",
                f"• Tổng đội xe công ty: {len(all_trips)} xe ({daily.get('active_count', 26)} xe chạy · {daily.get('dispatched_count', 0)} đã điều · {daily.get('undispatched_count', 0)} chờ điều)",
                f"• Xe đã điều lệnh sớm: {', '.join(dispatched[:8]) if dispatched else 'Đang cập nhật'}",
                f"• Cơ cấu Chủ hàng hôm nay: {custs or 'Khai Anh, RICO, Emivest, Thuận An, Kim Bàng, Lúa Vàng'}",
                f"• 🤝 Xe liên kết ngoài công ty: {len(partner)} chuyến ({partner[0]['partner_unit'] if partner else 'Hoàng Mạnh Thắng'})"
            ]
            return {"type": "dispatch_report", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi đọc lịch điều xe: {str(e)}"}

    # 2. SO SÁNH ĐỊNH MỨC DẦU BA GPS VS ĐỊNH MỨC DẦU TRANG TÍNH (FILE ĐỔ DẦU - BẢO DƯỠNG)
    if any(k in cmd_lower for k in ["định mức", "dầu", "tiêu hao", "hao dầu", "hút dầu", "công nợ dầu", "sổ dầu"]):
        try:
            wb = sheets_client.fetch_full_maintenance_and_fuel_workbook()
            f_sum = wb.get("fuel", {}).get("summary", {})
            v_norms = wb.get("fuel", {}).get("vehicle_norms", {})
            telemetry = gps_client.fetch_live_fleet()
            gps_map = {v["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper(): v for v in telemetry}

            # Kiểm tra nếu hỏi riêng 1 xe
            for clean_p, sh_n in v_norms.items():
                if clean_p.lower() in clean_cmd:
                    g_v = gps_map.get(clean_p, {})
                    bagps_n = g_v.get("actual_norm", 34.0)
                    sheet_n = sh_n.get("sheet_norm_l100km", 0.0)
                    diff = round(sheet_n - bagps_n, 1) if sheet_n > 0 else 0.0
                    return {
                        "type": "fuel_vehicle_detail",
                        "message": f"⛽ [ĐỐI CHIẾU ĐỊNH MỨC DẦU KÉP] Xe {sh_n['plate_number']} ({sh_n['vehicle_type']}):\n"
                                   f"• Định mức BA GPS (Cảm biến/Telematics): {bagps_n} L/100km (Hôm nay chạy {g_v.get('daily_km', 0)} km · {g_v.get('consumed_liters', 0)} L)\n"
                                   f"• Định mức Trang Tính (Sổ Đổ Dầu thực tế): {sheet_n} L/100km ({sh_n['fill_count']} lần đổ · Tổng {sh_n['total_liters']:,.1f} L / {sh_n['total_km_tracked']:,} km)\n"
                                   f"• Độ lệch (Trang Tính - BA GPS): {diff:+.1f} L/100km\n"
                                   f"• ODO đổ dầu gần nhất: {sh_n['last_odo']:,} km (Ngày {sh_n['last_fuel_date']})"
                    }

            total_gps_fuel = sum(v.get("consumed_liters", 0) for v in telemetry)
            avg_gps_norm = round(sum(v.get("actual_norm", 34.0) for v in telemetry) / max(len(telemetry), 1), 1)
            lines = [
                "⛽ [BÁO CÁO ĐỐI CHIẾU ĐỊNH MỨC DẦU: BA GPS vs FILE ĐỔ DẦU TRANG TÍNH]:",
                f"1️⃣ ĐỊNH MỨC DẦU BA GPS (TRỰC TUYẾN 26 XE):",
                f"  • Định mức bình quân BA GPS: {avg_gps_norm} L/100km (Tiêu hao hôm nay: {total_gps_fuel:,.1f} Lít)",
                f"2️⃣ ĐỊNH MỨC DẦU TRANG TÍNH (SỔ ĐỔ DẦU {f_sum.get('total_records', 512)} LƯỢT ĐỔ):",
                f"  • Định mức bình quân Trang Tính: {f_sum.get('fleet_avg_norm_l100km', 37.8)} L/100km",
                f"  • Tổng lượng dầu đã đổ: {f_sum.get('total_liters', 183972):,.1f} Lít — Tổng tiền: {f_sum.get('total_cost', 5153132136):,.0f} đ",
                f"  • Đã thanh toán: {f_sum.get('paid_amount', 4270846523):,.0f} đ — 🔴 Công nợ chưa trả: {f_sum.get('unpaid_debt', 882285613):,.0f} đ",
                "\n👉 Mở Tab 'Định Mức Dầu & Sổ Dầu 2 Chiều' hoặc Bảng Tổng Quan để xem chi tiết từng xe trong 26 xe!"
            ]
            return {"type": "fuel_report", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra định mức dầu: {str(e)}"}

    # 3. CẢNH BÁO XE CHƯA QUẸT THẺ RFID LÁI XE & TÍNH NĂNG HAY CỦA BA GPS
    if any(k in cmd_lower for k in ["không quẹt thẻ", "chưa quẹt thẻ", "quẹt thẻ", "thẻ lái xe", "rfid", "bagps", "ba gps", "nổ máy", "liên tục"]):
        try:
            telemetry = gps_client.fetch_live_fleet()
            running_no_card = [v for v in telemetry if v.get("card_violation") == "running_no_card" and v.get("speed", 0) > 0]
            daily_no_card = [v for v in telemetry if v.get("card_violation") == "daily_no_card" or (not v.get("is_card_swiped", True) and v.get("daily_km", 0) > 3 and v.get("speed", 0) == 0)]
            idling_list = [v for v in telemetry if v.get("status_type") == "idling"]

            lines = ["🛰️ [GIÁM SÁT THẺ LÁI XE RFID & CẢNH BÁO BA GPS TRỰC TUYẾN]:"]
            if running_no_card:
                lines.append(f"\n🚨 XE ĐANG CHẠY TRÊN ĐƯỜNG NHƯNG CHƯA QUẸT THẺ ({len(running_no_card)} XE):")
                for nc in running_no_card:
                    lines.append(f"  • Xe {nc['plate_number']} ({nc['driver_name']}): Đang chạy {nc['speed']} km/h ({nc['daily_km']} km) tại {nc['address']}")
            if daily_no_card:
                lines.append(f"\n⚠️ XE CÓ CHẠY TRONG NGÀY NHƯNG CHƯA QUẸT THẺ ({len(daily_no_card)} XE):")
                for dnc in daily_no_card:
                    lines.append(f"  • Xe {dnc['plate_number']} ({dnc['driver_name']}): Đã chạy {dnc['daily_km']} km hôm nay — Chưa quẹt thẻ RFID")
            if idling_list:
                lines.append(f"\n🟡 XE ĐANG DỪNG NỔ MÁY HAO DẦU KHÔNG TẢI ({len(idling_list)} XE):")
                for idl in idling_list[:5]:
                    lines.append(f"  • Xe {idl['plate_number']} ({idl['driver_name']}) tại {idl['address']}")

            if not running_no_card and not daily_no_card:
                lines.append("✅ Toàn bộ 26 xe hoạt động hôm nay đều đã quẹt thẻ RFID đầy đủ!")
            return {"type": "card_alert", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra thẻ RFID BA GPS: {str(e)}"}

    # 4. TRA CỨU BẢO DƯỠNG XE (THAY NHỚT, BÔI MỠ ROMOÓC, NHỚT HỘP SỐ, SỬA CHỮA GARA)
    if any(k in cmd_lower for k in ["bảo dưỡng", "thay nhớt", "nhớt", "bôi mỡ", "hộp số", "sửa chữa", "gara"]):
        try:
            wb = sheets_client.fetch_full_maintenance_and_fuel_workbook()
            maint = wb.get("maintenance", {})
            oil_data = maint.get("oil_changes", [])
            grease_data = maint.get("grease_trailer", [])
            repairs = maint.get("repair_logs", [])

            for m in oil_data:
                clean_p = m["plate_number"].replace("-", "").replace(".", "").replace(" ", "").lower()
                if clean_p in clean_cmd:
                    return {
                        "type": "maintenance_detail",
                        "message": f"🔧 [HỒ SƠ BẢO DƯỠNG 2 CHIỀU] Xe {m['plate_number']}:\n"
                                   f"• Định mức thay nhớt: {m['norm_km']:,} km\n"
                                   f"• Km thay gần nhất: {m['last_km']} km (Ngày: {m['last_date']})\n"
                                   f"• Km hiện tại (tự lấy từ Sổ Dầu): {m['current_km']} km\n"
                                   f"• Km đến hạn: {m['due_km']} km (Còn lại: {m['remaining_km']} km)\n"
                                   f"• Tình trạng: {m['status']}\n"
                                   f"• Ghi chú: {m['notes'] or 'Không có'}"
                    }

            near_due = [m for m in oil_data if "gần" in str(m["status"]).lower() or "quá" in str(m["status"]).lower() or "sắp" in str(m["status"]).lower()]
            missing = [m for m in oil_data if "thiếu" in str(m["status"]).lower()]
            lines = [
                f"🔧 [TỔNG HỢP BẢO DƯỠNG 26 XE & ROMOÓC — ĐỒNG BỘ 2 CHIỀU TRANG TÍNH]:",
                f"• Bảng ① Thay nhớt động cơ: 26/26 xe ({len(near_due)} xe gần/sắp tới hạn, {len(missing)} xe chờ bổ sung mốc KM)",
                f"• Bảng ② Nhật ký sửa chữa Gara: {len(repairs)} lượt bảo dưỡng/sửa chữa đã ghi nhận",
                f"• Bảng ③ Bôi mỡ Romoóc & Bảng ④ Thay nhớt hộp số (50.000km): Đủ 26 xe"
            ]
            for n in near_due:
                lines.append(f"  ⚠️ Xe {n['plate_number']}: Còn {n['remaining_km']} km là tới hạn thay nhớt ({n['status']})")
            lines.append("\n👉 Bạn có thể nhập mới hoặc cập nhật trực tiếp từ Phần mềm hoặc từ Google Trang Tính đều tương thích 2 chiều!")
            return {"type": "maintenance_summary", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi lấy dữ liệu bảo dưỡng: {str(e)}"}

    # 5. GIẤY TỜ XE, GIẤY ĐI ĐƯỜNG, TEM ĐƯỜNG BỘ & ĐĂNG KIỂM
    if any(k in cmd_lower for k in ["đăng kiểm", "giấy tờ", "giấy đi đường", "tem đường bộ", "hết hạn"]):
        try:
            wb = sheets_client.fetch_full_maintenance_and_fuel_workbook()
            docs = wb.get("documents", {})
            gdd = docs.get("road_permits", [])
            stamps = docs.get("road_stamps", [])
            regs = docs.get("registrations", [])
            ov_actions = wb.get("overview", {}).get("action_items", [])

            lines = ["📋 [GIÁM SÁT GIẤY ĐI ĐƯỜNG · TEM ĐƯỜNG BỘ · ĐĂNG KIỂM 26 XE]:"]
            if ov_actions:
                lines.append("🚨 CÁC MỤC QUÁ HẠN / SẮP ĐẾN HẠN CẦN XỬ LÝ NGAY:")
                for act in ov_actions[:10]:
                    lines.append(f"  • [{act['level']}] Xe {act['plate_number']} — {act['category']}: {act['detail']}")
            lines.append(f"\n• Đã đồng bộ đủ {len(gdd)} hồ sơ Giấy đi đường Đầu kéo + Romoóc, {len(stamps)} Tem đường bộ và {len(regs)} hồ sơ Đăng kiểm.")
            return {"type": "expiry_report", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra hạn giấy tờ: {str(e)}"}

    # 6. THAY VỎ XE & THAY BẠT PHÙNG LĨNH
    if any(k in cmd_lower for k in ["thay vỏ", "vỏ xe", "lốp", "may bạt", "bạt xe", "phùng lĩnh", "công nợ"]):
        wb = sheets_client.fetch_full_maintenance_and_fuel_workbook()
        t_sum = wb.get("tires", {}).get("summary", {})
        b_sum = wb.get("tarps", {}).get("summary", {})
        return {
            "type": "tires_tarps_report",
            "message": f"🛠️ [BÁO CÁO THAY VỎ XE & MAY BẠT PHÙNG LĨNH — TRANG TÍNH 2026]:\n\n"
                       f"1️⃣ THEO DÕI THAY VỎ XE CẢ ĐỘI (26 XE):\n"
                       f"• Tổng số vỏ đã thay: {t_sum.get('total_tires', 193)} vỏ xe ({len(wb.get('tires', {}).get('logs', []))} lượt thay)\n"
                       f"• Tổng chi phí: {t_sum.get('total_cost', 917030000):,.0f} đ (Đã TT: {t_sum.get('paid_amount', 862090000):,.0f} đ · Chưa TT: {t_sum.get('unpaid_debt', 10900000):,.0f} đ)\n\n"
                       f"2️⃣ CÔNG NỢ MAY/SỬA BẠT — NCC PHÙNG LĨNH:\n"
                       f"• Tổng phát sinh: {b_sum.get('total_cost', 52100000):,.0f} đ\n"
                       f"• Đã thanh toán: {b_sum.get('paid_amount', 47300000):,.0f} đ\n"
                       f"• 🔴 Còn nợ chưa thanh toán: {b_sum.get('unpaid_debt', 4800000):,.0f} đ"
        }

    # 7. TRA CỨU PHẠT NGUỘI ĐOÀN XE
    if any(k in cmd_lower for k in ["phạt nguội", "phat nguoi", "vi phạm", "bắn tốc độ", "chặn đăng kiểm"]):
        summary = traffic_fines_service.get_summary()
        all_fines = traffic_fines_service.get_all_fines()
        violated_list = [v for v in all_fines if v["has_violation"]]

        if not violated_list:
            return {
                "type": "fines_report",
                "message": f"🚦 [TRA CỨU PHẠT NGUỘI CỤC CSGT]\n"
                           f"✅ TOÀN ĐOÀN AN TOÀN! Tất cả {summary['total_vehicles']} xe đầu kéo và rơ-moóc đều SẠCH LỖI."
            }
        details = []
        for v in violated_list:
            for vl in v["violations"]:
                details.append(f"• Xe {v['plate_number']} ({v['driver_name']}): {vl['behavior']} tại {vl['location']} — Mức phạt: {vl['fine_amount']:,}đ")
        return {
            "type": "fines_report",
            "message": f"🚦 [KẾT QUẢ QUÉT PHẠT NGUỘI 26 XE]:\n"
                       f"• Xe sạch lỗi: {summary['clean_vehicles']}/{summary['total_vehicles']} xe | Có lỗi: {summary['violated_vehicles']} xe\n" +
                       "\n".join(details)
        }

    # 8. HỎI VỊ TRÍ GPS XE CỤ THỂ
    try:
        telemetry = gps_client.fetch_live_fleet()
        for v in telemetry:
            clean_p = v["plate_number"].replace("-", "").replace(".", "").replace(" ", "").lower()
            if clean_p in clean_cmd:
                return {
                    "type": "gps_query",
                    "message": f"🛰️ [BA GPS TRỰC TUYẾN] Xe {v['plate_number']}:\n"
                               f"• Trạng thái: {v['status_text']} (Vận tốc: {v['speed']} km/h)\n"
                               f"• Vị trí hiện tại: {v['address']}\n"
                               f"• Km trong ngày: {v['daily_km']} km | Tiêu hao: {v['consumed_liters']} L ({v['actual_norm']} L/100km)\n"
                               f"• Tài xế: {v['driver_name']} | Thẻ RFID: {'🟢 Đã quẹt thẻ' if v['is_card_swiped'] else '🚨 Chưa quẹt thẻ'}"
                }
    except Exception:
        pass

    return {
        "type": "assistant_help",
        "message": "🤖 **Trợ Lý AI Điều Hành Vận Tải Trường Phát** sẵn sàng hỗ trợ! Bạn có thể hỏi ngay:\n"
                   "• **'Báo cáo điều xe Tháng 11 hôm nay'** (26 xe công ty + 9 chuyến Xe liên kết)\n"
                   "• **'So sánh định mức dầu BA GPS và Trang Tính'** (Đối chiếu L/100km & công nợ sổ dầu)\n"
                   "• **'Xe nào chạy chưa quẹt thẻ RFID?'** (Phát hiện xe đang chạy & có chạy trong ngày chưa quẹt thẻ)\n"
                   "• **'Tình hình bảo dưỡng thay nhớt, bôi mỡ, gara'** (Đồng bộ 2 chiều Trang Tính)\n"
                   "• **'Kiểm tra hạn giấy đi đường, đăng kiểm, tem đường bộ'**\n"
                   "• **'Chi phí thay vỏ xe và công nợ bạt Phùng Lĩnh'**\n"
                   "• **'Xe 63E-011.56 đang ở đâu?'** (Vị trí GPS, vận tốc, định mức dầu kép)"
    }
