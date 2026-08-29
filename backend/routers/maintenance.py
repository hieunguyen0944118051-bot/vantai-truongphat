from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import models, schemas, auth
from database import get_db
from sheets_service import sheets_client

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])

@router.get("/oil")
def get_oil_maintenance_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Returns exact oil maintenance tracking from Google Sheet tab 'BẢO DƯỠNG XE + MOOC' (gid=1041617404).
    """
    try:
        sheet_data = sheets_client.fetch_maintenance_sheet()
        if sheet_data:
            return sheet_data
    except Exception as e:
        print("Error fetching maintenance sheet:", e)

    # Fallback to DB if Google Sheets is unreachable
    vehicles = db.query(models.Vehicle).all()
    res = []
    for i, v in enumerate(vehicles, 1):
        res.append({
            "stt": i,
            "plate_number": v.plate_number,
            "norm_km": "15.000",
            "last_km": v.oil_last_km or "—",
            "last_date": v.oil_last_date.strftime("%d/%m/%Y") if v.oil_last_date else "—",
            "current_km": v.current_odometer or "—",
            "due_km": (v.oil_last_km + 15000) if v.oil_last_km else "—",
            "remaining_km": "—",
            "status": "Còn xa",
            "notes": v.notes or ""
        })
    return res

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
        v_map[v_p][f"q{q}"] += r.quantity
        v_map[v_p]["total_tires"] += r.quantity
        v_map[v_p]["total_cost"] += r.total_cost

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
