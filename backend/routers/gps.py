from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, date
import models, schemas, auth
from database import get_db
from gps_service import gps_client

router = APIRouter(prefix="/api/gps", tags=["GPS Telematics"])

@router.get("/live")
def get_live_gps_telemetry(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    try:
        data = gps_client.fetch_live_fleet()
        # Merge with trailers in database
        vehicles = db.query(models.Vehicle).all()
        v_map = {v.plate_number.replace("-", "").replace(".", "").replace(" ", "").upper(): v for v in vehicles}

        for item in data:
            clean_plate = item["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
            db_v = v_map.get(clean_plate)
            if db_v:
                item["db_id"] = db_v.id
                item["trailer_number"] = db_v.trailer_number
                item["vehicle_type"] = db_v.vehicle_type
                # Update current odometer with cumulative or estimation
                if item["daily_km"] > 0 and db_v.current_odometer:
                    item["estimated_odometer"] = db_v.current_odometer + item["daily_km"]
                else:
                    item["estimated_odometer"] = db_v.current_odometer
            else:
                item["trailer_number"] = None
                item["vehicle_type"] = "Xe Đầu Kéo"
                item["estimated_odometer"] = None

        return {
            "success": True,
            "count": len(data),
            "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kết nối Bình Anh GPS: {str(e)}")

@router.post("/sync")
def sync_gps_to_database(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    try:
        data = gps_client.fetch_live_fleet()
        vehicles = db.query(models.Vehicle).all()
        v_map = {v.plate_number.replace("-", "").replace(".", "").replace(" ", "").upper(): v for v in vehicles}

        updated_count = 0
        total_daily_km = 0.0

        for item in data:
            clean_plate = item["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
            db_v = v_map.get(clean_plate)
            if db_v:
                daily_km = item["daily_km"]
                total_daily_km += daily_km
                # If vehicle was running, ensure status is active
                if item["speed"] > 0:
                    db_v.status = "active"
                
                # Fetch fuel for vehicles that are running or idling
                if item["speed"] > 0 or item["status_type"] == "running":
                    try:
                        fuel_res = gps_client.fetch_vehicle_fuel_detail(item["plate_code"], item["longitude"], item["latitude"])
                        if fuel_res.get("liters"):
                            item["fuel_liters"] = fuel_res["liters"]
                            item["fuel_percent"] = fuel_res["percent"]
                    except Exception:
                        pass

                updated_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"Đã đồng bộ thành công dữ liệu từ Bình Anh GPS cho {updated_count} xe!",
            "total_vehicles": len(data),
            "running_vehicles": sum(1 for x in data if x["speed"] > 0),
            "total_daily_km": round(total_daily_km, 1),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đồng bộ GPS: {str(e)}")

@router.get("/detail/{plate_code}")
def get_vehicle_detail(
    plate_code: str,
    lng: float = 106.5796,
    lat: float = 10.6869,
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        res = gps_client.fetch_vehicle_fuel_detail(plate_code, lng, lat)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fuel-analysis")
def get_fuel_analysis(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    try:
        data = gps_client.fetch_live_fleet()
        vehicles = db.query(models.Vehicle).all()
        v_map = {v.plate_number.replace("-", "").replace(".", "").replace(" ", "").upper(): v for v in vehicles}

        total_daily_km = 0.0
        total_consumed_liters = 0.0
        suspicious_list = []

        for item in data:
            clean_plate = item["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
            db_v = v_map.get(clean_plate)
            if db_v:
                item["trailer_number"] = db_v.trailer_number
                item["vehicle_type"] = db_v.vehicle_type
            else:
                item["trailer_number"] = None
                item["vehicle_type"] = "Xe Đầu Kéo"

            total_daily_km += item["daily_km"]
            total_consumed_liters += item["consumed_liters"]

            if item["is_suspicious_drain"]:
                suspicious_list.append(item)

        active_vehicles = [x for x in data if x["daily_km"] > 0]
        avg_fleet_norm = round(total_consumed_liters / total_daily_km * 100.0, 1) if total_daily_km > 0 else 40.0

        return {
            "success": True,
            "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "summary": {
                "total_vehicles": len(data),
                "active_vehicles": len(active_vehicles),
                "total_daily_km": round(total_daily_km, 1),
                "total_consumed_liters": round(total_consumed_liters, 1),
                "standard_norm": 40.0,
                "avg_fleet_norm": avg_fleet_norm,
                "suspicious_drain_count": len(suspicious_list)
            },
            "suspicious_vehicles": suspicious_list,
            "vehicles": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích nhiên liệu: {str(e)}")

