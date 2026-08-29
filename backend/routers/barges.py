from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/barges", tags=["Barges"])

@router.get("", response_model=List[schemas.BargeOut])
def get_barges(
    ownership_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.Barge)
    if ownership_type:
        query = query.filter(models.Barge.ownership_type == ownership_type)
    if status:
        query = query.filter(models.Barge.status == status)
    return query.order_by(models.Barge.name).all()

@router.get("/{barge_id}", response_model=schemas.BargeOut)
def get_barge(barge_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    b = db.query(models.Barge).filter(models.Barge.id == barge_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Không tìm thấy sà lan")
    return b

@router.post("", response_model=schemas.BargeOut)
def create_barge(
    b_in: schemas.BargeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["admin", "manager", "staff"]))
):
    existing = db.query(models.Barge).filter(models.Barge.name == b_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên sà lan đã tồn tại")
    b = models.Barge(**b_in.dict())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b

@router.put("/{barge_id}", response_model=schemas.BargeOut)
def update_barge(
    barge_id: int,
    b_in: schemas.BargeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["admin", "manager", "staff"]))
):
    b = db.query(models.Barge).filter(models.Barge.id == barge_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Không tìm thấy sà lan")
    for key, val in b_in.dict(exclude_unset=True).items():
        setattr(b, key, val)
    db.commit()
    db.refresh(b)
    return b

@router.delete("/{barge_id}")
def delete_barge(
    barge_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["admin", "manager"]))
):
    b = db.query(models.Barge).filter(models.Barge.id == barge_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Không tìm thấy sà lan")
    db.delete(b)
    db.commit()
    return {"message": "Đã xóa sà lan thành công"}
