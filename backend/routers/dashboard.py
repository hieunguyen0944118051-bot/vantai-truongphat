from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime
from typing import Optional
from collections import Counter, defaultdict
import models, auth
from database import get_db
from gps_service import gps_client, OFFICIAL_DRIVERS_BY_CLEAN_PLATE
from sheets_service import sheets_client
from traffic_fines_service import traffic_fines_service

XE_BEN_PLATES = {
    '63H04273', '63G00286', '63E01156', '63E01117', '63E01108',
    '63F00528', '63G00262', '63H04239', '63E01276', '63E01103',
    '63E01118', '63F00511', '63H04234', '63E01235', '63H04236'
}

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    view_date: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    today = date.today()
    if view_date:
        try:
            target_date = datetime.strptime(view_date, "%Y-%m-%d").date()
        except Exception:
            target_date = today
    else:
        target_date = today

    is_today = (target_date == today)
    target_expiring = today + timedelta(days=30)

    # 1. Realtime GPS Telemetry & Fuel Analysis
    try:
        gps_fleet = gps_client.fetch_live_fleet()
    except Exception:
        gps_fleet = []

    vehicles = db.query(models.Vehicle).all()
    v_map = {v.plate_number.replace("-", "").replace(".", "").replace(" ", "").upper(): v for v in vehicles}

    # 1.2 Đọc Workbook Đổ Dầu - Bảo Dưỡng - Đăng Kiểm để lấy Định mức dầu Trang Tính & Cảnh báo Bảo dưỡng
    try:
        wb_maint_fuel = sheets_client.fetch_full_maintenance_and_fuel_workbook()
        sheet_vehicle_norms = wb_maint_fuel.get("fuel", {}).get("vehicle_norms", {})
        sheet_fuel_summary = wb_maint_fuel.get("fuel", {}).get("summary", {})
        sheet_overview = wb_maint_fuel.get("overview", {})
    except Exception:
        wb_maint_fuel = {}
        sheet_vehicle_norms = {}
        sheet_fuel_summary = {}
        sheet_overview = {}

    # 1.3 Đọc Lịch Điều Xe từ Google Sheets (Tháng 11, 10, 12+...)
    try:
        sheet_trips_res = sheets_client.fetch_daily_trips(target_date=target_date.strftime("%Y-%m-%d"))
        all_sheet_trips = sheet_trips_res.get("all_trips", [])
        ben_trips = sheet_trips_res.get("ben_trips", [])
        thung_trips = sheet_trips_res.get("thung_trips", [])
        partner_trips = sheet_trips_res.get("partner_trips", [])
        active_sheet_count = sheet_trips_res.get("active_count", 0)
        dispatched_count = sheet_trips_res.get("dispatched_count", 0)
        undispatched_count = sheet_trips_res.get("undispatched_count", 0)
        off_sheet_count = sheet_trips_res.get("off_count", 0)
        customer_breakdown = sheet_trips_res.get("customer_breakdown", [])
        origin_breakdown = sheet_trips_res.get("origin_breakdown", [])
        destination_breakdown = sheet_trips_res.get("destination_breakdown", [])
        active_sheet_id = sheet_trips_res.get("sheet_id", "")
        active_sheet_url = sheet_trips_res.get("sheet_url", "")
    except Exception:
        all_sheet_trips = []
        ben_trips = []
        thung_trips = []
        partner_trips = []
        active_sheet_count = 26
        dispatched_count = 2
        undispatched_count = 24
        off_sheet_count = 0
        customer_breakdown = []
        origin_breakdown = []
        destination_breakdown = []
        active_sheet_id = ""
        active_sheet_url = ""

    total_daily_km = 0.0
    total_consumed_fuel = 0.0
    running_vehicles_count = 0
    idling_vehicles_count = 0
    stopped_vehicles_count = 0
    suspicious_drain_count = 0
    idling_alerts = []
    continuous_driving_alerts = []

    fuel_table = []
    dual_fuel_norms = []

    for item in gps_fleet:
        clean_plate = item["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
        db_v = v_map.get(clean_plate)
        trailer = db_v.trailer_number if db_v else "—"
        v_type = "Xe Ben" if clean_plate in XE_BEN_PLATES else "Xe Thùng"

        daily_km = item["daily_km"]
        consumed = item["consumed_liters"]
        bagps_norm = item["actual_norm"]
        total_daily_km += daily_km
        total_consumed_fuel += consumed

        # Lấy Định mức dầu Trang Tính (File Đổ Dầu - Bảo Dưỡng) của xe này
        sh_norm_info = sheet_vehicle_norms.get(clean_plate, {})
        sheet_norm_l100km = sh_norm_info.get("sheet_norm_l100km", 0.0)
        sheet_total_liters = sh_norm_info.get("total_liters", 0.0)
        sheet_total_km = sh_norm_info.get("total_km_tracked", 0)
        sheet_fill_count = sh_norm_info.get("fill_count", 0)
        sheet_last_odo = sh_norm_info.get("last_odo", 0)
        sheet_last_fuel_date = sh_norm_info.get("last_fuel_date", "—")
        norm_diff_sheet_vs_gps = round(sheet_norm_l100km - bagps_norm, 1) if (sheet_norm_l100km > 0 and bagps_norm > 0) else 0.0

        speed = item["speed"]
        cont_mins = item.get("continuous_minutes", 0)
        day_mins = item.get("daily_drive_minutes", 0)

        if speed > 0:
            running_vehicles_count += 1
            op_state = "running"
            op_label = f"🟢 Đang chạy ({speed} km/h)"
            vehicle_movement = "Xe đang chạy"
        elif item["status_type"] == "idling":
            idling_vehicles_count += 1
            op_state = "idling"
            op_label = "🟡 Dừng nổ máy"
            vehicle_movement = "Xe đang đỗ (Nổ máy)"
            idling_alerts.append({
                "plate_number": item["plate_number"],
                "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_plate) or item["driver_name"],
                "location": item["address"] or "Kho bãi",
                "warning": "Xe đang dừng nổ máy — Cần theo dõi để tránh hao hụt dầu không tải"
            })
        else:
            stopped_vehicles_count += 1
            op_state = "parked"
            op_label = "⚪ Dừng đỗ (Tắt máy)"
            vehicle_movement = "Xe đang đỗ (Tắt máy)"

        if cont_mins >= 180 or day_mins >= 480:
            continuous_driving_alerts.append({
                "plate_number": item["plate_number"],
                "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_plate) or item["driver_name"],
                "continuous_minutes": cont_mins,
                "daily_drive_minutes": day_mins,
                "speed": speed,
                "address": item["address"] or "Đang lưu thông"
            })

        if item["is_suspicious_drain"]:
            suspicious_drain_count += 1

        driver_full = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_plate) or item["driver_name"]

        row_entry = {
            "plate_number": item["plate_number"],
            "trailer_number": trailer,
            "vehicle_type": v_type,
            "driver_name": driver_full,
            "speed": speed,
            "op_state": op_state,
            "op_label": op_label,
            "vehicle_movement": vehicle_movement,
            "status_text": item["status_text"],
            "status_type": item["status_type"],
            "daily_km": daily_km,
            "consumed_liters": consumed,
            "standard_norm": item["standard_norm"],
            "actual_norm": bagps_norm,
            "bagps_norm": bagps_norm,
            "sheet_norm": sheet_norm_l100km,
            "norm_diff_sheet_vs_gps": norm_diff_sheet_vs_gps,
            "sheet_total_liters": sheet_total_liters,
            "sheet_total_km": sheet_total_km,
            "sheet_fill_count": sheet_fill_count,
            "sheet_last_odo": sheet_last_odo,
            "sheet_last_fuel_date": sheet_last_fuel_date,
            "is_suspicious_drain": item["is_suspicious_drain"],
            "drain_alert_type": item["drain_alert_type"],
            "fuel_liters": item["fuel_liters"],
            "address": item["address"] or "Bãi xe Trường Phát",
            "is_card_swiped": item.get("is_card_swiped", True),
            "card_driver_name": item.get("card_driver_name", "Chưa quẹt thẻ"),
            "card_violation": item.get("card_violation"),
            "continuous_minutes": cont_mins,
            "daily_drive_minutes": day_mins,
            "weekly_drive_minutes": item.get("weekly_drive_minutes", 0),
            "speed_violations": item.get("speed_violations", 0),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude")
        }
        fuel_table.append(row_entry)
        dual_fuel_norms.append({
            "plate_number": item["plate_number"],
            "vehicle_type": v_type,
            "driver_name": driver_full,
            "daily_km_bagps": daily_km,
            "daily_liters_bagps": consumed,
            "bagps_norm_l100km": bagps_norm,
            "sheet_norm_l100km": sheet_norm_l100km,
            "standard_norm_l100km": 35.0 if v_type == "Xe Ben" else 33.0,
            "variance_l100km": norm_diff_sheet_vs_gps,
            "sheet_total_liters": sheet_total_liters,
            "sheet_total_km": sheet_total_km,
            "sheet_fill_count": sheet_fill_count,
            "sheet_last_odo": sheet_last_odo,
            "sheet_last_fuel_date": sheet_last_fuel_date
        })

    fuel_table.sort(key=lambda x: (0 if x["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper() in XE_BEN_PLATES else 1, -x["daily_km"]))
    dual_fuel_norms.sort(key=lambda x: (0 if x["vehicle_type"] == "Xe Ben" else 1, x["plate_number"]))

    # 1.5 CẢNH BÁO XE CHƯA QUẸT THẺ RFID (CẢ ĐANG CHẠY & CÓ CHẠY TRONG NGÀY)
    running_no_card_alerts = []
    daily_no_card_alerts = []
    for item in gps_fleet:
        clean_p = item["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
        drv = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p) or item["driver_name"]
        if item.get("card_violation") == "running_no_card" and item.get("speed", 0) > 0:
            running_no_card_alerts.append({
                "plate_number": item["plate_number"],
                "driver_name": drv,
                "speed": item["speed"],
                "daily_km": item["daily_km"],
                "violation_type": "running_no_card",
                "badge": "ĐANG CHẠY CHƯA QUẸT THẺ",
                "address": item["address"] or "Đang lưu thông",
                "warning": f"Xe đang chạy {item['speed']} km/h ({item['daily_km']} km) nhưng CHƯA QUẸT THẺ RFID"
            })
        elif item.get("card_violation") == "daily_no_card" or (not item.get("is_card_swiped", True) and item.get("daily_km", 0) > 3.0):
            daily_no_card_alerts.append({
                "plate_number": item["plate_number"],
                "driver_name": drv,
                "speed": item.get("speed", 0),
                "daily_km": item["daily_km"],
                "violation_type": "daily_no_card",
                "badge": "CHẠY TRONG NGÀY CHƯA QUẸT THẺ",
                "address": item["address"] or "Bãi xe / Kho hàng",
                "warning": f"Xe đã chạy {item['daily_km']} km trong ngày nhưng tài xế không quẹt thẻ RFID"
            })
    running_no_card_alerts.sort(key=lambda x: -x["speed"])
    daily_no_card_alerts.sort(key=lambda x: -x["daily_km"])
    all_no_card_alerts = running_no_card_alerts + daily_no_card_alerts

    total_vehicles = 26
    active_percent = round((active_sheet_count / total_vehicles * 100), 1) if total_vehicles > 0 else 0.0

    # 2. Phân Tích Top Tuyến Đường Vận Chuyển Hàng Đầu Hôm Nay & Danh Sách Xe Chạy Từng Tuyến
    route_counter = Counter()
    route_trips_map = defaultdict(list)
    for t in all_sheet_trips:
        if t.get("status_code") == "active" and t.get("route"):
            r_clean = t["route"].strip()
            if r_clean and "NGHỈ" not in r_clean.upper() and "SỬA" not in r_clean.upper():
                route_counter[r_clean] += 1
                p_num = t.get("plate_number") or ""
                clean_p = t.get("clean_plate") or p_num.replace("-", "").replace(".", "").replace(" ", "").upper()
                d_name = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p) or t.get("driver_name") or "Tài xế công ty"
                c_name = t.get("customer_name") or "—"
                cargo = t.get("cargo_type") or "—"
                v_type = t.get("vehicle_type") or "Xe Ben"

                route_trips_map[r_clean].append({
                    "plate_number": p_num,
                    "driver_name": d_name,
                    "customer_name": c_name,
                    "cargo_type": cargo,
                    "vehicle_type": v_type,
                    "dispatched": t.get("dispatched", False)
                })

    top_routes = []
    for r, cnt in route_counter.most_common(10):
        t_list = route_trips_map[r]
        vehicle_agg = {}
        main_customer = ""
        main_cargo = ""
        for item in t_list:
            p = item["plate_number"]
            if not p:
                continue
            if not main_customer and item["customer_name"] != "—":
                main_customer = item["customer_name"]
            if not main_cargo and item["cargo_type"] != "—":
                main_cargo = item["cargo_type"]

            if p not in vehicle_agg:
                vehicle_agg[p] = {
                    "plate_number": p,
                    "driver_name": item["driver_name"],
                    "vehicle_type": item["vehicle_type"],
                    "customer_name": item["customer_name"],
                    "cargo_type": item["cargo_type"],
                    "dispatched": item.get("dispatched", False),
                    "trips_count": 0
                }
            vehicle_agg[p]["trips_count"] += 1

        vehicles_list = list(vehicle_agg.values())
        vehicles_list.sort(key=lambda x: -x["trips_count"])

        top_routes.append({
            "route": r,
            "trips_count": cnt,
            "vehicles_count": len(vehicles_list),
            "customer_name": main_customer or "—",
            "cargo_type": main_cargo or "—",
            "vehicles": vehicles_list,
            "plates_str": ", ".join([v["plate_number"] for v in vehicles_list])
        })

    # 3. BẢNG THEO DÕI NHIÊN LIỆU THEO TUẦN & SO SÁNH ĐỊNH MỨC KÉP (BA GPS vs TRANG TÍNH)
    weekly_sheet_stats = sheets_client.get_weekly_dispatch_stats(target_date)
    weekly_fuel_table = []
    total_weekly_km = 0.0
    total_weekly_fuel = 0.0
    suspicious_weekly_count = 0

    for item in gps_fleet:
        p = item["plate_number"]
        clean_p = p.replace("-", "").replace(".", "").replace(" ", "").upper()
        db_v = v_map.get(clean_p)
        v_type = "Xe Ben" if clean_p in XE_BEN_PLATES else "Xe Thùng"
        trailer = db_v.trailer_number if db_v else "—"

        sh_stat = weekly_sheet_stats.get(clean_p, {})
        sheet_trips_week = sh_stat.get("total_trips", 0)
        sheet_km_week = sh_stat.get("estimated_km", 0.0)
        daily_km = item.get("daily_km", 0.0)

        if sheet_km_week > 0:
            weekly_km = round(sheet_km_week, 1)
        elif daily_km > 0:
            weekly_km = round(daily_km * 6.0, 1)
        else:
            weekly_km = 0.0

        avg_daily_km = round(weekly_km / 7.0, 1)

        bagps_norm = item.get("actual_norm") or (34.5 if v_type == "Xe Ben" else 33.0)
        sh_norm_obj = sheet_vehicle_norms.get(clean_p, {})
        sheet_norm_val = sh_norm_obj.get("sheet_norm_l100km", 0.0)
        standard_norm = 35.0 if v_type == "Xe Ben" else 33.0

        weekly_liters = round((weekly_km * bagps_norm) / 100.0, 1) if weekly_km > 0 else 0.0
        total_weekly_km += weekly_km
        total_weekly_fuel += weekly_liters

        diff = round((sheet_norm_val - bagps_norm) if sheet_norm_val > 0 else (bagps_norm - standard_norm), 1)
        if weekly_km == 0:
            status_label = "⚪ Xe nghỉ bãi"
            status_type = "low"
        elif sheet_norm_val > 42.0 or bagps_norm > 42.0:
            status_label = "🟡 Cần kiểm tra ĐM"
            status_type = "warning"
            suspicious_weekly_count += 1
        else:
            status_label = "🟢 Định mức chuẩn"
            status_type = "normal"

        weekly_fuel_table.append({
            "plate_number": p,
            "trailer_number": trailer,
            "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p) or item["driver_name"],
            "vehicle_type": v_type,
            "weekly_trips": sheet_trips_week,
            "weekly_km": weekly_km,
            "avg_daily_km": avg_daily_km,
            "weekly_liters": weekly_liters,
            "actual_norm": bagps_norm,
            "bagps_norm": bagps_norm,
            "sheet_norm": sheet_norm_val,
            "sheet_total_liters": sh_norm_obj.get("total_liters", 0.0),
            "sheet_total_km": sh_norm_obj.get("total_km_tracked", 0),
            "standard_norm": standard_norm,
            "diff": diff,
            "status_label": status_label,
            "status_type": status_type
        })

    weekly_fuel_table.sort(key=lambda x: (0 if x["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper() in XE_BEN_PLATES else 1, -x["weekly_km"]))

    avg_weekly_fleet_norm = round((total_weekly_fuel / total_weekly_km * 100), 1) if total_weekly_km > 0 else 34.2
    weekly_summary = {
        "total_weekly_km": round(total_weekly_km, 1),
        "total_weekly_fuel": round(total_weekly_fuel, 1),
        "avg_daily_km": round(total_weekly_km / 7.0, 1),
        "avg_fleet_norm": avg_weekly_fleet_norm,
        "sheet_fleet_avg_norm": sheet_fuel_summary.get("fleet_avg_norm_l100km", 37.8),
        "suspicious_trucks_count": suspicious_weekly_count,
        "week_range": f"{(target_date - timedelta(days=6)).strftime('%d/%m')} - {target_date.strftime('%d/%m/%Y')}",
        "records": weekly_fuel_table
    }

    top_drivers_weekly = [
        {
            "rank": idx + 1,
            "driver_name": item["driver_name"],
            "plate_number": item["plate_number"],
            "weekly_km": item["weekly_km"],
            "avg_daily_km": item["avg_daily_km"],
            "actual_norm": item["actual_norm"],
            "sheet_norm": item["sheet_norm"],
            "status_label": item["status_label"]
        }
        for idx, item in enumerate(weekly_fuel_table[:5])
    ]

    # 4. Thống Kê Phạt Nguội Toàn Đoàn Xe
    fines_summary = traffic_fines_service.get_summary()

    # 5. Expiring docs kết hợp trực tiếp từ Trang Tính GIẤY TỜ XE + ĐĂNG KIỂM
    expiring_docs = []
    for doc_row in wb_maint_fuel.get("documents", {}).get("road_permits", []):
        st = doc_row.get("status", "")
        if "SẮP" in st.upper() or "GẦN" in st.upper() or "QUÁ" in st.upper():
            expiring_docs.append({
                "name": f"Xe {doc_row['plate_number']}",
                "type": "GĐĐ Đầu Kéo / Moóc",
                "date": doc_row.get("head_expiry", "—"),
                "expired": "QUÁ" in st.upper()
            })
    for reg_row in wb_maint_fuel.get("documents", {}).get("registrations", []):
        st = reg_row.get("status", "")
        if "SẮP" in st.upper() or "GẦN" in st.upper() or "QUÁ" in st.upper():
            expiring_docs.append({
                "name": f"Xe {reg_row['plate_number']}",
                "type": "Đăng kiểm",
                "date": reg_row.get("head_reg_expiry", "—"),
                "expired": "QUÁ" in st.upper()
            })

    norm_chart_data = []
    for item in fuel_table[:15]:
        if item["daily_km"] > 0 or item["sheet_norm"] > 0:
            norm_chart_data.append({
                "plate": item["plate_number"],
                "actual_norm": item["actual_norm"],
                "bagps_norm": item["bagps_norm"],
                "sheet_norm": item["sheet_norm"],
                "standard_norm": 35.0,
                "daily_km": item["daily_km"],
                "consumed_liters": item["consumed_liters"]
            })

    km_chart_data = [{
        "plate": item["plate_number"],
        "km": item["daily_km"]
    } for item in fuel_table if item["daily_km"] > 0][:15]

    return {
        "selected_date": target_date.strftime("%Y-%m-%d"),
        "selected_date_display": target_date.strftime("%d/%m/%Y"),
        "is_today": is_today,
        "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        "active_sheet_id": active_sheet_id,
        "active_sheet_url": active_sheet_url,
        "total_vehicles": total_vehicles,
        "active_percent": active_percent,
        "active_vehicles_count": active_sheet_count,
        "dispatched_count": dispatched_count,
        "undispatched_count": undispatched_count,
        "off_vehicles_count": off_sheet_count,
        "ben_active_count": len([t for t in ben_trips if t.get("status_code") == "active"]),
        "thung_active_count": len([t for t in thung_trips if t.get("status_code") == "active"]),
        "partner_trips": partner_trips,
        "partner_trips_count": len(partner_trips),
        "running_vehicles_count": running_vehicles_count,
        "idling_vehicles_count": idling_vehicles_count,
        "stopped_vehicles_count": stopped_vehicles_count,
        "total_daily_km": round(total_daily_km, 1),
        "total_consumed_fuel": round(total_consumed_fuel, 1),
        "suspicious_drain_count": suspicious_drain_count,
        "standard_norm": 35.0,
        "sheet_fleet_avg_norm": sheet_fuel_summary.get("fleet_avg_norm_l100km", 37.8),
        "sheet_fuel_summary": sheet_fuel_summary,
        "sheet_overview": sheet_overview,
        "fuel_table": fuel_table,
        "dual_fuel_norms": dual_fuel_norms,
        "norm_chart_data": norm_chart_data,
        "km_chart_data": km_chart_data,
        "expiring_documents": expiring_docs,
        "top_routes": top_routes,
        "customer_breakdown": customer_breakdown,
        "origin_breakdown": origin_breakdown,
        "destination_breakdown": destination_breakdown,
        "weekly_fuel_summary": weekly_summary,
        "top_drivers_weekly": top_drivers_weekly,
        "fines_summary": fines_summary,
        "idling_alerts": idling_alerts,
        "running_no_card_alerts": running_no_card_alerts,
        "running_no_card_count": len(running_no_card_alerts),
        "daily_no_card_alerts": daily_no_card_alerts,
        "daily_no_card_count": len(daily_no_card_alerts),
        "all_no_card_alerts": all_no_card_alerts,
        "all_no_card_count": len(all_no_card_alerts),
        "continuous_driving_alerts": continuous_driving_alerts
    }
