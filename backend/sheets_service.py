import urllib.request
import csv
import io
import re
from datetime import datetime, date

SHEET1_BASE_URL = "https://docs.google.com/spreadsheets/d/1p0B1bx_yUM6BfW2D88P-Jgra3sBSfqHEM_Op35WxSpI/export?format=csv&gid="
SHEET2_VEHICLES_URL = "https://docs.google.com/spreadsheets/d/1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es/export?format=csv"
SHEET2_MAINTENANCE_URL = "https://docs.google.com/spreadsheets/d/1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es/export?format=csv&gid=1041617404"

# Exact GID mapping for all days of August 2026 in Sheet 1
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

class GoogleSheetsSyncService:
    def __init__(self):
        self.cached_trips = []
        self.cached_vehicles = {"ben": [], "thung": []}
        self.cached_maintenance = []
        self.last_sync_time = None

    def fetch_daily_trips(self, target_date=None):
        today_str = date.today().strftime("%Y-%m-%d")
        t_date = target_date or today_str
        
        # Determine day of month (e.g. "28" or "29")
        try:
            d_obj = datetime.strptime(t_date, "%Y-%m-%d")
            day_str = f"{d_obj.day:02d}"
            display_date = d_obj.strftime("%d/%m/%Y")
        except Exception:
            day_str = "29"
            display_date = "29/08/2026"

        gid = AUGUST_DAY_GIDS.get(day_str, "51584766")
        sheet_url = f"{SHEET1_BASE_URL}{gid}"

        req = urllib.request.Request(sheet_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        ben_trips = []
        thung_trips = []
        current_section = None

        for row in rows:
            if not row or len(row) < 3:
                continue
            first_col = row[0].strip()
            second_col = row[1].strip() if len(row) > 1 else ""
            row_joined = " ".join(row).upper()

            if "XE BEN" in first_col or "XE BEN" in row_joined:
                current_section = "ben"
                continue
            elif "XE CÔNG DÀI" in first_col or "XE THÙNG" in first_col or "XE CÔNG DÀI" in row_joined:
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
                col3 = row[3].strip() if len(row) > 3 else ""
                col4 = row[4].strip() if len(row) > 4 else ""

                is_off = ("NGHỈ" in route_str.upper()) or ("NGHỈ" in col3.upper()) or ("NGHỈ" in col4.upper()) or (route_str == "" and col3 == "" and "NGHỈ" in row_joined)

                if is_off:
                    # User requirement: "phần ghi tài xế nghỉ là nghỉ luôn ngày đó k phải nghỉ ca"
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
                    cargo_type = col3
                    customer_name = col4
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
                elif current_section == "thung":
                    thung_trips.append(trip_item)

        self.cached_trips = ben_trips + thung_trips
        self.last_sync_time = datetime.now()
        active_count = len([t for t in self.cached_trips if t["status_code"] == "active"])
        off_count = len([t for t in self.cached_trips if t["status_code"] == "driver_off"])
        active_percent = round((active_count / len(self.cached_trips) * 100), 1) if self.cached_trips else 0.0

        return {
            "all_trips": self.cached_trips,
            "ben_trips": ben_trips,
            "thung_trips": thung_trips,
            "total": len(self.cached_trips),
            "active_count": active_count,
            "off_count": off_count,
            "active_percent": active_percent,
            "selected_date": t_date,
            "selected_date_display": display_date,
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
                last_km = r[4].strip() if len(r) > 4 else ""
                last_date = r[5].strip() if len(r) > 5 else ""
                current_km = r[6].strip() if len(r) > 6 else ""
                due_km = r[8].strip() if len(r) > 8 else ""
                remaining_km = r[9].strip() if len(r) > 9 else ""
                status = r[10].strip() if len(r) > 10 else "Thiếu số liệu"
                notes = r[11].strip() if len(r) > 11 else ""

                clean_p = raw_plate.replace(".", "").replace("-", "").replace(" ", "").upper()
                if len(clean_p) == 8:
                    fmt_p = f"{clean_p[:3]}-{clean_p[3:6]}.{clean_p[6:]}"
                else:
                    fmt_p = raw_plate

                maintenance_list.append({
                    "stt": stt,
                    "plate_number": fmt_p,
                    "norm_km": norm or "15.000",
                    "last_km": last_km or "—",
                    "last_date": last_date or "—",
                    "current_km": current_km or "—",
                    "due_km": due_km or "—",
                    "remaining_km": remaining_km or "—",
                    "status": status or "Thiếu số liệu",
                    "notes": notes or ""
                })

        self.cached_maintenance = maintenance_list
        return maintenance_list

    def fetch_vehicles_grouped(self):
        req = urllib.request.Request(SHEET2_VEHICLES_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        ben_list = []
        thung_list = []
        current_type = "ben"

        for row in rows:
            if not row or len(row) < 3:
                continue
            row_str = " ".join(row).upper()
            if "XE THÙNG" in row_str or "CÔNG DÀI" in row_str:
                current_type = "thung"
                continue

            matches = re.findall(r'(63[A-Z]-\d{3}\.\d{2}|66[A-Z]-\d{3}\.\d{2}|63[A-Z]\d{5}|66[A-Z]\d{5})', row_str)
            if matches:
                plate = matches[0]
                if "-" not in plate and len(plate) >= 8:
                    plate = f"{plate[:3]}-{plate[3:6]}.{plate[6:]}"

                trailer_matches = re.findall(r'(63R-\d{3}\.\d{2}|63R\d{5})', row_str)
                trailer = trailer_matches[0] if trailer_matches else None
                if trailer and "-" not in trailer:
                    trailer = f"{trailer[:3]}-{trailer[3:6]}.{trailer[6:]}"

                item = {
                    "plate_number": plate,
                    "trailer_number": trailer,
                    "vehicle_type": "Xe Ben" if current_type == "ben" else "Xe Thùng"
                }

                if current_type == "ben" and len(ben_list) < 15:
                    ben_list.append(item)
                elif current_type == "thung" and len(thung_list) < 11:
                    thung_list.append(item)

        self.cached_vehicles = {"ben": ben_list, "thung": thung_list}
        return self.cached_vehicles

sheets_client = GoogleSheetsSyncService()
