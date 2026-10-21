"""Danh sách xe – romoóc – tài xế phụ trách: NGUỒN DUY NHẤT trong code.

Mọi module (GPS, Sheets, dashboard, tài xế, trợ lý) lấy từ đây, không tự khai báo lại.
Theo file "DANH SÁCH XE (12.8.2026).xlsx". Không ghi CCCD / số GPLX vào code.
GĐ2 sẽ chuyển sang đọc danh mục từ Google Sheets.
"""
import re

# (biển số đầu kéo, loại "ben"|"thung", romoóc, tài xế, SĐT tài xế)
FLEET = [
    ("63E-011.56", "ben", "63R-011.90", "Nguyễn Văn Tuấn", "0974 406 941"),
    ("63E-011.17", "ben", "63R-012.16", "Phan Hoàng Duy", "0901 077 345"),
    ("63H-042.73", "ben", "63R-011.85", "Lâm Hoàng Tuấn", "0778 117 516"),
    ("63G-002.86", "ben", "63R-012.25", "Nguyễn Xuân Về", "0395 557 714"),
    ("63F-005.12", "thung", "63R-012.03", "Hoàng Quốc Bảo", "0792 961 140"),
    ("63F-005.38", "thung", "63R-011.94", "Lý Minh Tới", "0971 307 737"),
    ("63E-011.08", "ben", "63R-012.11", "Lý Minh Hoàng", "0904 079 178"),
    ("63F-005.28", "ben", "63R-011.95", "Nguyễn Văn Hiếu", "0878 109 102"),
    ("63E-012.12", "thung", "63R-012.15", "Mạch Đình Phước", "0938 256 639"),
    ("63E-011.41", "thung", "63R-011.93", "Dương Thanh Sang", "0933 549 648"),
    ("63G-002.62", "ben", "63R-011.92", "Nguyễn Thanh Tây", "0703 238 667"),
    ("63H-042.39", "ben", "63R-011.96", "Kim Sô Phép", "0708 400 332"),
    ("63E-011.32", "thung", "63R-011.98", "Đào Ngọc Kha", "0945 220 539"),
    ("63E-012.01", "thung", "63R-012.12", "Lê Trọng Nghĩa", "0949 528 128"),
    ("63F-005.16", "thung", "63R-011.86", "Phùng Phú Kim Toàn", "0986 853 754"),
    ("63E-012.76", "ben", "63R-012.10", "Nguyễn Thanh Giàu", "0345 636 358"),
    ("63E-011.03", "ben", "63R-012.23", "Lê Phương Linh", "0374 929 126"),
    ("63E-011.18", "ben", "63R-012.01", "Lê Ngọc Quí", "0903 722 301"),
    ("63F-005.11", "ben", "63RM-007.44", "Bạch Tấn Trí", "0919 277 113"),
    ("63H-042.34", "ben", "63RM-007.43", "Nguyễn Thành Hiếu", "0937 912 665"),
    ("63G-002.97", "thung", "66RM-010.30", "Trần Trọng Ngân", "0984 731 739"),
    ("63E-012.35", "ben", "66RM-010.32", "Lý Hoàng Thái", "0365 908 374"),
    ("63H-042.36", "ben", "66RM-010.34", "Lê Văn Trọng", "0978 840 929"),
    ("63G-002.80", "thung", "66RM-010.37", "Lê Trung Trực", "0358 426 114"),
    ("66H-083.48", "thung", "66RM-010.38", "Trần Trọng Nghĩa", "0327 066 337"),
    ("63F-005.44", "thung", "63R-012.30", "", ""),
]


def clean_plate(plate: str) -> str:
    """'63E-011.56' / '63E 01156' -> '63E01156'."""
    return re.sub(r"[\s\-\.]", "", plate or "").upper()


FLEET_BY_CLEAN = {clean_plate(p): {"plate_number": p, "vehicle_type": "Xe Ben" if t == "ben" else "Xe Thùng",
                                   "trailer_number": m, "driver_name": n, "phone": ph}
                  for p, t, m, n, ph in FLEET}
XE_BEN_PLATES = {clean_plate(p) for p, t, *_ in FLEET if t == "ben"}
DRIVER_BY_CLEAN_PLATE = {k: v["driver_name"] for k, v in FLEET_BY_CLEAN.items() if v["driver_name"]}


def driver_for(plate: str, default: str = "Chưa phân công") -> str:
    return DRIVER_BY_CLEAN_PLATE.get(clean_plate(plate), default)
