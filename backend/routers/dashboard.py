"""Trang Tổng quan. Chỉ trả số liệu có nguồn thật:
- Lệnh điều xe trong ngày: Google Sheets XE_NHẬN_HÀNG_THÁNG_MM-YYYY
- Vị trí, km trong ngày, thẻ lái xe: GPS Bình Anh (kèm giờ GPS gốc từng xe)
Đã bỏ: dầu tiêu hao/định mức/hút dầu (bịa), km tuần ước tính, top tài xế, phạt nguội mẫu,
giấy tờ xe từ DB tháng 8 (GĐ2 sẽ đọc từ Sheets).
"""
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import auth
import models
from database import get_db
from fleet import FLEET_BY_CLEAN, XE_BEN_PLATES, clean_plate, driver_for
from gps_service import gps_client
from sheets_service import sheets_client

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    view_date: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    today = date.today()
    try:
        target_date = datetime.strptime(view_date, "%Y-%m-%d").date() if view_date else today
    except ValueError:
        target_date = today

    # ---- 1. Lệnh điều xe từ Google Sheets ----
    try:
        sheet = sheets_client.fetch_daily_trips(target_date=target_date.strftime("%Y-%m-%d"))
        sheet_warning = None
    except Exception as e:  # chưa có file / lỗi đọc: không bịa số
        sheet, sheet_warning = {}, str(e)
    all_trips = sheet.get("all_trips", [])
    ben_trips = sheet.get("ben_trips", [])
    thung_trips = sheet.get("thung_trips", [])
    active_count = sheet.get("active_count", 0)
    off_count = sheet.get("off_count", 0)
    total_vehicles = len(FLEET_BY_CLEAN)
    active_percent = round(active_count / total_vehicles * 100, 1) if total_vehicles else 0.0

    # ---- 2. GPS Bình Anh ----
    gps_fleet = gps_client.fetch_live_fleet()
    gps_table, km_chart = [], []
    running = idling = stopped = 0
    total_daily_km = 0.0
    for item in gps_fleet:
        cp = clean_plate(item["plate_number"])
        info = FLEET_BY_CLEAN.get(cp, {})
        if item["speed"] > 0:
            running += 1
            op_state = "running"
        elif item["status_type"] == "idling":
            idling += 1
            op_state = "idling"
        else:
            stopped += 1
            op_state = "parked"
        total_daily_km += item["daily_km"]
        gps_table.append({
            **item,
            "trailer_number": info.get("trailer_number", "—"),
            "vehicle_type": info.get("vehicle_type", "—"),
            "op_state": op_state,
        })
        if item["daily_km"] > 0:
            km_chart.append({"plate": item["plate_number"], "km": item["daily_km"]})
    gps_table.sort(key=lambda x: (0 if clean_plate(x["plate_number"]) in XE_BEN_PLATES else 1, -x["daily_km"]))
    km_chart.sort(key=lambda x: -x["km"])

    running_no_card = sorted(
        ({"plate_number": i["plate_number"], "driver_name": i["driver_name"], "speed": i["speed"],
          "daily_km": i["daily_km"], "address": i["address"], "gps_time": i["gps_time"]}
         for i in gps_fleet if i.get("card_violation") == "running_no_card" and i["speed"] > 0),
        key=lambda x: -x["speed"])

    # ---- 3. Tuyến chạy trong ngày (từ Sheets) ----
    route_counter, route_trips = Counter(), defaultdict(list)
    for t in all_trips:
        r = (t.get("route") or "").strip()
        if t.get("status_code") == "active" and r and "NGHỈ" not in r.upper():
            route_counter[r] += 1
            route_trips[r].append(t)
    top_routes = []
    for r, cnt in route_counter.most_common(10):
        vehicles = {}
        for t in route_trips[r]:
            p = t.get("plate_number")
            if not p:
                continue
            v = vehicles.setdefault(p, {"plate_number": p, "driver_name": driver_for(p, t.get("driver_name") or "—"),
                                        "vehicle_type": t.get("vehicle_type") or "—",
                                        "customer_name": t.get("customer_name") or "—",
                                        "cargo_type": t.get("cargo_type") or "—", "trips_count": 0})
            v["trips_count"] += 1
        vl = sorted(vehicles.values(), key=lambda x: -x["trips_count"])
        top_routes.append({
            "route": r, "trips_count": cnt, "vehicles_count": len(vl),
            "customer_name": next((v["customer_name"] for v in vl if v["customer_name"] != "—"), "—"),
            "cargo_type": next((v["cargo_type"] for v in vl if v["cargo_type"] != "—"), "—"),
            "vehicles": vl, "plates_str": ", ".join(v["plate_number"] for v in vl),
        })

    now = datetime.now()
    return {
        "sheet_warning": sheet_warning,
        "selected_date": target_date.strftime("%Y-%m-%d"),
        "selected_date_display": target_date.strftime("%d/%m/%Y"),
        "is_today": target_date == today,
        "timestamp": now.strftime("%H:%M:%S %d/%m/%Y"),
        "sources": {
            "sheets": {"label": "Google Sheets – XE NHẬN HÀNG THÁNG", "sync_time": sheet.get("sync_time")},
            "gps": gps_client.status(),
        },
        "total_vehicles": total_vehicles,
        "active_percent": active_percent,
        "active_vehicles_count": active_count,
        "off_vehicles_count": off_count,
        "ben_active_count": sum(1 for t in ben_trips if t.get("status_code") == "active"),
        "thung_active_count": sum(1 for t in thung_trips if t.get("status_code") == "active"),
        "running_vehicles_count": running,
        "idling_vehicles_count": idling,
        "stopped_vehicles_count": stopped,
        "total_daily_km": round(total_daily_km, 1),
        "gps_table": gps_table,
        "km_chart_data": km_chart[:15],
        "top_routes": top_routes,
        "customer_breakdown": sheet.get("customer_breakdown", []),
        "running_no_card_alerts": running_no_card,
        "running_no_card_count": len(running_no_card),
    }
