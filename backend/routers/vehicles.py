from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import models, schemas, auth
from fleet import FLEET
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

@router.get("/fleet")
def get_fleet(current_user: models.User = Depends(auth.get_current_user)):
    """Danh sách xe – romoóc – tài xế phụ trách (nguồn duy nhất: fleet.py).
    Hạn giấy tờ tạm ẩn: dữ liệu DB chỉ đến 08/2026 và đã sai; GĐ2 đọc tab GIẤY TỜ XE trên Google Sheets."""
    vehicles = [{"plate_number": p, "vehicle_type": "Xe Ben" if t == "ben" else "Xe Thùng",
                 "trailer_number": m, "driver_name": n or None, "phone": ph or None}
                for p, t, m, n, ph in FLEET]
    ben = sum(1 for v in vehicles if v["vehicle_type"] == "Xe Ben")
    return {"vehicles": vehicles, "total": len(vehicles), "total_ben": ben, "total_thung": len(vehicles) - ben,
            "source": "Danh sách xe 12/08/2026 (fleet.py)"}

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

@router.get("/{vehicle_id}", response_model=schemas.VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    v = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Không tìm thấy xe")
    return v
