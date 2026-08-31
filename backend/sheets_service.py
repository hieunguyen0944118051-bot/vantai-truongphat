import urllib.request
import urllib.parse
import csv
import io
import re
import openpyxl
from datetime import datetime, date
from database import SessionLocal
import models

# Trang tính mặc định
DEFAULT_SHEET_AUGUST_ID = "1p0B1bx_yUM6BfW2D88P-Jgra3sBSfqHEM_Op35WxSpI"
DEFAULT_SHEET_SEPTEMBER_ID = "" # Người dùng có thể dán link mới bất cứ lúc nào

SHEET_BASE_CSV = "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid="
SHEET_BASE_XLSX = "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

# GID các ngày Tháng 08/2026
AUGUST_DAY_GIDS = {
    "01": "769155513", "02": "471343189", "03": "2083643691", "04": "1808732284",
    "05": "27125077", "06": "366542307", "07": "462758268", "08": "1292525407",
    "09": "2051999310", "10": "843701052", "11": "664876869", "12": "461431695",
    "13": "512544451", "14": "1744984511", "15": "1349609157", "16": "1938651349",
    "17": "1596651326", "18": "1442146768", "19": "22985075", "20": "1918502258",
    "21": "1091331882", "22": "602170138", "23": "1195131580", "24": "390199280",
    "25": "2138537258", "26": "2042832939", "27": "163556344", "28": "2100186358",
    "29": "51584766", "30": "1210470376", "31": "1716980095"
}

SHEET2_VEHICLES_URL = "https://docs.google.com/spreadsheets/d/1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es/export?format=csv"
SHEET2_MAINTENANCE_URL = "https://docs.google.com/spreadsheets/d/1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es/export?format=csv&gid=1041617404"

class GoogleSheetsSyncService:
    def __init__(self):
        self.cached_trips = []
        self.cached_vehicles = {"ben": [], "thung": []}
        self.cached_maintenance = []
        self.last_sync_time = None
        self._xlsx_cache = {} # sheet_id -> (timestamp, bytes)

    def extract_sheet_id(self, url_or_id: str) -> str:
        """Trích xuất ID Google Sheet từ URL hoặc chuỗi ID"""
        if not url_or_id:
            return ""
        url_or_id = url_or_id.strip()
        m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_or_id)
        if m:
            return m.group(1)
        return url_or_id

    def get_sheet_id_for_month(self, month_str: str) -> str:
        """Lấy Google Sheet ID cho tháng cụ thể (08, 09...) từ DB hoặc mặc định"""
        db = SessionLocal()
        try:
            setting = db.query(models.SystemSetting).filter(
                models.SystemSetting.key == f"sheet_url_month_{month_str}"
            ).first()
            if setting and setting.value:
                return self.extract_sheet_id(setting.value)
        except Exception:
            pass
        finally:
            db.close()

        if month_str == "08":
            return DEFAULT_SHEET_AUGUST_ID
        elif month_str == "09":
            return DEFAULT_SHEET_SEPTEMBER_ID or DEFAULT_SHEET_AUGUST_ID
        return DEFAULT_SHEET_AUGUST_ID

    def set_sheet_url_for_month(self, month_str: str, sheet_url: str):
        """Lưu link Google Sheet cho tháng vào cơ sở dữ liệu"""
        sheet_id = self.extract_sheet_id(sheet_url)
        db = SessionLocal()
        try:
            setting = db.query(models.SystemSetting).filter(
                models.SystemSetting.key == f"sheet_url_month_{month_str}"
            ).first()
            if not setting:
                setting = models.SystemSetting(
                    key=f"sheet_url_month_{month_str}",
                    value=sheet_url
                )
                db.add(setting)
            else:
                setting.value = sheet_url
                setting.updated_at = datetime.utcnow()
            db.commit()
            return sheet_id
        finally:
            db.close()

    def fetch_daily_trips(self, target_date=None):
        today_obj = date.today()
        today_str = today_obj.strftime("%Y-%m-%d")
        t_date = target_date or today_str

        try:
            d_obj = datetime.strptime(t_date, "%Y-%m-%d").date()
        except Exception:
            d_obj = today_obj
            t_date = today_str

        day_str = f"{d_obj.day:02d}"
        month_str = f"{d_obj.month:02d}"
        display_date = d_obj.strftime("%d/%m/%Y")

        sheet_id = self.get_sheet_id_for_month(month_str)
        if not sheet_id:
            sheet_id = DEFAULT_SHEET_AUGUST_ID

        rows = []

        # Cách 1: Nếu là Tháng 08 và có GID sẵn trong AUGUST_DAY_GIDS -> Đọc CSV cực nhanh
        if month_str == "08" and day_str in AUGUST_DAY_GIDS and sheet_id == DEFAULT_SHEET_AUGUST_ID:
            gid = AUGUST_DAY_GIDS[day_str]
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    content = resp.read().decode("utf-8", errors="ignore")
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
            except Exception as e:
                print(f"Error fetching CSV via GID: {e}")
                rows = []

        # Cách 2: Nếu chưa có rows (ví dụ Tháng 09 hoặc ngày mới) -> Đọc động toàn bộ sheet qua XLSX
        if not rows:
            try:
                xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                req = urllib.request.Request(xlsx_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()

                wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
                matching_sheet = None

                # Tìm tab bắt đầu bằng số ngày, ví dụ "01 - T3", "01", "31 - T2"
                for s_name in wb.sheetnames:
                    clean_s = s_name.strip()
                    if clean_s.startswith(day_str) or clean_s.startswith(f"{d_obj.day} "):
                        matching_sheet = s_name
                        break

                if not matching_sheet:
                    # Fallback tìm tab có chứa ngày
                    for s_name in wb.sheetnames:
                        if day_str in s_name:
                            matching_sheet = s_name
                            break

                if matching_sheet and matching_sheet in wb.sheetnames:
                    ws = wb[matching_sheet]
                    for r in ws.iter_rows(values_only=True):
                        row_vals = [str(c).strip() if c is not None else "" for c in r]
                        if any(row_vals):
                            rows.append(row_vals)
            except Exception as e:
                print(f"Error fetching dynamic XLSX: {e}")

        # Phân tích các dòng bảng kê
        ben_trips = []
        thung_trips = []
        current_section = "ben"

        for row in rows:
            if not row or len(row) < 2:
                continue
            first_col = row[0].strip() if len(row) > 0 else ""
            second_col = row[1].strip() if len(row) > 1 else ""
            row_joined = " ".join(row).upper()

            if "XE BEN" in first_col.upper() or "XE BEN" in row_joined:
                current_section = "ben"
                continue
            elif "XE CÔNG DÀI" in first_col.upper() or "XE THÙNG" in first_col.upper() or "XE CÔNG DÀI" in row_joined:
                current_section = "thung"
                continue

            if first_col == "STT" or second_col in ["Biển số", "TỔNG", ""]:
                continue

            if first_col.isdigit() and len(second_col) >= 6:
                raw_plate = second_col.replace(".", "").replace("-", "").replace(" ", "").upper()
                if len(raw_plate) == 8 and (raw_plate.startswith("63") or raw_plate.startswith("66")):
                    formatted_plate = f"{raw_plate[:3]}-{raw_plate[3:6]}.{raw_plate[6:]}"
                else:
                    formatted_plate = raw_plate

                route_str = row[2].strip() if len(row) > 2 else ""
                col3 = row[3].strip() if len(row) > 3 else "" # Loại hàng
                col4 = row[4].strip() if len(row) > 4 else "" # Chủ hàng 1

                is_off = (
                    ("NGHỈ" in route_str.upper()) or 
                    ("NGHỈ" in col3.upper()) or 
                    ("NGHỈ" in col4.upper()) or 
                    ("TÀI XẾ NGHỈ" in row_joined) or
                    (route_str == "" and col3 == "" and "NGHỈ" in row_joined)
                )

                if is_off:
                    status_text = "Tài xế nghỉ (Nghỉ cả ngày)"
                    status_code = "driver_off"
                    route_display = "Tài xế nghỉ cả ngày / Xe đậu bãi"
                    cargo_type = "—"
                    customer_name = "—"
                    origin = ""
                    destination = ""
                else:
                    status_text = "Hoạt động"
                    status_code = "active"
                    route_display = route_str
                    cargo_type = col3 or "Hàng xá"
                    # Chuẩn hóa tên chủ hàng
                    raw_cust = col4.strip()
                    if raw_cust and "NGHỈ" not in raw_cust.upper():
                        customer_name = raw_cust
                    else:
                        customer_name = "Khai Anh" # Default if not specified

                    parts = route_str.split("=>")
                    if len(parts) == 2:
                        origin = parts[0].strip()
                        destination = parts[1].strip()
                    else:
                        origin = "Cảng Phú Mỹ"
                        destination = route_str

                trip_item = {
                    "stt": int(first_col),
                    "plate_number": formatted_plate,
                    "raw_plate": raw_plate,
                    "vehicle_type": "Xe Ben" if current_section == "ben" else "Xe Thùng",
                    "route": route_display,
                    "origin": origin,
                    "destination": destination,
                    "cargo_type": cargo_type,
                    "customer_name": customer_name,
                    "status_text": status_text,
                    "status_code": status_code,
                    "trip_date": t_date,
                    "trip_date_display": display_date
                }

                if current_section == "ben":
                    ben_trips.append(trip_item)
                else:
                    thung_trips.append(trip_item)

        self.cached_trips = ben_trips + thung_trips
        self.last_sync_time = datetime.now()
        active_count = len([t for t in self.cached_trips if t["status_code"] == "active"])
        off_count = len([t for t in self.cached_trips if t["status_code"] == "driver_off"])
        active_percent = round((active_count / len(self.cached_trips) * 100), 1) if self.cached_trips else 0.0

        # Thống kê cơ cấu chủ hàng
        customer_counts = {}
        for t in self.cached_trips:
            if t["status_code"] == "active":
                c = t["customer_name"]
                if c and c != "—":
                    customer_counts[c] = customer_counts.get(c, 0) + 1

        total_active_trips = sum(customer_counts.values())
        customer_breakdown = [
            {
                "customer": cust,
                "trips": cnt,
                "percent": round((cnt / total_active_trips * 100), 1) if total_active_trips > 0 else 0.0
            }
            for cust, cnt in sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "all_trips": self.cached_trips,
            "ben_trips": ben_trips,
            "thung_trips": thung_trips,
            "total": len(self.cached_trips),
            "active_count": active_count,
            "off_count": off_count,
            "active_percent": active_percent,
            "customer_breakdown": customer_breakdown,
            "selected_date": t_date,
            "selected_date_display": display_date,
            "month": month_str,
            "sheet_id": sheet_id,
            "sync_time": self.last_sync_time.strftime("%H:%M:%S %d/%m/%Y")
        }

    def fetch_maintenance_sheet(self):
        req = urllib.request.Request(SHEET2_MAINTENANCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        maintenance_list = []
        for r in rows:
            if len(r) > 2 and r[1].strip().isdigit():
                stt = int(r[1].strip())
                if stt > 26:
                    continue
                raw_plate = r[2].strip()
                norm = r[3].strip() if len(r) > 3 else "15.000"
                last_odo = r[4].strip() if len(r) > 4 else "0"
                last_date = r[5].strip() if len(r) > 5 else ""
                next_odo = r[6].strip() if len(r) > 6 else "0"
                actual_odo = r[7].strip() if len(r) > 7 else "0"
                diff_km = r[8].strip() if len(r) > 8 else "0"
                status_text = r[9].strip() if len(r) > 9 else "Bình thường"
                notes = r[10].strip() if len(r) > 10 else ""

                maintenance_list.append({
                    "stt": stt,
                    "plate_number": raw_plate,
                    "norm": norm,
                    "last_odo": last_odo,
                    "last_date": last_date,
                    "next_odo": next_odo,
                    "actual_odo": actual_odo,
                    "diff_km": diff_km,
                    "status_text": status_text,
                    "notes": notes
                })

        self.cached_maintenance = maintenance_list
        return maintenance_list

    def fetch_vehicles_sheet(self):
        req = urllib.request.Request(SHEET2_VEHICLES_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        ben_vehicles = []
        thung_vehicles = []
        current_type = "ben"

        for r in rows:
            if not r or len(r) < 2:
                continue
            r_str = " ".join(r).upper()
            if "XE BEN" in r_str:
                current_type = "ben"
                continue
            elif "XE THÙNG" in r_str or "XE CÔNG DÀI" in r_str:
                current_type = "thung"
                continue

            if len(r) > 1 and r[1].strip().isdigit():
                stt = int(r[1].strip())
                if stt > 26:
                    continue
                v_item = {
                    "stt": stt,
                    "plate_number": r[2].strip() if len(r) > 2 else "",
                    "trailer_number": r[3].strip() if len(r) > 3 else "",
                    "driver_name": r[4].strip() if len(r) > 4 else "",
                    "driver_phone": r[5].strip() if len(r) > 5 else "",
                    "gdd_head": r[6].strip() if len(r) > 6 else "",
                    "gdd_trailer": r[7].strip() if len(r) > 7 else "",
                    "registration_expiry": r[8].strip() if len(r) > 8 else "",
                    "insurance_expiry": r[9].strip() if len(r) > 9 else "",
                    "vehicle_type": "Xe Ben" if current_type == "ben" else "Xe Thùng"
                }
                if current_type == "ben":
                    ben_vehicles.append(v_item)
                else:
                    thung_vehicles.append(v_item)

        self.cached_vehicles = {"ben": ben_vehicles, "thung": thung_vehicles}
        return self.cached_vehicles

sheets_client = GoogleSheetsSyncService()
