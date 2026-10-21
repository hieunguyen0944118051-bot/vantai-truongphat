from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db
from fleet import FLEET, clean_plate
from gps_service import gps_client

router = APIRouter(prefix="/api/drivers", tags=["Drivers"])

# CCCD / số GPLX không còn ghi trong code; chỉ admin xem được qua API.
PII_FIELDS = ("national_id", "national_id_expiry", "license_number", "license_expiry")


def _mask(d: models.Driver, user: models.User):
    out = schemas.DriverOut.model_validate(d).model_dump()
    if user.role != "admin":
        for f in PII_FIELDS:
            out[f] = None
    return out


@router.get("/activity")
def get_drivers_daily_activity(current_user: models.User = Depends(auth.get_current_user)):
    """Tài xế theo xe + hoạt động hôm nay từ GPS Bình Anh (km, trạng thái, thẻ lái xe).
    Đã bỏ điểm năng suất / A+ / nhận xét mẫu vì không có cơ sở số liệu."""
    gps_map = {clean_plate(g["plate_number"]): g for g in gps_client.fetch_live_fleet()}
    drivers = []
    for plate, typ, mooc, name, phone in FLEET:
        g = gps_map.get(clean_plate(plate), {})
        speed = g.get("speed", 0)
        drivers.append({
            "full_name": name or "Chưa phân công",
            "phone": phone,
            "vehicle_plate": plate,
            "vehicle_type": "Xe Ben" if typ == "ben" else "Xe Thùng",
            "trailer_number": mooc,
            "daily_km": g.get("daily_km", 0.0),
            "speed": speed,
            "movement_state": "🟢 Đang chạy" if speed > 0 else ("🟡 Dừng nổ máy" if g.get("status_type") == "idling" else "⚪ Đậu bãi"),
            "current_address": g.get("address") or "",
            "gps_time": g.get("gps_time"),
            "is_stale": g.get("is_stale", True),
            "is_card_swiped": g.get("is_card_swiped", False),
            "card_driver_name": g.get("card_driver_name", "Chưa quẹt thẻ"),
            "card_violation": g.get("card_violation"),
        })
    drivers.sort(key=lambda x: x["daily_km"], reverse=True)

    no_card_alerts = []
    for d in drivers:
        if d["card_violation"]:
            running = d["card_violation"] == "running_no_card"
            no_card_alerts.append({
                "plate_number": d["vehicle_plate"], "driver_assigned": d["full_name"], "phone": d["phone"],
                "speed": d["speed"], "daily_km": d["daily_km"], "address": d["current_address"],
                "gps_time": d["gps_time"], "violation_type": d["card_violation"],
                "violation_title": "🚨 ĐANG CHẠY KHÔNG QUẸT THẺ" if running else "⚠️ ĐÃ CHẠY TRONG NGÀY NHƯNG CHƯA QUẸT THẺ",
                "severity": "danger" if running else "warning",
            })
    no_card_alerts.sort(key=lambda x: (x["violation_type"] != "running_no_card", -x["speed"], -x["daily_km"]))

    return {
        "source": "GPS Bình Anh",
        "gps_status": gps_client.status(),
        "total_drivers": sum(1 for d in drivers if d["full_name"] != "Chưa phân công"),
        "active_today": sum(1 for d in drivers if d["daily_km"] > 0),
        "no_card_count": len(no_card_alerts),
        "no_card_running_count": sum(1 for x in no_card_alerts if x["violation_type"] == "running_no_card"),
        "no_card_daily_count": sum(1 for x in no_card_alerts if x["violation_type"] == "daily_no_card"),
        "no_card_alerts": no_card_alerts,
        "drivers": drivers,
    }

@router.get("", response_model=List[schemas.DriverOut])
def get_drivers(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return [_mask(d, current_user) for d in db.query(models.Driver).all()]

@router.post("", response_model=schemas.DriverOut)
def create_driver(data: schemas.DriverCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["admin", "manager"]))):
    driver = models.Driver(**data.dict())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver

@router.get("/{id}", response_model=schemas.DriverOut)
def get_driver(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    d = db.query(models.Driver).filter(models.Driver.id == id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài xế")
    return _mask(d, current_user)

@router.put("/{id}", response_model=schemas.DriverOut)
def update_driver(id: int, data: schemas.DriverUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["admin", "manager"]))):
    d = db.query(models.Driver).filter(models.Driver.id == id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài xế")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d

@router.delete("/{id}")
def delete_driver(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["admin"]))):
    d = db.query(models.Driver).filter(models.Driver.id == id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài xế")
    db.delete(d)
    db.commit()
    return {"message": "Đã xóa tài xế thành công"}
