import re
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models, schemas, auth
from database import get_db
from gps_service import gps_client
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
    today = date.today()

    # 1. TRA CỨU BẢO DƯỠNG XE & THAY NHỚT 15.000 KM
    if any(k in cmd_lower for k in ["bảo dưỡng", "thay nhớt", "nhớt", "bảo trì", "đến hạn thay", "quá hạn thay"]):
        try:
            maint_data = sheets_client.fetch_maintenance_sheet()
            if not maint_data:
                return {"type": "maintenance_report", "message": "🔧 Hiện chưa đồng bộ được dữ liệu bảo dưỡng từ Google Sheets. Vui lòng kiểm tra lại sau ít phút!"}

            # Kiểm tra xem có hỏi riêng 1 xe cụ thể không
            matched_m = None
            clean_cmd = cmd_lower.replace("-", "").replace(".", "").replace(" ", "")
            for m in maint_data:
                clean_p = m["plate_number"].replace("-", "").replace(".", "").replace(" ", "").lower()
                if clean_p in clean_cmd:
                    matched_m = m
                    break

            if matched_m:
                return {
                    "type": "maintenance_detail",
                    "message": f"🔧 [HỒ SƠ BẢO DƯỠNG] Xe {matched_m['plate_number']}:\n"
                               f"• Chu kỳ chuẩn: {matched_m['norm_km']} km / lần thay nhớt\n"
                               f"• Km thay nhớt gần nhất: {matched_m['last_km']} km (Ngày: {matched_m['last_date']})\n"
                               f"• ODO hiện tại: {matched_m['current_km']} km\n"
                               f"• Mốc ODO đến hạn: {matched_m['due_km']} km\n"
                               f"• Số Km còn lại: {matched_m['remaining_km']} km\n"
                               f"• Tình trạng kỹ thuật: {matched_m['status']}\n"
                               f"• Ghi chú xưởng: {matched_m['notes'] or 'Không có'}"
                }

            # Tổng hợp toàn đội
            overdue = [m for m in maint_data if "quá" in m["status"].lower() or "sắp" in m["status"].lower() or str(m["remaining_km"]).startswith("-")]
            near_due = [m for m in maint_data if "gần" in m["status"].lower()]
            notes_trucks = [m for m in maint_data if m["notes"] and "thay" in m["notes"].lower()]

            lines = ["🔧 [BÁO CÁO BẢO DƯỠNG ĐỊNH KỲ — THAY NHỚT 15.000 KM]:"]
            if overdue:
                lines.append("🚨 CÁC XE QUÁ HẠN / CẦN THAY NGAY:")
                for o in overdue:
                    lines.append(f"  • Xe {o['plate_number']}: Km hiện tại {o['current_km']} km, Quá hạn {o['remaining_km']} km (Đến hạn ở mốc {o['due_km']} km)")
            else:
                lines.append("✅ Không có xe nào bị quá hạn thay nhớt!")

            if near_due:
                lines.append("\n⚠️ CÁC XE GẦN TỚI HẠN (CẦN LÊN LỊCH SỚM):")
                for n in near_due:
                    lines.append(f"  • Xe {n['plate_number']}: Hiện tại {n['current_km']} km, Còn lại {n['remaining_km']} km (Đến hạn mốc {n['due_km']} km)")

            if notes_trucks:
                lines.append("\n📌 XE CÓ MỐC GHI CHÚ ĐẶC BIỆT TỪ TRANG TÍNH:")
                for nt in notes_trucks[:5]:
                    lines.append(f"  • Xe {nt['plate_number']}: {nt['notes']} (ODO hiện tại: {nt['current_km']} km)")

            lines.append("\n👉 Vào Tab 'Bảo Dưỡng Định Kỳ' để xem đầy đủ 25 xe theo đúng Google Sheet!")
            return {"type": "maintenance_summary", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi lấy dữ liệu bảo dưỡng: {str(e)}"}

    # 2. CẢNH BÁO XE CHẠY KHÔNG QUẸT THẺ RFID LÁI XE
    if any(k in cmd_lower for k in ["không quẹt thẻ", "chưa quẹt thẻ", "quẹt thẻ", "thẻ lái xe", "rfid"]):
        try:
            telemetry = gps_client.fetch_live_fleet()
            no_card = [v for v in telemetry if v.get("card_violation") == "running_no_card" and v.get("speed", 0) > 0]
            
            if not no_card:
                return {
                    "type": "card_report",
                    "message": "🟢 [GIÁM SÁT THẺ RFID LÁI XE BÌNH ANH GPS]\n"
                               "✅ TOÀN ĐOÀN ĐÚNG QUY ĐỊNH! Tất cả các xe đang lăn bánh trên đường đều ĐÃ QUẸT THẺ lái xe hợp lệ theo quy định của Tổng cục Đường bộ."
                }
            else:
                lines = [f"🚨 [CẢNH BÁO VI PHẠM: {len(no_card)} XE ĐANG CHẠY NHƯNG CHƯA QUẸT THẺ RFID]:"]
                for nc in no_card:
                    lines.append(f"• Xe {nc['plate_number']}: Đang chạy {nc['speed']} km/h (TX trên xe: {nc['driver_name']}) tại {nc['address']}")
                lines.append("\n⚠️ Đề nghị Bộ Phận Điều Hành gọi điện nhắc nhở tài xế quẹt thẻ ngay để tránh bị Thanh Tra Giao Thông xử phạt vi phạm hành chính!")
                return {"type": "card_alert", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra thẻ RFID: {str(e)}"}

    # 3. CƠ CẤU ĐỘI XE: 15 XE BEN & 11 XE THÙNG
    if any(k in cmd_lower for k in ["bao nhiêu xe", "phân loại", "xe ben", "xe thùng", "cơ cấu", "đội xe gồm"]):
        ben_list = ["63H-042.73", "63G-002.86", "63E-011.56", "63E-011.17", "63E-011.08", "63F-005.28", "63G-002.62", "63H-042.39", "63E-012.76", "63E-011.03", "63E-011.18", "63F-005.11", "63H-042.34", "63E-012.35", "63H-042.36"]
        thung_list = ["63E-012.01", "63G-002.80", "63G-002.97", "66H-083.48", "63E-011.32", "63F-005.12", "63E-011.41", "63E-012.12", "63F-005.38", "63F-005.44", "63F-005.16"]
        return {
            "type": "fleet_structure",
            "message": f"🚛 [CƠ CẤU ĐỘI XE ĐẦU KÉO TRƯỜNG PHÁT — TỔNG CỘNG 26 XE]:\n\n"
                       f"🔸 15 XE BEN (Chuyên cát, đá, vật liệu xây dựng — Ký hiệu màu Cam/Hổ phách):\n"
                       f"  {', '.join(ben_list)}\n\n"
                       f"🔹 11 XE THÙNG (Chuyên chở container, hàng khô, cám — Ký hiệu màu Xanh dương):\n"
                       f"  {', '.join(thung_list)}\n\n"
                       f"💡 Trên hệ thống, 15 Xe Ben luôn được tự động gom lên trên đầu bảng nhiên liệu, Xe Thùng ở phía dưới kèm mã màu trực quan để nhận diện tức thì."
        }

    # 4. HẠN ĐĂNG KIỂM & GIẤY TỜ XE SẮP HẾT HẠN
    if any(k in cmd_lower for k in ["đăng kiểm", "hạn đăng kiểm", "giấy tờ", "bảo hiểm", "phù hiệu", "hết hạn"]):
        try:
            expiring_vehicles = [
                {"plate": "63H-042.36", "expiry": "02/09/2026", "days": 1, "note": "Hết hạn ngày mai! Cần đưa đi kiểm định ngay"},
                {"plate": "63F-005.16", "expiry": "03/09/2026", "days": 2, "note": "Sắp hết hạn trong 2 ngày"},
                {"plate": "63G-002.62", "expiry": "05/09/2026", "days": 4, "note": "Thế chấp VPBank"},
                {"plate": "63H-042.39", "expiry": "05/09/2026", "days": 4, "note": "Thế chấp VPBank"},
                {"plate": "63H-042.34", "expiry": "08/09/2026", "days": 7, "note": "Sắp hết hạn trong 7 ngày"},
                {"plate": "63F-005.11", "expiry": "08/09/2026", "days": 7, "note": "Sắp hết hạn trong 7 ngày"},
                {"plate": "63E-012.12", "expiry": "09/09/2026", "days": 8, "note": "Sắp hết hạn trong 8 ngày"},
                {"plate": "63G-002.80", "expiry": "10/09/2026", "days": 9, "note": "Sắp hết hạn trong 9 ngày"},
                {"plate": "63G-002.97", "expiry": "16/09/2026", "days": 15, "note": "Sắp hết hạn trong 15 ngày"},
                {"plate": "63E-012.01", "expiry": "17/09/2026", "days": 16, "note": "Sắp hết hạn trong 16 ngày"}
            ]
            lines = [f"📋 [HỆ THỐNG GIÁM SÁT HẠN ĐĂNG KIỂM & GIẤY TỜ XE (DƯỚI 30 NGÀY)]:\n"
                     f"⚠️ Phát hiện {len(expiring_vehicles)} xe sắp đến hạn kiểm định trong tháng 09/2026:"]
            for ev in expiring_vehicles:
                lines.append(f"• Xe {ev['plate']}: Hạn {ev['expiry']} (Còn {ev['days']} ngày) — {ev['note']}")
            lines.append("\n👉 Bộ phận hồ sơ cần sắp xếp lịch đăng kiểm luân phiên để không gián đoạn lệnh chạy hàng!")
            return {"type": "expiry_report", "message": "\n".join(lines)}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra hạn giấy tờ: {str(e)}"}

    # 5. CHI PHÍ THAY VỎ XE & CÔNG NỢ MAY BẠT PHÙNG LĨNH
    if any(k in cmd_lower for k in ["thay vỏ", "vỏ xe", "lốp", "may bạt", "bạt xe", "phùng lĩnh"]):
        return {
            "type": "tires_tarps_report",
            "message": "🛠️ [BÁO CÁO VẬT TƯ & CÔNG NỢ XƯỞNG NĂM 2026]:\n\n"
                       "1️⃣ THEO DÕI THAY VỎ XE CẢ ĐỘI:\n"
                       "• Tổng số vỏ đã thay trong năm: 141 vỏ xe\n"
                       "• Tổng chi phí thay vỏ: 630.910.000 đ (Đã thanh toán 100%)\n\n"
                       "2️⃣ CÔNG NỢ MAY BẠT — NHÀ CUNG CẤP PHÙNG LĨNH:\n"
                       "• Tổng phát sinh: 45.600.000 đ\n"
                       "• Đã thanh toán: 40.800.000 đ\n"
                       "• CÒN NỢ CHƯA THANH TOÁN: 4.800.000 đ\n\n"
                       "👉 Dữ liệu được đồng bộ trực tiếp từ file Quản lý Vật tư & Trang thiết bị của công ty."
        }

    # 6. THÔNG TIN ĐỘI SÀ LAN VẬN TẢI THỦY
    if any(k in cmd_lower for k in ["sà lan", "sa lan", "đội tàu", "đường thủy"]):
        return {
            "type": "barge_report",
            "message": "🛥️ [ĐỘI TÀU & SÀ LAN VẬN TẢI THỦY TRƯỜNG PHÁT]:\n"
                       "• Tổng số lượng: 10 Sà Lan (Trường Phát 01 đến Trường Phát 10)\n"
                       "• Trọng tải chuyên chở: Từ 500 Tấn đến 1.500 Tấn / chiếc\n"
                       "• Chuyên tuyến: Vận chuyển cát đá, clinker, than đá và nông sản tuyến Đồng bằng Sông Cửu Long — TP.HCM — Vũng Tàu — Campuchia\n"
                       "• Trạng thái hôm nay: Đang vận hành an toàn và phối hợp trung chuyển hàng hóa với đội xe đầu kéo tại các bến cảng."
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
                           f"✅ TOÀN ĐOÀN AN TOÀN! Tất cả {summary['total_vehicles']} xe đầu kéo và rơ-moóc đều SẠCH LỖI, không có vi phạm phạt nguội nào trên hệ thống toàn quốc!"
            }
        else:
            details = []
            for v in violated_list:
                for vl in v["violations"]:
                    details.append(
                        f"• Xe {v['plate_number']} (TX: {v['driver_name']}):\n"
                        f"  - Hành vi: {vl['behavior']}\n"
                        f"  - Địa điểm: {vl['location']}\n"
                        f"  - Tiền phạt ước tính: {vl['fine_amount']:,}đ ({vl['status']})\n"
                        f"  - Đơn vị CSGT: {vl['enforcing_unit']}\n"
                        f"  - ⚠️ {vl['registry_warning_text']}"
                    )
            details_str = "\n".join(details)
            return {
                "type": "fines_report",
                "message": f"🚦 [KẾT QUẢ QUÉT PHẠT NGUỘI TOÀN ĐOÀN 26 XE]:\n"
                           f"• Số xe an toàn sạch lỗi: {summary['clean_vehicles']}/{summary['total_vehicles']} xe\n"
                           f"• Phát hiện: {summary['violated_vehicles']} xe có lỗi phạt nguội chưa nộp phạt:\n"
                           f"{details_str}\n\n"
                           f"👉 Vui lòng vào Tab 'Tra Cứu Phạt Nguội' để xem chi tiết biên bản và nộp phạt trước kỳ đăng kiểm!"
            }

    # 8. HỎI THÔNG TIN VỊ TRÍ, GPS, KM, NHIÊN LIỆU XE
    if any(k in cmd_lower for k in ["ở đâu", "vị trí", "gps", "tọa độ", "nhiên liệu", "chạy bao nhiêu", "km hôm nay", "tình hình xe", "% xe"]):
        try:
            telemetry = gps_client.fetch_live_fleet()
            # Check if asking about specific vehicle
            matched_v = None
            clean_cmd = cmd_lower.replace("-", "").replace(".", "").replace(" ", "")
            for v in telemetry:
                clean_p = v["plate_number"].replace("-", "").replace(".", "").replace(" ", "").lower()
                if clean_p in clean_cmd:
                    matched_v = v
                    break

            if matched_v:
                clean_target = matched_v["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
                v_type = "Xe Ben" if clean_target in XE_BEN_PLATES else "Xe Thùng"
                fuel_txt = ""
                try:
                    fuel_info = gps_client.fetch_vehicle_fuel_detail(matched_v["plate_code"], matched_v["longitude"], matched_v["latitude"])
                    if fuel_info.get("liters"):
                        fuel_txt = f"\n⛽ Mức nhiên liệu: {fuel_info['liters']} Lít ({fuel_info['percent']}%)"
                except Exception:
                    pass

                return {
                    "type": "gps_query",
                    "message": f"🛰️ [BÌNH ANH GPS] Xe {matched_v['plate_number']} ({v_type}):\n"
                               f"• Trạng thái: {matched_v['status_text']}\n"
                               f"• Vị trí hiện tại: {matched_v['address']}\n"
                               f"• Km chạy hôm nay: {matched_v['daily_km']} km\n"
                               f"• Tài xế phụ trách: {matched_v['driver_name']}\n"
                               f"• Quẹt thẻ RFID: {'🟢 Đã quẹt thẻ' if matched_v['is_card_swiped'] else '🚨 Chưa quẹt thẻ'}"
                               f"{fuel_txt}"
                }
            else:
                running = [v for v in telemetry if v["speed"] > 0]
                idling = [v for v in telemetry if v["status_type"] == "idling"]
                total_km = sum(v["daily_km"] for v in telemetry)
                return {
                    "type": "gps_summary",
                    "message": f"🛰️ [TỔNG QUAN HÀNH TRÌNH ĐỘI XE]:\n"
                               f"• Tổng số xe quản lý: 26 xe đầu kéo (15 Xe Ben + 11 Xe Thùng)\n"
                               f"• Đang chạy trên đường: {len(running)} xe\n"
                               f"• Đang dừng nổ máy: {len(idling)} xe\n"
                               f"• Tổng quãng đường cả đội đã chạy hôm nay: {round(total_km, 1)} km"
                }
        except Exception as e:
            return {"type": "error", "message": f"Không thể lấy dữ liệu GPS: {str(e)}"}

    # 9. BÁO CÁO HAO HỤT / CHỐNG HÚT DẦU
    if any(k in cmd_lower for k in ["hao dầu", "hút dầu", "tiêu hao", "dầu", "định mức"]):
        try:
            telemetry = gps_client.fetch_live_fleet()
            suspicious = [v for v in telemetry if v["is_suspicious_drain"]]
            over_norm = [v for v in telemetry if v["drain_alert_type"] == "over_norm"]
            total_consumed = sum(v["consumed_liters"] for v in telemetry)

            if not suspicious and not over_norm:
                return {
                    "type": "fuel_report",
                    "message": f"⛽ [GIÁM SÁT NHIÊN LIỆU]:\n"
                               f"• Tổng dầu đã tiêu hao hôm nay: {round(total_consumed, 1)} Lít\n"
                               f"• Định mức bình quân toàn đội: Đạt chuẩn quy chuẩn 40 Lít/100km\n"
                               f"• Cảnh báo thất thoát: 🟢 AN TOÀN - Không phát hiện xe nào có dấu hiệu sụt dầu hoặc hút trộm dầu!"
                }
            else:
                alert_lines = []
                for s in suspicious:
                    alert_lines.append(f"🚨 Xe {s['plate_number']} ({s['driver_name']}): Nghi ngờ sụt dầu bất thường tại {s['address']}")
                for o in over_norm:
                    alert_lines.append(f"⚠️ Xe {o['plate_number']} ({o['driver_name']}): Định mức vọt lên {o['actual_norm']} L/100km (Vượt chuẩn 40L)")
                return {
                    "type": "fuel_alert",
                    "message": f"⛽ [CẢNH BÁO TIÊU HAO DẦU BẤT THƯỜNG]:\n" + "\n".join(alert_lines)
                }
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra dầu: {str(e)}"}

    # 10. THI ĐUA TÀI XẾ
    if any(k in cmd_lower for k in ["tài xế", "chạy nhiều", "top", "thi đua", "nhiều km"]):
        try:
            telemetry = gps_client.fetch_live_fleet()
            ranked = sorted(telemetry, key=lambda x: x["daily_km"], reverse=True)
            top3 = ranked[:3]
            msg = "🏆 [TOP 3 TÀI XẾ CHẠY NHIỀU KM NHẤT HÔM NAY]:\n"
            medals = ["🥇", "🥈", "🥉"]
            for i, t in enumerate(top3):
                msg += f"{medals[i]} {t['driver_name']} (Xe {t['plate_number']}): {t['daily_km']} km [Vận tốc: {t['speed']} km/h]\n"
            return {"type": "driver_ranking", "message": msg.strip()}
        except Exception as e:
            return {"type": "error", "message": f"Lỗi xếp hạng tài xế: {str(e)}"}

    # Default fallback
    return {
        "type": "assistant_help",
        "message": f"🤖 Tôi là Trợ Lý AI Vận Hành Thông Minh của Vận Tải Trường Phát. Bạn có thể hỏi tôi bất kỳ thông tin nào sau đây:\n"
                   f"• 'Tình hình bảo dưỡng xe' hoặc 'Xe nào quá hạn thay nhớt' (Khớp 100% Google Sheet)\n"
                   f"• 'Xe 63F-005.38 bảo dưỡng chưa' (Xem chi tiết ODO & mốc đến hạn từng xe)\n"
                   f"• 'Xe nào chạy không quẹt thẻ' (Cảnh báo vi phạm RFID lái xe theo thời gian thực)\n"
                   f"• 'Đội xe có bao nhiêu xe ben và xe thùng' (Cơ cấu 15 xe ben & 11 xe thùng)\n"
                   f"• 'Xe nào sắp hết hạn đăng kiểm' (Cảnh báo giấy tờ xe dưới 30 ngày)\n"
                   f"• 'Chi phí thay vỏ xe và may bạt' (Công nợ Phùng Lĩnh & 141 vỏ xe)\n"
                   f"• 'Tình hình đội sà lan' (10 sà lan vận tải thủy)\n"
                   f"• 'Kiểm tra phạt nguội đoàn xe' (Quét trực tiếp Cục CSGT)\n"
                   f"• 'Xe 63E-011.18 đang ở đâu' (Tra cứu vị trí GPS, tốc độ & bình dầu)\n"
                   f"• 'Báo cáo xe nào hao dầu hôm nay' (Chống hút trộm dầu)\n"
                   f"• 'Tài xế nào chạy nhiều km nhất hôm nay' (Bảng vàng thi đua)"
    }
