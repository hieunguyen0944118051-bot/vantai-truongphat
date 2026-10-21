"""Tra cứu nhanh (dò từ khóa, KHÔNG phải AI).

Chỉ trả lời từ dữ liệu thật: GPS Bình Anh, Sheets lệnh điều xe, Sheets bảo dưỡng.
Câu hỏi về dầu / giấy tờ / phạt nguội: nói rõ chưa có nguồn thay vì bịa số.
"""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import auth
import models
from fleet import FLEET, FLEET_BY_CLEAN, clean_plate
from gps_service import gps_client
from sheets_service import sheets_client

router = APIRouter(prefix="/api/assistant", tags=["Tra cứu nhanh"])

HELP = ("Tra cứu nhanh hiểu các câu như:\n"
        "• \"Xe 63E-011.18 ở đâu\" (GPS Bình Anh)\n"
        "• \"% xe hoạt động hôm nay\" (Sheets lệnh điều xe)\n"
        "• \"Xe nào chưa quẹt thẻ\" (GPS Bình Anh)\n"
        "• \"Bảo dưỡng\" hoặc \"Bảo dưỡng 63H-042.73\" (Sheets bảo dưỡng)")


class AssistantCommand(BaseModel):
    command: str


def _find_plate(text: str):
    t = clean_plate(text)
    return next((k for k in FLEET_BY_CLEAN if k in t), None)


@router.post("/execute")
def execute(req: AssistantCommand, current_user: models.User = Depends(auth.get_current_user)):
    cmd = req.command.strip().lower()
    plate = _find_plate(req.command)

    if any(k in cmd for k in ("dầu", "định mức", "phạt nguội", "đăng kiểm", "giấy tờ", "hết hạn")):
        return {"type": "not_available",
                "message": "Mục này chưa có nguồn dữ liệu thật trên app (đang chuyển sang đọc file "
                           "ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM ở GĐ2). Tạm xem trực tiếp trên Google Sheets."}

    if any(k in cmd for k in ("bảo dưỡng", "thay nhớt", "nhớt")):
        rows = sheets_client.fetch_maintenance_sheet()
        if not rows:
            return {"type": "error", "message": "Không đọc được bảng bảo dưỡng từ Google Sheets."}
        if plate:
            m = next((r for r in rows if clean_plate(r["plate_number"]) == plate), None)
            if not m:
                return {"type": "error", "message": f"Không thấy xe {FLEET_BY_CLEAN[plate]['plate_number']} trong bảng bảo dưỡng."}
            return {"type": "maintenance_detail", "message":
                    f"🔧 Xe {m['plate_number']} (nguồn: Sheets bảo dưỡng)\n"
                    f"• Km thay nhớt gần nhất: {m['last_km']} ({m['last_date']})\n"
                    f"• Km hiện tại: {m['current_km']} — đến hạn ở {m['due_km']}\n"
                    f"• Còn lại: {m['remaining_km']} km — {m['status']}"}
        due = [r for r in rows if any(w in r["status"].lower() for w in ("quá", "sắp", "gần"))]
        missing = [r for r in rows if "thiếu" in r["status"].lower()]
        lines = [f"🔧 Bảng thay nhớt (nguồn: Sheets) — {len(rows)} xe"]
        lines += [f"• {r['plate_number']}: còn {r['remaining_km']} km — {r['status']}" for r in due] or ["• Không có xe sắp/quá hạn."]
        if missing:
            lines.append("Thiếu số liệu: " + ", ".join(r["plate_number"] for r in missing))
        return {"type": "maintenance_summary", "message": "\n".join(lines)}

    if any(k in cmd for k in ("quẹt thẻ", "thẻ lái", "rfid")):
        fleet = gps_client.fetch_live_fleet()
        bad = [v for v in fleet if v.get("card_violation") == "running_no_card"]
        if not bad:
            return {"type": "card_report", "message": "Không có xe nào đang chạy mà chưa quẹt thẻ (nguồn: GPS Bình Anh)."}
        return {"type": "card_alert", "message": "Xe đang chạy chưa quẹt thẻ (GPS Bình Anh):\n" + "\n".join(
            f"• {v['plate_number']} — {v['speed']} km/h — GPS lúc {v['gps_time']}" for v in bad)}

    if any(k in cmd for k in ("% xe", "hoạt động", "bao nhiêu xe chạy")):
        try:
            d = sheets_client.fetch_daily_trips(date.today().strftime("%Y-%m-%d"))
        except Exception as e:
            return {"type": "error", "message": f"Chưa đọc được lệnh điều xe hôm nay: {e}"}
        total = len(FLEET)
        return {"type": "active_rate", "message":
                f"Hôm nay {d['active_count']}/{total} xe có lệnh chạy ({round(d['active_count'] / total * 100, 1)}%), "
                f"{d['off_count']} xe nghỉ/sửa. Nguồn: Sheets lệnh điều xe, đọc lúc {d['sync_time']}."}

    if plate or any(k in cmd for k in ("ở đâu", "vị trí", "gps", "km")):
        fleet = gps_client.fetch_live_fleet()
        if plate:
            v = next((x for x in fleet if clean_plate(x["plate_number"]) == plate), None)
            if not v:
                return {"type": "error", "message": "Không có dữ liệu GPS của xe này."}
            stale = " (⚠ tín hiệu cũ)" if v["is_stale"] else ""
            return {"type": "gps_detail", "message":
                    f"🛰 Xe {v['plate_number']} — {v['status_text']}\n"
                    f"• Vị trí: {v['address'] or 'không rõ'}\n"
                    f"• Km hôm nay: {v['daily_km']} km\n"
                    f"• Giờ GPS: {v['gps_time'] or 'không có'}{stale}"}
        return {"type": "gps_summary", "message": f"GPS: {sum(1 for x in fleet if x['speed'] > 0)} xe đang chạy, "
                f"{sum(1 for x in fleet if x['is_stale'])} xe tín hiệu cũ. Hỏi \"Xe <biển số> ở đâu\" để xem từng xe."}

    return {"type": "help", "message": HELP}
