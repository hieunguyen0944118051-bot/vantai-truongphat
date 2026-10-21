from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import date
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/fuel", tags=["Fuel"])

@router.get("", response_model=List[schemas.FuelRecordOut])
def get_fuel_records(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    vehicle_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.FuelRecord).options(joinedload(models.FuelRecord.vehicle))
    if start_date:
        query = query.filter(models.FuelRecord.record_date >= start_date)
    if end_date:
        query = query.filter(models.FuelRecord.record_date <= end_date)
    if vehicle_id:
        query = query.filter(models.FuelRecord.vehicle_id == vehicle_id)
    return query.order_by(models.FuelRecord.record_date.desc(), models.FuelRecord.id.desc()).all()

@router.get("/summary")
def get_fuel_summary(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month

    records = db.query(
        models.Vehicle.plate_number,
        func.sum(models.FuelRecord.liters).label("total_liters"),
        func.sum(models.FuelRecord.total_cost).label("total_cost"),
        func.count(models.FuelRecord.id).label("fill_count")
    ).join(models.Vehicle, models.FuelRecord.vehicle_id == models.Vehicle.id)     .filter(func.strftime("%Y", models.FuelRecord.record_date) == str(target_year))     .filter(func.strftime("%m", models.FuelRecord.record_date) == f"{target_month:02d}")     .group_by(models.Vehicle.plate_number).all()

    return [{
        "plate_number": r[0],
        "total_liters": float(r[1] or 0),
        "total_cost": float(r[2] or 0),
        "fill_count": r[3]
    } for r in records]

@router.post("", response_model=schemas.FuelRecordOut)
def create_fuel_record(
    f_in: schemas.FuelRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    f_data = f_in.dict()
    if not f_data.get("total_cost") or f_data["total_cost"] == 0:
        f_data["total_cost"] = f_data["liters"] * f_data["price_per_liter"]
    
    rec = models.FuelRecord(**f_data, created_by=current_user.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

@router.put("/{record_id}", response_model=schemas.FuelRecordOut)
def update_fuel_record(
    record_id: int,
    f_in: schemas.FuelRecordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    rec = db.query(models.FuelRecord).filter(models.FuelRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
    for k, v in f_in.dict(exclude_unset=True).items():
        setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec

@router.delete("/{record_id}")
def delete_fuel_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["admin", "manager"]))
):
    rec = db.query(models.FuelRecord).filter(models.FuelRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
    db.delete(rec)
    db.commit()
    return {"message": "Đã xóa bản ghi nhiên liệu"}
