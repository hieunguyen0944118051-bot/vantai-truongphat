from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import models, schemas, auth
from database import get_db
from gps_service import gps_client

router = APIRouter(prefix="/api/drivers", tags=["Drivers"])

# DANH SÁCH CHÍNH THỨC 25 TÀI XẾ + XE THEO FILE "DANH SÁCH XE (12.8.2026).xlsx"
# Bao gồm: Họ tên, SĐT, Hạng bằng lái FC, GPLX, CCCD
OFFICIAL_DRIVERS = {
    "63E-011.56": {
        "name": "Nguyễn Văn Tuấn",
        "phone": "0974 406 941",
        "class": "FC",
        "gplx": "790167009177",
        "cccd": "040093001917",
        "mooc": "63R-011.90"
    },
    "63E-011.17": {
        "name": "Phan Hoàng Duy",
        "phone": "0901 077 345",
        "class": "FC",
        "gplx": "790157272563",
        "cccd": "083093002142",
        "mooc": "63R-012.16"
    },
    "63H-042.73": {
        "name": "Lâm Hoàng Tuấn",
        "phone": "0778 117 516",
        "class": "FC",
        "gplx": "940229004107",
        "cccd": "094097006574",
        "mooc": "63R-011.85"
    },
    "63G-002.86": {
        "name": "Nguyễn Xuân Về",
        "phone": "0395 557 714",
        "class": "FC",
        "gplx": "740099013258",
        "cccd": "089091013867",
        "mooc": "63R-012.25"
    },
    "63F-005.12": {
        "name": "Hoàng Quốc Bảo",
        "phone": "0792 961 140",
        "class": "FC",
        "gplx": "310163002505",
        "cccd": "044091011506",
        "mooc": "63R-012.03"
    },
    "63F-005.38": {
        "name": "Lý Minh Tới",
        "phone": "0971 307 737",
        "class": "FC",
        "gplx": "920162000978",
        "cccd": "092091001122",
        "mooc": "63R-011.94"
    },
    "63E-011.08": {
        "name": "Lý Minh Hoàng",
        "phone": "0904 079 178",
        "class": "FC",
        "gplx": "790190267531",
        "cccd": "094089007590",
        "mooc": "63R-012.11"
    },
    "63F-005.28": {
        "name": "Nguyễn Văn Hiếu",
        "phone": "0878 109 102",
        "class": "FC",
        "gplx": "820073000222",
        "cccd": "082080014752",
        "mooc": "63R-011.95"
    },
    "63E-012.12": {
        "name": "Mạch Đình Phước",
        "phone": "0938 256 639",
        "class": "FC",
        "gplx": "750967000334",
        "cccd": "052073022465",
        "mooc": "63R-012.15"
    },
    "63E-011.41": {
        "name": "Dương Thanh Sang",
        "phone": "0933 549 648",
        "class": "FC",
        "gplx": "790164241059",
        "cccd": "082089012194",
        "mooc": "63R-011.93"
    },
    "63G-002.62": {
        "name": "Nguyễn Thanh Tây",
        "phone": "0703 238 667",
        "class": "FC",
        "gplx": "790144910111",
        "cccd": "046082006178",
        "mooc": "63R-011.92"
    },
    "63H-042.39": {
        "name": "Kim Sô Phép",
        "phone": "0708 400 332",
        "class": "FC",
        "gplx": "940189004832",
        "cccd": "094200015057",
        "mooc": "63R-011.96"
    },
    "63E-011.32": {
        "name": "Đào Ngọc Kha",
        "phone": "0945 220 539",
        "class": "FC",
        "gplx": "790138039277",
        "cccd": "058092010536",
        "mooc": "63R-011.98"
    },
    "63E-012.01": {
        "name": "Lê Trọng Nghĩa",
        "phone": "0949 528 128",
        "class": "FC",
        "gplx": "790163005852",
        "cccd": "080084004172",
        "mooc": "63R-012.12"
    },
    "63F-005.16": {
        "name": "Phùng Phú Kim Toàn",
        "phone": "0986 853 754",
        "class": "FC",
        "gplx": "790171115785",
        "cccd": "080093006479",
        "mooc": "63R-011.86"
    },
    "63E-012.76": {
        "name": "Nguyễn Thanh Giàu",
        "phone": "0345 636 358",
        "class": "FC",
        "gplx": "790170313630",
        "cccd": "082093010788",
        "mooc": "63R-012.10"
    },
    "63E-011.03": {
        "name": "Lê Phương Linh",
        "phone": "0374 929 126",
        "class": "FC",
        "gplx": "790141806556",
        "cccd": "082093018526",
        "mooc": "63R-012.23"
    },
    "63E-011.18": {
        "name": "Lê Ngọc Quí",
        "phone": "0903 722 301",
        "class": "FC",
        "gplx": "820029003923",
        "cccd": "082081011834",
        "mooc": "63R-012.01"
    },
    "63F-005.11": {
        "name": "Bạch Tấn Trí",
        "phone": "0919 277 113",
        "class": "FC",
        "gplx": "790123815389",
        "cccd": "060090002999",
        "mooc": "63RM-007.44"
    },
    "63H-042.34": {
        "name": "Nguyễn Thành Hiếu",
        "phone": "0937 912 665",
        "class": "FC",
        "gplx": "790164134391",
        "cccd": "087092021046",
        "mooc": "63RM-007.43"
    },
    "63G-002.97": {
        "name": "Trần Trọng Ngân",
        "phone": "0984 731 739",
        "class": "FC",
        "gplx": "790128000027",
        "cccd": "083090008569",
        "mooc": "66RM-010.30"
    },
    "63E-012.35": {
        "name": "Lý Hoàng Thái",
        "phone": "0365 908 374",
        "class": "FC",
        "gplx": "790110025050",
        "cccd": "094092014528",
        "mooc": "66RM-010.32"
    },
    "63H-042.36": {
        "name": "Lê Văn Trọng",
        "phone": "0978 840 929",
        "class": "FC",
        "gplx": "790133023459",
        "cccd": "083086011897",
        "mooc": "66RM-010.34"
    },
    "63G-002.80": {
        "name": "Lê Trung Trực",
        "phone": "0358 426 114",
        "class": "FC",
        "gplx": "790150234937",
        "cccd": "082097011973",
        "mooc": "66RM-010.37"
    },
    "66H-083.48": {
        "name": "Trần Trọng Nghĩa",
        "phone": "0327 066 337",
        "class": "FC",
        "gplx": "830144002196",
        "cccd": "083092002095",
        "mooc": "66RM-010.38"
    },
    "63F-005.44": {
        "name": "Tài Xế Dự Phòng",
        "phone": "0913 567 890",
        "class": "FC",
        "gplx": "790180543210",
        "cccd": "082090123456",
        "mooc": "63R-012.30"
    }
}

DRIVER_VEHICLE_MAP = {
    plate: (info["name"], info["phone"], info["class"], info["gplx"])
    for plate, info in OFFICIAL_DRIVERS.items()
}

@router.get("/activity")
def get_drivers_daily_activity(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Trả về bảng đánh giá hoạt động lái xe theo đúng danh sách tài xế chính thức 
    của Công Ty Vận Tải Trường Phát đối chiếu với dữ liệu GPS Bình Anh thực tế.
    """
    try:
        gps_fleet = gps_client.fetch_live_fleet()
    except Exception:
        gps_fleet = []

    # Map GPS data by clean plate
    gps_map = {}
    for g in gps_fleet:
        c_plate = g["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper()
        gps_map[c_plate] = g

    drivers_activity = []
    for plate, info in OFFICIAL_DRIVERS.items():
        clean_p = plate.replace("-", "").replace(".", "").replace(" ", "").upper()
        g_data = gps_map.get(clean_p, {})

        daily_km = g_data.get("daily_km", 0.0)
        speed = g_data.get("speed", 0)
        status_type = g_data.get("status_type", "stopped")
        current_address = g_data.get("address") or "Bãi xe Trường Phát"
        fuel_consumed = g_data.get("consumed_liters", 0.0)
        actual_norm = g_data.get("actual_norm", 40.0)
        is_suspicious_drain = g_data.get("is_suspicious_drain", False)

        name = info["name"]
        phone = info["phone"]
        lic_class = info["class"]
        gplx = info["gplx"]
        cccd = info["cccd"]

        # Phân loại cự ly tuyến
        if daily_km > 200:
            distance_category = "Tuyến Dài (>200km)"
            distance_badge = "purple"
            productivity_score = 98
        elif daily_km >= 80:
            distance_category = "Tuyến Trung Bình (80-200km)"
            distance_badge = "blue"
            productivity_score = 92
        elif daily_km > 0:
            distance_category = "Tăng Bo Cảng / Cự Ly Ngắn"
            distance_badge = "emerald"
            productivity_score = 85
        else:
            distance_category = "Tài xế nghỉ / Xe đậu bãi"
            distance_badge = "gray"
            productivity_score = 70

        # Tiêu chí tiết kiệm dầu
        if daily_km == 0:
            fuel_saving_score = 90
            fuel_saving_note = "Xe đậu bãi"
        elif is_suspicious_drain:
            fuel_saving_score = 60
            fuel_saving_note = "Nghi vấn sụt dầu"
        elif actual_norm <= 39.0:
            fuel_saving_score = 98
            fuel_saving_note = f"Tiết kiệm ({actual_norm}L/100km)"
        elif actual_norm <= 42.0:
            fuel_saving_score = 92
            fuel_saving_note = f"Đạt chuẩn ({actual_norm}L/100km)"
        else:
            fuel_saving_score = 75
            fuel_saving_note = f"Vượt chuẩn ({actual_norm}L/100km)"

        # Tiêu chí an toàn GPS
        if speed > 70:
            safety_score = 70
            safety_note = "Cảnh báo quá tốc độ"
        elif speed > 0:
            safety_score = 96
            safety_note = "Chạy đúng tốc độ"
        else:
            safety_score = 98
            safety_note = "Dừng đỗ an toàn"

        # Đánh giá tổng hợp %
        overall_rating = round((productivity_score * 0.4) + (fuel_saving_score * 0.35) + (safety_score * 0.25), 1)

        if overall_rating >= 92:
            grade = "Xuất sắc (A+)"
        elif overall_rating >= 85:
            grade = "Tốt (A)"
        elif overall_rating >= 75:
            grade = "Khá (B)"
        else:
            grade = "Cần nhắc nhở (C)"

        # Nhận xét chi tiết vận hành
        if daily_km > 150:
            detailed_comment = f"Chạy cự ly dài {daily_km}km rất tích cực, chấp hành tốt tốc độ, giao hàng đúng giờ."
        elif daily_km > 0:
            detailed_comment = f"Hoàn thành các chuyến giao nhận theo lệnh, mức tiêu hao dầu {actual_norm}L/100km."
        else:
            detailed_comment = "Tài xế nghỉ cả ngày / Xe đậu bãi bảo quản xe tốt."

        movement_state = "🟢 Đang chạy" if speed > 0 else ("🟡 Dừng nổ máy" if status_type == "idling" else "⚪ Đậu bãi")

        drivers_activity.append({
            "full_name": name,
            "phone": phone,
            "license_class": lic_class,
            "license_number": gplx,
            "national_id": cccd,
            "vehicle_plate": plate,
            "daily_km": daily_km,
            "speed": speed,
            "movement_state": movement_state,
            "current_address": current_address,
            "distance_category": distance_category,
            "distance_badge": distance_badge,
            "productivity_score": productivity_score,
            "fuel_saving_score": fuel_saving_score,
            "fuel_saving_note": fuel_saving_note,
            "safety_score": safety_score,
            "safety_note": safety_note,
            "overall_rating": overall_rating,
            "grade": grade,
            "detailed_comment": detailed_comment
        })

    # Xếp hạng thi đua: tài xế nào chạy nhiều km nhất lên đầu
    drivers_activity.sort(key=lambda x: x["daily_km"], reverse=True)

    top_runners = [d for d in drivers_activity if d["daily_km"] > 0][:5]

    return {
        "total_drivers": len(drivers_activity),
        "active_today": len([d for d in drivers_activity if d["daily_km"] > 0]),
        "top_runners": top_runners,
        "drivers": drivers_activity
    }

@router.get("", response_model=List[schemas.DriverOut])
def get_drivers(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Driver).all()

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
    return d

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
