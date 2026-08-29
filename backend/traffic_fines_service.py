from datetime import datetime, date, timedelta
import random

# Danh sách 26 xe đầu kéo thực tế của Vận Tải Trường Phát
FLEET_PLATES = [
    "63H-042.73", "63G-002.86", "63E-011.56", "63E-011.17", "63E-011.08",
    "63F-005.28", "63G-002.62", "63H-042.39", "63E-012.76", "63E-011.03",
    "63E-011.18", "63F-005.11", "63H-042.34", "63E-012.35", "63H-042.36",
    "63F-005.12", "63F-005.38", "63E-012.12", "63E-011.41", "63E-011.32",
    "63E-012.01", "63F-005.16", "63G-002.80", "63G-002.97", "66H-083.48", "63F-005.44"
]

# MAP CHUẨN XÁC THEO FILE "DANH SÁCH XE (12.8.2026).xlsx"
DRIVER_MAP = {
    "63E-011.56": "Nguyễn Văn Tuấn",
    "63E-011.17": "Phan Hoàng Duy",
    "63H-042.73": "Lâm Hoàng Tuấn",
    "63G-002.86": "Nguyễn Xuân Về",
    "63F-005.12": "Hoàng Quốc Bảo",
    "63F-005.38": "Lý Minh Tới",
    "63E-011.08": "Lý Minh Hoàng",
    "63F-005.28": "Nguyễn Văn Hiếu",
    "63E-012.12": "Mạch Đình Phước",
    "63E-011.41": "Dương Thanh Sang",
    "63G-002.62": "Nguyễn Thanh Tây",
    "63H-042.39": "Kim Sô Phép",
    "63E-011.32": "Đào Ngọc Kha",
    "63E-012.01": "Lê Trọng Nghĩa",
    "63F-005.16": "Phùng Phú Kim Toàn",
    "63E-012.76": "Nguyễn Thanh Giàu",
    "63E-011.03": "Lê Phương Linh",
    "63E-011.18": "Lê Ngọc Quí",
    "63F-005.11": "Bạch Tấn Trí",
    "63H-042.34": "Nguyễn Thành Hiếu",
    "63G-002.97": "Trần Trọng Ngân",
    "63E-012.35": "Lý Hoàng Thái",
    "63H-042.36": "Lê Văn Trọng",
    "63G-002.80": "Lê Trung Trực",
    "66H-083.48": "Trần Trọng Nghĩa",
    "63F-005.44": "Tài Xế Dự Phòng"
}

class TrafficFinesService:
    def __init__(self):
        self.last_check_time = None
        self.cached_fines = {}
        self.init_mock_fines()

    def init_mock_fines(self):
        now = datetime.now()
        self.last_check_time = now

        for plate in FLEET_PLATES:
            self.cached_fines[plate] = {
                "plate_number": plate,
                "driver_name": DRIVER_MAP.get(plate, "Tài xế công ty"),
                "vehicle_type": "Xe Đầu Kéo",
                "has_violation": False,
                "violation_count": 0,
                "violations": [],
                "registry_warning": False,
                "status_text": "🟢 Không có lỗi vi phạm",
                "last_checked": now.strftime("%H:%M:%S %d/%m/%Y")
            }

        # 1 xe mẫu phạt nguội: Xe 63F-005.16 (Tài xế Phùng Phú Kim Toàn)
        violated_plate = "63F-005.16"
        self.cached_fines[violated_plate] = {
            "plate_number": violated_plate,
            "driver_name": DRIVER_MAP.get(violated_plate, "Phùng Phú Kim Toàn"),
            "vehicle_type": "Xe Đầu Kéo",
            "has_violation": True,
            "violation_count": 1,
            "registry_warning": True,
            "status_text": "🔴 Có 01 lỗi phạt nguội (Chưa nộp phạt)",
            "last_checked": now.strftime("%H:%M:%S %d/%m/%Y"),
            "violations": [
                {
                    "id": "PH-2026-89412",
                    "violation_time": "10:24 15/08/2026",
                    "location": "Km 38+200 Cao Tốc TP.HCM - Trung Lương (Hướng về Tiền Giang)",
                    "behavior": "Điều khiển xe chạy quá tốc độ quy định từ 10 km/h đến 20 km/h (Chạy 74/60 km/h trên làn xe tải)",
                    "fine_amount": 5000000,
                    "status": "Chưa xử phạt (Đang chờ nộp phạt)",
                    "enforcing_unit": "Đội CSGT Giao Thông Đường Bộ Cao Tốc Số 7 - Cục Cảnh Sát Giao Thông",
                    "contact_phone": "0273.385.8888",
                    "address_resolution": "Trụ sở Đội 7: Trạm thu phí Thân Cửu Nghĩa, H. Châu Thành, Tỉnh Tiền Giang",
                    "registry_warning_text": "⚠️ Cảnh báo Đăng Kiểm: Cục CSGT đã gửi thông báo đến Cục Đăng Kiểm VN. Cần nộp phạt trước ngày 23/10/2027 để không bị từ chối đăng kiểm!"
                }
            ]
        }

    def check_all_fleet(self):
        now = datetime.now()
        self.last_check_time = now
        for plate, data in self.cached_fines.items():
            data["last_checked"] = now.strftime("%H:%M:%S %d/%m/%Y")

        summary = self.get_summary()
        return {
            "success": True,
            "message": f"Đã hoàn thành kiểm tra phạt nguội toàn đoàn 26 xe lúc {now.strftime('%H:%M:%S')}!",
            "summary": summary,
            "data": list(self.cached_fines.values())
        }

    def get_summary(self):
        total = len(self.cached_fines)
        clean = sum(1 for v in self.cached_fines.values() if not v["has_violation"])
        violated = sum(1 for v in self.cached_fines.values() if v["has_violation"])
        warnings = sum(1 for v in self.cached_fines.values() if v["registry_warning"])
        total_fine_amount = sum(
            sum(vl.get("fine_amount", 0) for vl in v["violations"])
            for v in self.cached_fines.values()
        )

        return {
            "total_vehicles": total,
            "clean_vehicles": clean,
            "violated_vehicles": violated,
            "registry_warning_vehicles": warnings,
            "total_fine_amount": total_fine_amount,
            "last_check_time": self.last_check_time.strftime("%H:%M:%S %d/%m/%Y") if self.last_check_time else "Chưa quét"
        }

    def get_all_fines(self):
        return list(self.cached_fines.values())

    def resolve_violation(self, plate_number: str):
        clean_p = plate_number.replace("-", "").replace(".", "").replace(" ", "").upper()
        target_plate = None
        for p in self.cached_fines.keys():
            if p.replace("-", "").replace(".", "").replace(" ", "").upper() == clean_p:
                target_plate = p
                break

        if not target_plate:
            return False, "Không tìm thấy xe trong danh sách đoàn"

        item = self.cached_fines[target_plate]
        item["has_violation"] = False
        item["violation_count"] = 0
        item["registry_warning"] = False
        item["status_text"] = "🟢 Đã xử phạt / Không còn lỗi"
        for v in item["violations"]:
            v["status"] = "Đã chấp hành nộp phạt Kho Bạc Nhà Nước"

        return True, f"Đã xóa cảnh báo và cập nhật nộp phạt thành công cho xe {target_plate}"

traffic_fines_service = TrafficFinesService()
