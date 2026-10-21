"""Tra cứu nhanh (dò từ khóa, KHÔNG phải AI).

Chỉ trả lời từ dữ liệu thật: GPS Bình Anh, Sheets lệnh điều xe, Sheets ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM.
Phạt nguội: cổng CSGT có mã xác nhận nên không tự tra — hướng dẫn mở cổng, không bịa số.
"""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import auth
import models
from fleet import FLEET, FLEET_BY_CLEAN, clean_plate
from gps_service import gps_client
from sheets_service import sheets_client
from fleet_sheet import fleet_sheet

router = APIRouter(prefix="/api/assistant", tags=["Tra cứu nhanh"])

HELP = ("Tra cứu nhanh hiểu các câu như:\n"
        "• \"Xe 63E-011.18 ở đâu\" (GPS Bình Anh)\n"
        "• \"% xe hoạt động hôm nay\" (Sheets lệnh điều xe)\n"
        "• \"Xe nào chưa quẹt thẻ\" (GPS Bình Anh)\n"
        "• \"Bảo dưỡng\" hoặc \"Bảo dưỡng 63H-042.73\" (Sheets bảo dưỡng)\n"
        "• \"Xe nào hao dầu\" hoặc \"Dầu 63H-042.73\" (sổ đổ dầu)\n"
        "• \"Giấy tờ sắp hết hạn\" (đăng kiểm, giấy đi đường, tem)\n"
        "• \"Tài xế nào chạy nhiều km nhất\" (GPS Bình Anh)")


class AssistantCommand(BaseModel):
    command: str


def _find_plate(text: str):
    t = clean_plate(text)
    return next((k for k in FLEET_BY_CLEAN if k in t), None)


def _dmy(s):
    return "—" if not s else "/".join(reversed(str(s)[:10].split("-")))


def _left(x):
    if x.get("days_left") is None:
        return "thiếu số liệu"
    return f"quá {-x['days_left']} ngày" if x["days_left"] < 0 else f"còn {x['days_left']} ngày"


@router.post("/execute")
def execute(req: AssistantCommand, current_user: models.User = Depends(auth.get_current_user)):
    cmd = req.command.strip().lower()
    plate = _find_plate(req.command)

    if "phạt nguội" in cmd:
        return {"type": "fines_info", "message":
                "🚦 Phạt nguội tra trên cổng CSGT: https://www.csgt.vn/tra-cuu-phuong-tien-vi-pham.html\n"
                "Cổng bắt nhập mã xác nhận nên app không tự tra. Vào mục \"Tra Cứu Phạt Nguội\": bấm nút ở từng xe, "
                "app chép sẵn biển số và mở trang CSGT. Nên tra trước các xe sắp đăng kiểm."}

    if any(k in cmd for k in ("dầu", "định mức", "hao")):
        try:
            d = fleet_sheet.load()
        except Exception as e:
            return {"type": "error", "message": f"Không đọc được sổ đổ dầu trên Google Sheets: {e}"}
        src = f"Nguồn: sổ ĐỔ DẦU (Sheets), nhập đến {_dmy(d['todo']['fuel_log_last_date'])}."
        if plate:
            v = next((x for k, x in d["fuel"]["by_plate"].items() if clean_plate(k) == plate), None)
            if not v or v.get("latest_l_per_100km") is None:
                return {"type": "fuel_detail", "message": f"Xe {FLEET_BY_CLEAN[plate]['plate_number']} chưa đủ 2 lần đổ đầy bình để tính L/100km. {src}"}
            return {"type": "fuel_detail", "message":
                    f"⛽ Xe {FLEET_BY_CLEAN[plate]['plate_number']}\n"
                    f"• L/100km lần gần nhất: {v['latest_l_per_100km']} (định mức {v['norm']})\n"
                    f"• Bình quân: {v['avg_l_per_100km']} • {v['fills']} lượt đổ\n{src}"}
        over = [(k, v) for k, v in d["fuel"]["by_plate"].items()
                if v.get("latest_l_per_100km") is not None and v.get("norm") and (v["latest_l_per_100km"] - v["norm"]) / v["norm"] > 0.1]
        over.sort(key=lambda kv: (kv[1]["latest_l_per_100km"] - kv[1]["norm"]) / kv[1]["norm"], reverse=True)
        if not over:
            return {"type": "fuel_summary", "message": f"Không có xe nào vượt định mức > 10% ở lần đo gần nhất. {src}"}
        return {"type": "fuel_summary", "message": "⛽ Xe vượt định mức > 10% (lần đo gần nhất, giữa 2 lần đầy bình):\n" + "\n".join(
            f"• {k}: {v['latest_l_per_100km']} L/100km (định mức {v['norm']}, +{round((v['latest_l_per_100km'] - v['norm']) / v['norm'] * 100, 1)}%)"
            for k, v in over) + f"\n{src}"}

    if any(k in cmd for k in ("giấy tờ", "đăng kiểm", "hết hạn", "giấy đi đường", "tem", "bảo hiểm")):
        try:
            d = fleet_sheet.load()
        except Exception as e:
            return {"type": "error", "message": f"Không đọc được bảng giấy tờ trên Google Sheets: {e}"}
        docs = d["docs"]
        if plate:
            mine = [x for x in docs if clean_plate(x["plate"]) == plate]
            return {"type": "docs_detail", "message": f"📄 Giấy tờ xe {FLEET_BY_CLEAN[plate]['plate_number']} (Sheets):\n" + "\n".join(
                f"• {x['kind']}: {_dmy(x['expiry'])} — {_left(x)}" for x in mine)}
        due = sorted([x for x in docs if x["status"] in ("overdue", "soon", "near")], key=lambda x: x["days_left"])
        if not due:
            return {"type": "docs_summary", "message": "📄 Không có giấy tờ nào quá hạn / sắp hạn (nguồn: Google Sheets)."}
        return {"type": "docs_summary", "message": f"📄 Giấy tờ quá hạn / sắp hạn (Sheets, đỏ ≤ {d['thresholds']['red']} ngày, vàng ≤ {d['thresholds']['yellow']} ngày):\n" + "\n".join(
            f"• {x['plate']} — {x['kind']}{(' (' + x['subject'] + ')') if x['subject'] != x['plate'] else ''}: {_dmy(x['expiry'])}, {_left(x)}" for x in due)}

    if any(k in cmd for k in ("top", "chạy nhiều", "nhiều km")) and "thẻ" not in cmd:
        fleet = gps_client.fetch_live_fleet()
        top = sorted([v for v in fleet if v.get("daily_km", 0) > 0], key=lambda v: v["daily_km"], reverse=True)[:5]
        if not top:
            return {"type": "top_drivers", "message": "Chưa có xe nào chạy hôm nay (nguồn: GPS Bình Anh)."}
        return {"type": "top_drivers", "message": "🏆 Chạy nhiều km nhất hôm nay (GPS Bình Anh):\n" + "\n".join(
            f"{i + 1}. {FLEET_BY_CLEAN.get(clean_plate(v['plate_number']), {}).get('driver_name') or v.get('driver_name') or 'Chưa rõ tài xế'} — {v['plate_number']}: {v['daily_km']} km"
            for i, v in enumerate(top))}

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
