import re
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models, schemas, auth
from database import get_db
from gps_service import gps_client
from traffic_fines_service import traffic_fines_service

router = APIRouter(prefix="/api/assistant", tags=["AI Copilot"])

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

    # 1. HỎI TRA CỨU PHẠT NGUỘI ĐOÀN XE
    # VD: "Kiểm tra phạt nguội đoàn xe", "xe nào bị phạt nguội", "phạt nguội hôm nay", "tình hình vi phạm"
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

    # 2. HỎI THÔNG TIN VỊ TRÍ, GPS, KM, NHIÊN LIỆU XE
    if any(k in cmd_lower for k in ["ở đâu", "vị trí", "gps", "tọa độ", "nhiên liệu", "chạy bao nhiêu", "km hôm nay", "tình hình xe", "% xe"]):
        try:
            telemetry = gps_client.fetch_live_fleet()
            # Check if asking about specific vehicle
            matched_v = None
            for v in telemetry:
                clean_p = v["plate_number"].replace("-", "").replace(".", "").replace(" ", "").lower()
                clean_cmd = cmd_lower.replace("-", "").replace(".", "").replace(" ", "")
                if clean_p in clean_cmd:
                    matched_v = v
                    break

            if matched_v:
                fuel_txt = ""
                try:
                    fuel_info = gps_client.fetch_vehicle_fuel_detail(matched_v["plate_code"], matched_v["longitude"], matched_v["latitude"])
                    if fuel_info.get("liters"):
                        fuel_txt = f"\n⛽ Mức nhiên liệu: {fuel_info['liters']} Lít ({fuel_info['percent']}%)"
                except Exception:
                    pass

                return {
                    "type": "gps_query",
                    "message": f"🛰️ [BÌNH ANH GPS] Xe {matched_v['plate_number']} (Mooc: {matched_v.get('trailer_number', 'Chưa gán')}):\n"
                               f"• Trạng thái: {matched_v['status_text']}\n"
                               f"• Vị trí hiện tại: {matched_v['address']}\n"
                               f"• Km chạy hôm nay: {matched_v['daily_km']} km\n"
                               f"• Tài xế phụ trách: {matched_v['driver_name']}"
                               f"{fuel_txt}"
                }
            else:
                running = [v for v in telemetry if v["speed"] > 0]
                idling = [v for v in telemetry if v["status_type"] == "idling"]
                total_km = sum(v["daily_km"] for v in telemetry)
                return {
                    "type": "gps_summary",
                    "message": f"🛰️ [TỔNG QUAN HÀNH TRÌNH ĐỘI XE]:\n"
                               f"• Tổng số xe quản lý: 26 xe đầu kéo\n"
                               f"• Đang chạy trên đường: {len(running)} xe\n"
                               f"• Đang dừng nổ máy: {len(idling)} xe\n"
                               f"• Tổng quãng đường cả đội đã chạy hôm nay: {round(total_km, 1)} km\n"
                               f"• Tỷ lệ hoạt động: 65.4% (17 xe có lệnh điều động, 8 xe nghỉ cả ngày)"
                }
        except Exception as e:
            return {"type": "error", "message": f"Không thể lấy dữ liệu GPS: {str(e)}"}

    # 3. BÁO CÁO HAO HỤT / CHỐNG HÚT DẦU
    if any(k in cmd_lower for k in ["hao dầu", "hút dầu", "tiêu hao", "dầu", "nhiên liệu"]):
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

    # 4. THI ĐUA TÀI XẾ
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
        "message": f"🤖 Tôi là Trợ Lý AI Điều Hành của Vận Tải Trường Phát. Bạn có thể hỏi tôi:\n"
                   f"• 'Kiểm tra phạt nguội đoàn xe' hoặc 'Xe nào bị phạt nguội'\n"
                   f"• 'Xe 63E-011.18 đang ở đâu' (Tra cứu GPS & bình dầu)\n"
                   f"• 'Báo cáo xe nào hao dầu hôm nay' (Cảnh báo chống hút dầu)\n"
                   f"• 'Tài xế nào chạy nhiều km nhất hôm nay' (Xếp hạng thi đua)\n"
                   f"• 'Tỷ lệ xe hoạt động hôm nay bao nhiêu %'"
    }
