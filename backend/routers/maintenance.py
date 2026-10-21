from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import models, schemas, auth
from database import get_db
from sheets_service import sheets_client

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])

@router.get("/oil")
def get_oil_maintenance_status(current_user: models.User = Depends(auth.get_current_user)):
    """Bảng thay nhớt 15.000 km từ tab 'BẢO DƯỠNG XE + MOOC' (Google Sheets).
    Đọc lỗi -> báo lỗi, KHÔNG tự gán 'Còn xa' từ dữ liệu cũ trong DB."""
    rows = sheets_client.fetch_maintenance_sheet()
    if not rows:
        raise HTTPException(status_code=502, detail="Không đọc được bảng bảo dưỡng từ Google Sheets. Thử lại sau hoặc mở file Sheets.")
    return rows

@router.get("/tires/summary")
def get_tires_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    records = db.query(models.TireRecord).all()
    v_map = {}
    for r in records:
        v_p = r.vehicle.plate_number if r.vehicle else "Khác"
        if v_p not in v_map:
            v_map[v_p] = {"plate_number": v_p, "q1": 0, "q2": 0, "q3": 0, "q4": 0, "total_tires": 0, "total_cost": 0.0}
        
        q = (r.record_date.month - 1) // 3 + 1
        v_map[v_p][f"q{q}"] += r.tire_count or 0
        v_map[v_p]["total_tires"] += r.tire_count or 0
        v_map[v_p]["total_cost"] += r.total_cost or 0

    summary = list(v_map.values())
    total_tires_all = sum(s["total_tires"] for s in summary)
    total_cost_all = sum(s["total_cost"] for s in summary)

    return {
        "summary": summary,
        "total_tires_all": total_tires_all,
        "total_cost_all": total_cost_all
    }

@router.get("/tarps")
def get_tarp_records(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.TarpRecord).order_by(models.TarpRecord.record_date.desc()).all()
