from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import models, auth
from traffic_fines_service import traffic_fines_service

router = APIRouter(prefix="/api/fines", tags=["Traffic Fines"])

@router.get("")
def get_all_fines(current_user: models.User = Depends(auth.get_current_user)):
    """
    Lấy danh sách kết quả tra cứu phạt nguội toàn đoàn xe.
    """
    return {
        "success": True,
        "summary": traffic_fines_service.get_summary(),
        "data": traffic_fines_service.get_all_fines()
    }

@router.get("/summary")
def get_fines_summary(current_user: models.User = Depends(auth.get_current_user)):
    """
    Lấy tóm tắt chỉ số phạt nguội cho Dashboard.
    """
    return {
        "success": True,
        "summary": traffic_fines_service.get_summary()
    }

@router.post("/check-all")
def check_all_fines(current_user: models.User = Depends(auth.require_role(["admin", "manager"]))):
    """
    Kích hoạt quét phạt nguội tự động cho toàn bộ 26 xe đầu kéo.
    """
    result = traffic_fines_service.check_all_fleet()
    return result

@router.post("/{plate_number}/resolve")
def resolve_fine(
    plate_number: str,
    current_user: models.User = Depends(auth.require_role(["admin", "manager"]))
):
    """
    Đánh dấu đã nộp phạt thành công cho xe.
    """
    ok, msg = traffic_fines_service.resolve_violation(plate_number)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "message": msg}
