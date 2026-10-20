import urllib.request
import urllib.parse
import csv
import io
import re
import time
import os
import unicodedata
import openpyxl
from datetime import datetime, date, timedelta
from database import SessionLocal
import models
from gps_service import OFFICIAL_DRIVERS_BY_CLEAN_PLATE

DEFAULT_SHEET_AUGUST_ID = "1p0B1bx_yUM6BfW2D88P-Jgra3sBSfqHEM_Op35WxSpI"
DEFAULT_SHEET_SEPTEMBER_ID = "1NSNhOIO--PEx9W3u5O2I-w1bvl4kN3TTh9qXfiXb2U0"

# ===== FILE XE NHẬN HÀNG THEO THÁNG =====
# Thứ tự ưu tiên khi tìm file của 1 tháng (xem get_sheet_id_for):
#   1. Link dán tay trong app (bảng system_settings, key sheet_url_YYYY_MM)
#   2. Danh sách cố định KNOWN_MONTH_SHEETS dưới đây (không mất khi Render deploy lại)
#   3. Tự dò trong thư mục Drive chia sẻ link (SHEETS_FOLDER_IDS) theo tên file chuẩn:
#        XE_NHẬN_HÀNG_THÁNG_MM-YYYY   (chấp nhận cả "XE NHẬN HÀNG THÁNG MM/YYYY")
#   4. Không tìm thấy -> báo "chưa có file", TUYỆT ĐỐI không lấy file tháng khác.
KNOWN_MONTH_SHEETS = {
    "2026-05": "1I3JrSieGWbefreeTi1WbC4_uVm7-b5X7Oo4cq0hiFMQ",
    "2026-06": "174-XpY0SPk78jLoTQfExRQiy37fXN6y_tx8nQa6wM4I",
    "2026-07": "1hQ_qLeD9uPczFTukDVGbsGEJZat4rNrRFTfcFZu0O5s",
    "2026-08": DEFAULT_SHEET_AUGUST_ID,
    "2026-09": "1e5ywy9BthpB3o5l6b7HC8A7J-1UsOQesdiMdio0dFqs",
    "2026-10": "1dWyWM3BMSDQwKMIwgcCu4zSQJujMIx3anpuAa2Q_Nao",
}

# Thư mục Drive chứa file tháng (phải bật "Bất kỳ ai có đường liên kết - Người xem").
# Có thể ghi đè bằng biến môi trường SHEETS_FOLDER_IDS="id1,id2" trên Render.
DEFAULT_SHEETS_FOLDER_IDS = ["1TqSGS7fktz2aYWMPeHhkt2YWH0cmSwrT"]  # Drive: 00 - DÙNG HẰNG NGÀY / XE NHẬN HÀNG THEO THÁNG (APP ĐỌC)
DISCOVERY_CACHE_SECONDS = 1800   # tháng chưa có file: 30 phút dò lại 1 lần


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").upper()


_MONTH_FILE_RE = re.compile(r"XE[\W_]*NHAN[\W_]*HANG[\W_]*THANG[\W_]*(\d{1,2})[\W_]*(\d{4})")


def parse_month_file_name(name: str):
    """'XE_NHẬN_HÀNG_THÁNG_11-2026' -> '2026-11'. Không khớp -> None."""
    m = _MONTH_FILE_RE.search(_strip_accents(name))
    if not m:
        return None
    month, year = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}"


def month_key(d) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def parse_embedded_folder_html(html: str):
    """Tách (file_id, tên file) từ trang drive.google.com/embeddedfolderview."""
    import html as _html
    out = []
    for m in re.finditer(r'id="entry-([a-zA-Z0-9_-]{20,})"(.*?)flip-entry-title">(.*?)</div>', html, re.S):
        out.append((m.group(1), _html.unescape(m.group(3)).strip()))
    return out


# ===== BỘ ĐỌC TAB NGÀY (theo tiêu đề cột, không cố định vị trí) =====
_PLATE_RE = re.compile(r"^(6[0-9])[A-Z]{1,2}\d{4,6}$")

def _norm_header(v: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(v or "")).strip()

def _clean_plate(v: str) -> str:
    return re.sub(r"[\s\-\.]", "", (v or "")).upper()

def _detect_header(row):
    """Nhận diện dòng tiêu đề. Trả về dict cột hoặc None."""
    hs = [_norm_header(c) for c in row]
    if not any(h in ("BIEN SO", "SO XE", "BIEN SO XE") for h in hs):
        return None
    cols = {"plate": next(i for i, h in enumerate(hs) if h in ("BIEN SO", "SO XE", "BIEN SO XE")), "legs": []}
    for i, h in enumerate(hs):
        if h.startswith("TUYEN"):
            cols["route"] = i
    for k in (1, 2, 3):
        leg = {}
        for i, h in enumerate(hs):
            if h == f"NOI NHAN {k}": leg["origin"] = i
            elif h == f"NOI GIAO {k}": leg["dest"] = i
            elif h == f"LOAI HANG {k}": leg["cargo"] = i
            elif h == f"CHU HANG {k}": leg["customer"] = i
        if leg:
            cols["legs"].append(leg)
    return cols

def _cell(row, idx):
    if idx is None or idx >= len(row):
        return ""
    return (row[idx] or "").strip()

def _split_route(route: str):
    for sep in ("=>", "->", "➔", "→"):
        if sep in route:
            o, d = route.split(sep, 1)
            return o.strip(), d.strip()
    return "", route.strip()

_OFF_WORDS = ("TÀI XẾ NGHỈ", "TX NGHỈ", "NGHỈ")
_REPAIR_WORDS = ("SỬA XE", "BẢO DƯỠNG", "SỬA")

def parse_dispatch_rows(rows, display_date=""):
    """Đọc các dòng của 1 tab ngày -> (ben_trips, thung_trips).
    Mẫu mới: Biển số | Nơi nhận k | Nơi giao k | Loại hàng k | Chủ hàng k (k=1..3).
    Mẫu cũ : Biển số | Tuyến / Ghi chú | Loại hàng k | Chủ hàng k."""
    ben_trips, thung_trips = [], []
    section = "ben"
    cols = None
    seen = set()
    for row in rows:
        if not row:
            continue
        first = _norm_header(row[0])
        # Mốc phân đoạn (chỉ xét ô đầu dòng)
        if "XE BEN" in first:
            section = "ben"; continue
        if "XE CONG DAI" in first or "XE THUNG" in first:
            section = "thung"; continue
        if "TONG XE NM" in first or first.startswith("TANG BO") or "CHAY TANG BO" == first:
            if cols is not None or ben_trips or thung_trips:
                break
        hdr = _detect_header(row)
        if hdr:
            cols = hdr
            continue
        if cols is None:
            continue
        clean_p = _clean_plate(_cell(row, cols["plate"]))
        if not _PLATE_RE.match(clean_p) or clean_p in seen:
            continue
        seen.add(clean_p)

        legs = []
        for leg in cols["legs"]:
            o = _cell(row, leg.get("origin")); d = _cell(row, leg.get("dest"))
            cg = _cell(row, leg.get("cargo")); cu = _cell(row, leg.get("customer"))
            legs.append({"origin": o, "dest": d, "cargo": cg, "customer": cu})
        route_raw = _cell(row, cols.get("route"))
        if route_raw and legs:
            o, d = _split_route(route_raw)
            if not legs[0]["origin"] and not legs[0]["dest"]:
                legs[0]["origin"], legs[0]["dest"] = o, d

        first_leg = legs[0] if legs else {"origin": "", "dest": "", "cargo": "", "customer": ""}
        notes = " ".join([route_raw] + [" ".join(l.values()) for l in legs]).upper()

        def is_real(l):
            txt = " ".join(l.values()).upper()
            if not (l["dest"] or l["customer"] or l["origin"]):
                return False
            return not any(w in txt for w in _OFF_WORDS + _REPAIR_WORDS + ("TRỐNG LỊCH",))
        real_legs = [l for l in legs if is_real(l)]

        if any(w in notes for w in _OFF_WORDS):
            status_code, status_str = "driver_off", "Tài xế nghỉ cả ngày"
        elif any(w in notes for w in _REPAIR_WORDS):
            status_code, status_str = "off", "Bảo dưỡng / Sửa xe"
        elif "TRỐNG LỊCH" in notes or "ĐỢI GIAO" in notes:
            status_code = "idle"
            status_str = "Đợi giao hàng / Trống lịch" if "ĐỢI GIAO" in notes else "Trống lịch"
        elif not real_legs and not route_raw:
            status_code, status_str = "idle", "Nghỉ bãi / Trống lịch"
        else:
            status_code, status_str = "active", "Đang hoạt động"
        if status_code == "active" and real_legs:
            first_leg = real_legs[0]

        origin, dest = first_leg["origin"], first_leg["dest"]
        if origin and dest:
            route = f"{origin} => {dest}"
        else:
            route = route_raw or dest or origin
        if len(real_legs) > 1:
            route += f" (+{len(real_legs) - 1} chuyến)"

        formatted = f"{clean_p[:3]}-{clean_p[3:6]}.{clean_p[6:]}" if len(clean_p) == 8 else clean_p
        item = {
            "raw_plate": formatted,
            "plate_number": formatted,
            "clean_plate": clean_p,
            "vehicle_type": "Xe Ben" if section == "ben" else "Xe Thùng",
            "route": route or ("Nghỉ bãi" if status_code != "active" else "Đang chạy"),
            "origin": origin,
            "destination": dest,
            "cargo_type": first_leg["cargo"] or "—",
            "customer_name": first_leg["customer"] or "—",
            "status_code": status_code,
            "status_text": status_str,
            "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p, "Tài xế công ty"),
            "num_trips": max(1, len(real_legs)) if status_code == "active" else 0,
            "legs": real_legs,
            "date": display_date,
        }
        (ben_trips if section == "ben" else thung_trips).append(item)
    return ben_trips, thung_trips


def find_day_sheet(sheetnames, day: int):
    """Tìm tab theo ngày: '20', '20 - T3', '20-10', '20 T3'. Không nhầm với 'TỔNG THÁNG 10'."""
    pat = re.compile(rf"^0?{day}(\D|$)")
    for n in sheetnames:
        if pat.match(n.strip()):
            return n
    return None


def estimate_leg_km(dest: str) -> float:
    """Ước tính km khứ hồi 1 chuyến theo nơi giao (giữ quy ước cũ)."""
    d = (dest or "").lower()
    if any(k in d for k in ("đức hòa", "bến lức", "long an")):
        return 180.0
    if any(k in d for k in ("thăng long", "đan phượng", "bình dương")):
        return 150.0
    if any(k in d for k in ("cát lái", "hiệp phước", "hcm")):
        return 130.0
    if any(k in d for k in ("cảng", "ptsc", "mỹ xuân")):
        return 80.0
    if "vũng tàu" in d:
        return 90.0
    return 140.0


class SheetNotFoundError(Exception):
    """Chưa có file Google Sheets cho tháng được chọn."""


AUGUST_DAY_GIDS = {
    "01": "2036778103", "02": "1298495420", "03": "349372223",
    "04": "1940989344", "05": "685790695",  "06": "775628549",
    "07": "426462719",  "08": "1517596825", "09": "1801267674",
    "10": "1002307521", "11": "119854746",  "12": "2029705886",
    "13": "1994784733", "14": "1815525547", "15": "917527663",
    "16": "1830588414", "17": "1564883446", "18": "864147041",
    "19": "1992019904", "20": "774136979",  "21": "1406859599",
    "22": "1408821946", "23": "673756214",  "24": "1369715783",
    "25": "1738747493", "26": "632069695",  "27": "1126602330",
    "28": "893952771",  "29": "1753303657",  "30": "1041617404",
    "31": "1753303657"
}

SHEET2_VEHICLES_URL = "https://docs.google.com/spreadsheets/d/1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es/export?format=csv"
SHEET2_MAINTENANCE_URL = "https://docs.google.com/spreadsheets/d/1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es/export?format=csv&gid=1041617404"

class GoogleSheetsSyncService:
    def __init__(self):
        self.cached_trips = {}          # date_str -> (timestamp, result_dict)
        self.cached_xlsx = {}           # sheet_id -> (timestamp, bytes)
        self.cached_weekly_stats = {}   # cache_key -> (timestamp, dict)
        self.cached_maintenance = None  # (timestamp, list)
        self.cached_vehicles = None     # (timestamp, dict)
        self.last_sync_time = None
        self._discovered = {}          # YYYY-MM -> sheet_id (dò thư mục)
        self._discovered_ts = 0
        self._discovery_errors = []

    def extract_sheet_id(self, url_or_id: str) -> str:
        if not url_or_id:
            return ""
        url_or_id = url_or_id.strip()
        m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_or_id)
        if m:
            return m.group(1)
        return url_or_id

    # ---------- Cấu hình file theo tháng ----------
    def _folder_ids(self):
        env = os.environ.get("SHEETS_FOLDER_IDS", "")
        ids = [x.strip() for x in env.split(",") if x.strip()]
        db_val = self._get_setting("sheets_folder_ids")
        if db_val:
            ids += [x.strip() for x in db_val.split(",") if x.strip()]
        ids += DEFAULT_SHEETS_FOLDER_IDS
        seen, out = set(), []
        for i in ids:
            fid = self.extract_folder_id(i)
            if fid and fid not in seen:
                seen.add(fid)
                out.append(fid)
        return out

    def extract_folder_id(self, url_or_id: str) -> str:
        if not url_or_id:
            return ""
        m = re.search(r"/folders/([a-zA-Z0-9-_]+)", url_or_id)
        if m:
            return m.group(1)
        m = re.search(r"[?&]id=([a-zA-Z0-9-_]+)", url_or_id)
        if m:
            return m.group(1)
        return url_or_id.strip()

    def _get_setting(self, key: str):
        db = SessionLocal()
        try:
            st = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
            return st.value if st and st.value else None
        except Exception as e:
            print(f"[sheets] Lỗi đọc cấu hình {key}: {e}")
            return None
        finally:
            db.close()

    def _set_setting(self, key: str, value: str):
        db = SessionLocal()
        try:
            st = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
            if st:
                st.value = value
            else:
                db.add(models.SystemSetting(key=key, value=value))
            db.commit()
        finally:
            db.close()

    def _delete_setting(self, key: str):
        db = SessionLocal()
        try:
            db.query(models.SystemSetting).filter(models.SystemSetting.key == key).delete()
            db.commit()
        finally:
            db.close()

    def _list_folder_files(self, folder_id: str):
        """Đọc danh sách file của thư mục Drive chia sẻ link công khai (không cần API key).
        Trả về list (file_id, title)."""
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        return parse_embedded_folder_html(html)

    def discover_month_sheets(self, force: bool = False):
        """Dò tất cả file XE_NHẬN_HÀNG_THÁNG_MM-YYYY trong các thư mục cấu hình.
        Kết quả cache trong RAM; trả về dict {YYYY-MM: sheet_id}."""
        now = time.time()
        if not force and self._discovered and now - self._discovered_ts < DISCOVERY_CACHE_SECONDS:
            return self._discovered
        found = {}
        errors = []
        for fid in self._folder_ids():
            try:
                for file_id, title in self._list_folder_files(fid):
                    mk = parse_month_file_name(title)
                    if mk and mk not in found:
                        found[mk] = file_id
            except Exception as e:
                errors.append(f"{fid}: {e}")
        if errors:
            print(f"[sheets] Lỗi dò thư mục: {errors}")
        self._discovered = found
        self._discovered_ts = now
        self._discovery_errors = errors
        return found

    def resolve_month(self, mk: str):
        """Trả về (sheet_id, nguồn) cho tháng 'YYYY-MM'; (None, None) nếu chưa có file."""
        yyyy, mm = mk.split("-")
        manual = self._get_setting(f"sheet_url_{yyyy}_{mm}")
        if manual:
            return self.extract_sheet_id(manual), "manual"
        if yyyy == "2026":
            # tương thích cấu hình cũ (sheet_url_month_09 ...)
            legacy = self._get_setting(f"sheet_url_month_{mm}")
            if legacy:
                return self.extract_sheet_id(legacy), "manual"
        if mk in KNOWN_MONTH_SHEETS:
            return KNOWN_MONTH_SHEETS[mk], "known"
        found = self.discover_month_sheets()
        if mk not in found:
            # Tháng mới vừa tạo file: dò lại ngay nếu cache đã quá 2 phút
            if time.time() - self._discovered_ts > 120:
                found = self.discover_month_sheets(force=True)
        if mk in found:
            return found[mk], "auto"
        return None, None

    def get_sheet_id_for(self, d) -> str:
        sheet_id, _ = self.resolve_month(month_key(d))
        if not sheet_id:
            raise SheetNotFoundError(
                f"Chưa có file XE_NHẬN_HÀNG_THÁNG_{d.month:02d}-{d.year} "
                f"cho ngày {d.strftime('%d/%m/%Y')}"
            )
        return sheet_id

    def get_sheet_id_for_month(self, month_str: str, year: int = None) -> str:
        """Giữ tương thích code cũ. Trả '' nếu chưa có file."""
        y = year or date.today().year
        sheet_id, _ = self.resolve_month(f"{y:04d}-{int(month_str):02d}")
        return sheet_id or ""

    def set_sheet_url_for_month(self, month_str: str, sheet_url: str, year: int = None):
        y = year or date.today().year
        mm = f"{int(month_str):02d}"
        key = f"sheet_url_{y:04d}_{mm}"
        if sheet_url and sheet_url.strip():
            self._set_setting(key, sheet_url.strip())
        else:
            self._delete_setting(key)
            if y == 2026:
                self._delete_setting(f"sheet_url_month_{mm}")
        self.clear_caches()

    def clear_caches(self):
        self.cached_trips.clear()
        self.cached_xlsx.clear()
        self.cached_weekly_stats.clear()
        self._discovered = {}
        self._discovered_ts = 0

    def list_month_config(self, months_back: int = 6, months_ahead: int = 1):
        """Bảng trạng thái file theo tháng cho màn hình cài đặt."""
        today = date.today()
        keys = set(KNOWN_MONTH_SHEETS.keys())
        found = self.discover_month_sheets()
        keys |= set(found.keys())
        y, m = today.year, today.month
        for i in range(-months_back, months_ahead + 1):
            mm = m + i
            yy = y + (mm - 1) // 12
            mm = (mm - 1) % 12 + 1
            keys.add(f"{yy:04d}-{mm:02d}")
        rows = []
        for mk in sorted(keys, reverse=True):
            sid, src = self.resolve_month(mk)
            yyyy, mm = mk.split("-")
            rows.append({
                "month": mk,
                "label": f"Tháng {mm}/{yyyy}",
                "file_name": f"XE_NHẬN_HÀNG_THÁNG_{mm}-{yyyy}",
                "sheet_id": sid,
                "url": f"https://docs.google.com/spreadsheets/d/{sid}/edit" if sid else "",
                "source": src,
                "is_current": mk == month_key(today),
            })
        return {
            "months": rows,
            "folder_ids": self._folder_ids(),
            "discovery_errors": getattr(self, "_discovery_errors", []),
        }

    def _get_xlsx_bytes(self, sheet_id: str) -> bytes:
        now = time.time()
        if sheet_id in self.cached_xlsx:
            ts, data = self.cached_xlsx[sheet_id]
            if now - ts < 600: # 10 phút cache XLSX
                return data

        try:
            xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
            req = urllib.request.Request(xlsx_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            self.cached_xlsx[sheet_id] = (now, data)
            return data
        except Exception as e:
            print(f"Error fetching XLSX for sheet {sheet_id}: {e}")
            raise e

    def fetch_daily_trips(self, target_date=None):
        today_obj = date.today()
        today_str = today_obj.strftime("%Y-%m-%d")
        t_date = target_date or today_str

        # Kiểm tra in-memory cache để chuyển ngày siêu tốc (< 5ms)
        now = time.time()
        if t_date in self.cached_trips:
            ts, cached_res = self.cached_trips[t_date]
            if now - ts < 300: # 5 phút cache
                return cached_res

        try:
            d_obj = datetime.strptime(t_date, "%Y-%m-%d").date()
        except Exception:
            d_obj = today_obj
            t_date = today_str

        day_str = f"{d_obj.day:02d}"
        month_str = f"{d_obj.month:02d}"
        display_date = d_obj.strftime("%d/%m/%Y")

        # Lấy đúng file của THÁNG + NĂM được chọn. Chưa có file -> SheetNotFoundError
        # (không bao giờ lấy nhầm file tháng khác).
        sheet_id = self.get_sheet_id_for(d_obj)

        rows = []

        # Cách 1: Thử tải CSV nhanh qua GID nếu có sẵn
        if month_str == "08" and day_str in AUGUST_DAY_GIDS and sheet_id == DEFAULT_SHEET_AUGUST_ID:
            gid = AUGUST_DAY_GIDS[day_str]
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    content = resp.read().decode("utf-8", errors="ignore")
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
            except Exception:
                rows = []

        # Cách 2: Đọc qua XLSX cached
        if not rows:
            try:
                data = self._get_xlsx_bytes(sheet_id)
                wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
            except Exception as e:
                raise RuntimeError(f"Không tải được file Google Sheets tháng {month_str} "
                                   f"(kiểm tra file đã bật chia sẻ link chưa): {e}")
            matching_sheet = find_day_sheet(wb.sheetnames, d_obj.day)
            if not matching_sheet:
                raise SheetNotFoundError(f"File tháng {month_str} chưa có tab ngày {day_str}")
            for r in wb[matching_sheet].iter_rows(values_only=True):
                row_vals = [str(c).strip() if c is not None else "" for c in r]
                if any(row_vals):
                    rows.append(row_vals)

        # Phân tích dòng bảng kê (hỗ trợ cả mẫu cũ T08 và mẫu mới T09+)
        ben_trips, thung_trips = parse_dispatch_rows(rows, display_date)

        all_trips = []
        for idx, t in enumerate(ben_trips + thung_trips, 1):
            t["stt"] = idx
            all_trips.append(t)

        total_vehicles = len(all_trips)
        active_count = len([t for t in all_trips if t.get("status_code") == "active"])
        off_count = len([t for t in all_trips if t.get("status_code") != "active"])
        active_percent = round((active_count / total_vehicles * 100), 1) if total_vehicles > 0 else 0.0

        # Phân tích cơ cấu chủ hàng (%)
        from collections import Counter
        cust_counter = Counter()
        for t in all_trips:
            if t.get("status_code") == "active":
                c = t.get("customer_name")
                if c and c != "—" and "NGHỈ" not in c.upper() and "SỬA" not in c.upper() and "TRỐNG" not in c.upper():
                    cust_counter[c] += 1

        total_cust_trips = sum(cust_counter.values())
        customer_breakdown = []
        for c_name, c_cnt in cust_counter.most_common(5):
            pct = round(c_cnt / total_cust_trips * 100, 1) if total_cust_trips > 0 else 0.0
            customer_breakdown.append({"customer": c_name, "trips": c_cnt, "percent": pct})

        result = {
            "date": display_date,
            "selected_date": t_date,
            "ben": ben_trips,
            "thung": thung_trips,
            "ben_trips": ben_trips,
            "thung_trips": thung_trips,
            "all_trips": all_trips,
            "trips": all_trips,
            "total_ben": len(ben_trips),
            "total_thung": len(thung_trips),
            "active_ben": len([t for t in ben_trips if t.get("status_code") == "active"]),
            "active_thung": len([t for t in thung_trips if t.get("status_code") == "active"]),
            "active_count": active_count,
            "off_count": off_count,
            "active_percent": active_percent,
            "customer_breakdown": customer_breakdown,
            "sync_time": datetime.now().strftime("%H:%M:%S")
        }

        # Lưu cache
        self.cached_trips[t_date] = (now, result)
        return result

    def get_weekly_dispatch_stats(self, target_date=None):
        """
        Tính toán chính xác hoạt động tuần (7 ngày) của toàn bộ 26 xe từ bảng kê Google Sheets trong 1 lượt đọc siêu tốc.
        Mỗi chuyến chạy có cự ly khứ hồi thực tế từ tuyến đường (trung bình 130km - 180km).
        """
        today_obj = date.today()
        if isinstance(target_date, str):
            try:
                base_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except Exception:
                base_date = today_obj
        elif isinstance(target_date, date):
            base_date = target_date
        else:
            base_date = today_obj

        cache_key = f"weekly_{base_date.strftime('%Y-%m-%d')}"

        now = time.time()
        if cache_key in self.cached_weekly_stats:
            ts, stats = self.cached_weekly_stats[cache_key]
            if now - ts < 600: # Cache 10 phút
                return stats

        days_to_fetch = [base_date - timedelta(days=i) for i in range(7)]
        # 7 ngày có thể nằm ở 2 tháng (vd 03/11 lùi về 28/10) -> đọc từng file tháng
        days_by_month = {}
        for d in days_to_fetch:
            days_by_month.setdefault(month_key(d), []).append(d)

        truck_stats = {}
        try:
          for mk, month_days in days_by_month.items():
            try:
                sheet_id = self.get_sheet_id_for(month_days[0])
            except SheetNotFoundError as e:
                print(f"[weekly] {e}")
                continue
            data = self._get_xlsx_bytes(sheet_id)
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
            for d in month_days:
                s_name = find_day_sheet(wb.sheetnames, d.day)
                if not s_name:
                    continue
                rows = [[str(c).strip() if c is not None else "" for c in r]
                        for r in wb[s_name].iter_rows(values_only=True)]
                ben, thung = parse_dispatch_rows(rows, d.strftime("%d/%m/%Y"))
                for t in ben + thung:
                    clean_p = t["clean_plate"]
                    st = truck_stats.setdefault(clean_p, {
                        "plate_number": t["plate_number"],
                        "trailer_number": "",
                        "driver_name": t["driver_name"],
                        "active_days": 0,
                        "total_trips": 0,
                        "routes": set(),
                        "estimated_km": 0.0,
                    })
                    if t["status_code"] != "active":
                        continue
                    st["active_days"] += 1
                    legs = t.get("legs") or [{"origin": t["origin"], "dest": t["destination"]}]
                    for leg in legs:
                        st["total_trips"] += 1
                        st["estimated_km"] += estimate_leg_km(leg.get("dest", ""))
                        if leg.get("origin") and leg.get("dest"):
                            st["routes"].add(f"{leg['origin']} ➔ {leg['dest']}")

          self.cached_weekly_stats[cache_key] = (now, truck_stats)
        except Exception as e:
            print(f"Error calculating weekly stats: {e}")

        return truck_stats

    def fetch_maintenance_sheet(self):
        now = time.time()
        if self.cached_maintenance:
            ts, data = self.cached_maintenance
            if now - ts < 120:
                return data

        try:
            req = urllib.request.Request(SHEET2_MAINTENANCE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode("utf-8", errors="ignore")

            reader = csv.reader(io.StringIO(content))
            rows = list(reader)

            maintenance_list = []
            count = 0
            for r in rows:
                if len(r) > 2 and r[1].strip().isdigit():
                    stt = int(r[1].strip())
                    if stt != count + 1 or count >= 25:
                        continue
                    count += 1

                    raw_plate = r[2].strip()
                    clean_p = raw_plate.replace(" ", "").replace("-", "").replace(".", "").upper()
                    if len(clean_p) == 8:
                        plate_formatted = f"{clean_p[:3]}-{clean_p[3:6]}.{clean_p[6:]}"
                    else:
                        plate_formatted = raw_plate

                    norm = r[3].strip() if len(r) > 3 and r[3].strip() else "15.000"
                    last_km = r[4].strip() if len(r) > 4 and r[4].strip() else "—"
                    last_date = r[5].strip() if len(r) > 5 and r[5].strip() else "—"
                    current_km = r[6].strip() if len(r) > 6 and r[6].strip() else "—"
                    due_km = r[8].strip() if len(r) > 8 and r[8].strip() else "—"
                    remaining_km = r[9].strip() if len(r) > 9 and r[9].strip() else "—"
                    status_text = r[10].strip() if len(r) > 10 and r[10].strip() else ""
                    notes = r[11].strip() if len(r) > 11 else ""

                    if not status_text:
                        if remaining_km and remaining_km != "—":
                            try:
                                rem_num = float(remaining_km.replace(".", "").replace(",", "."))
                                if rem_num < 0:
                                    status_text = "Sắp / quá hạn"
                                elif rem_num < 3000:
                                    status_text = "Gần tới hạn"
                                else:
                                    status_text = "Còn xa"
                            except Exception:
                                status_text = "Còn xa"
                        else:
                            status_text = "Thiếu số liệu"

                    maintenance_list.append({
                        "stt": stt,
                        "plate_number": plate_formatted,
                        "raw_plate": raw_plate,
                        "norm_km": norm,
                        "last_km": last_km,
                        "last_date": last_date,
                        "current_km": current_km,
                        "due_km": due_km,
                        "remaining_km": remaining_km,
                        "status": status_text,
                        "status_text": status_text,
                        "notes": notes
                    })

            if maintenance_list:
                self.cached_maintenance = (now, maintenance_list)
                return maintenance_list
        except Exception as e:
            print(f"Error fetching maintenance sheet: {e}")
            if self.cached_maintenance:
                return self.cached_maintenance[1]
        return []

    def fetch_vehicles_sheet(self):
        now = time.time()
        if self.cached_vehicles:
            ts, data = self.cached_vehicles
            if now - ts < 300:
                return data

        try:
            req = urllib.request.Request(SHEET2_VEHICLES_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode("utf-8", errors="ignore")

            reader = csv.reader(io.StringIO(content))
            rows = list(reader)

            ben_vehicles = []
            thung_vehicles = []
            is_thung = False

            for r in rows:
                if not r or len(r) < 2:
                    continue
                first = r[0].strip().upper()
                if "XE CÔNG DÀI" in first or "XE THÙNG" in first:
                    is_thung = True
                    continue
                if "XE BEN" in first:
                    is_thung = False
                    continue

                if len(r) > 2 and r[1].strip().isdigit():
                    v_item = {
                        "stt": int(r[1].strip()),
                        "plate_number": r[2].strip() if len(r) > 2 else "",
                        "trailer_number": r[3].strip() if len(r) > 3 else "",
                        "driver_name": r[4].strip() if len(r) > 4 else "",
                        "phone": r[5].strip() if len(r) > 5 else "",
                        "driver_status": r[6].strip() if len(r) > 6 else "Bình thường"
                    }
                    if is_thung:
                        thung_vehicles.append(v_item)
                    else:
                        ben_vehicles.append(v_item)

            res = {"ben": ben_vehicles, "thung": thung_vehicles}
            self.cached_vehicles = (now, res)
            return res
        except Exception as e:
            print(f"Error fetching vehicles sheet: {e}")
            if self.cached_vehicles:
                return self.cached_vehicles[1]
            return {"ben": [], "thung": []}

sheets_client = GoogleSheetsSyncService()
