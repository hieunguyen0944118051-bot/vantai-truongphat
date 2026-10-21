from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

import auth
import models
from fleet import FLEET_BY_CLEAN, clean_plate
from gps_service import gps_client

router = APIRouter(prefix="/api/gps", tags=["GPS Telematics"])


def _with_fleet_info(data):
    for item in data:
        info = FLEET_BY_CLEAN.get(clean_plate(item["plate_number"]), {})
        item["trailer_number"] = info.get("trailer_number")
        item["vehicle_type"] = info.get("vehicle_type", "—")
    return data


@router.get("/live")
def get_live_gps(current_user: models.User = Depends(auth.get_current_user)):
    """Vị trí / km / thẻ lái xe từng xe, kèm giờ GPS gốc. Không có ODO ước tính, không có định mức dầu."""
    data = _with_fleet_info(gps_client.fetch_live_fleet())
    return {
        "success": True,
        "count": len(data),
        "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        "status": gps_client.status(),
        "data": data,
    }


@router.get("/status")
def get_gps_status(current_user: models.User = Depends(auth.get_current_user)):
    return gps_client.status()


@router.get("/detail/{plate_code}")
def get_vehicle_detail(plate_code: str, lng: float, lat: float,
                       current_user: models.User = Depends(auth.get_current_user)):
    """Mức nhiên liệu do thiết bị Bình Anh báo (chỉ xe có cảm biến dầu)."""
    try:
        return {"success": True, "data": gps_client.fetch_vehicle_fuel_detail(plate_code, lng, lat)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không lấy được dữ liệu Bình Anh: {e}")
