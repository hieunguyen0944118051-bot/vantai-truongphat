from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])

def calc_doc_status(exp_date: Optional[date], today: date):
    if not exp_date:
        return {"date": None, "days": None, "status": "none", "label": "Chưa có"}
    days = (exp_date - today).days
    if days < 0:
        status = "expired"
        label = f"Quá hạn {abs(days)}N"
    elif days <= 14:
        status = "red"
        label = f"Đỏ: {days}N"
    elif days <= 30:
        status = "yellow"
        label = f"Vàng: {days}N"
    else:
        status = "green"
        label = f"Còn {days}N"
    return {
        "date": exp_date.strftime("%d/%m/%Y"),
        "days": days,
        "status": status,
        "label": label
    }

@router.get("/grouped")
def get_grouped_vehicles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Returns vehicles cleanly separated into 2 groups:
    - 15 Xe Ben (Khúc trên)
    - 11 Xe Thùng (Khúc dưới)
    Matching Google Sheets document tracking format.
    """
    today = date.today()
    all_vehicles = db.query(models.Vehicle).all()

    ben_list = []
    thung_list = []

    for v in all_vehicles:
        item = {
            "id": v.id,
            "plate_number": v.plate_number,
            "trailer_number": v.trailer_number or "—",
            "vehicle_type": v.vehicle_type,
            "payload_capacity": v.payload_capacity,
            "status": v.status,
            "gdd_head": calc_doc_status(v.gdd_head_expiry, today),
            "gdd_trailer": calc_doc_status(v.gdd_trailer_expiry, today),
            "registration": calc_doc_status(v.registration_expiry, today),
            "insurance": calc_doc_status(v.insurance_expiry, today),
            "notes": v.notes or ""
        }
        if v.vehicle_type == "Xe Ben":
            ben_list.append(item)
        else:
            thung_list.append(item)

    return {
        "success": True,
        "ben_vehicles": ben_list,
        "thung_vehicles": thung_list,
        "total_ben": len(ben_list),
        "total_thung": len(thung_list),
        "total_all": len(all_vehicles)
    }

@router.get("", response_model=List[schemas.VehicleOut])
def get_vehicles(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.Vehicle)
    if status:
        query = query.filter(models.Vehicle.status == status)
    if search:
        query = query.filter(models.Vehicle.plate_number.ilike(f"%{search}%"))
    return query.order_by(models.Vehicle.plate_number).all()

@router.get("/expiring")
def get_expiring_vehicles(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    today = date.today()
    target_date = today + timedelta(days=days)
    
    vehicles = db.query(models.Vehicle).all()
    expiring_list = []
    
    for v in vehicles:
        alerts = []
        if v.registration_expiry and v.registration_expiry <= target_date:
            alerts.append({"type": "Đăng kiểm", "expiry": v.registration_expiry, "expired": v.registration_expiry < today})
        if v.insurance_expiry and v.insurance_expiry <= target_date:
            alerts.append({"type": "Bảo hiểm", "expiry": v.insurance_expiry, "expired": v.insurance_expiry < today})
        if v.badge_expiry and v.badge_expiry <= target_date:
            alerts.append({"type": "Phù hiệu", "expiry": v.badge_expiry, "expired": v.badge_expiry < today})
        
        if alerts:
            expiring_list.append({
                "vehicle_id": v.id,
                "plate_number": v.plate_number,
                "alerts": alerts
            })
    return expiring_list

@router.get("/{vehicle_id}", response_model=schemas.VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    v = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Không tìm thấy xe")
    return v
