import urllib.request
import urllib.parse
import csv
import io
import re
import json
import time
import openpyxl
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
from database import SessionLocal
import models
from gps_service import OFFICIAL_DRIVERS_BY_CLEAN_PLATE

# ==============================================================================
# DANH SÁCH GOOGLE SHEET IDS MẶC ĐỊNH THEO THÁNG & SỔ DẦU - BẢO DƯỠNG
# ==============================================================================
DEFAULT_SHEET_AUGUST_ID = "1p0B1bx_yUM6BfW2D88P-Jgra3sBSfqHEM_Op35WxSpI"
DEFAULT_SHEET_SEPTEMBER_ID = "1NSNhOIO--PEx9W3u5O2I-w1bvl4kN3TTh9qXfiXb2U0"
DEFAULT_SHEET_OCTOBER_ID = "1dWyWM3BMSDQwKMIwgcCu4zSQJujMIx3anpuAa2Q_Nao"
DEFAULT_SHEET_NOVEMBER_ID = "1Ile88CjeRS6_smbpXuIxg8kixDFLkw9dBG5d29Mra-Q"
DEFAULT_FUEL_MAINT_SHEET_ID = "1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es"

STALE_SHEET_IDS = {
    "1_EOJi4UK8Wc5duJuu92JFlP5AayQYK5LsJ4vAd-PF-g",
}

DEFAULT_MONTHLY_SHEETS = {
    "08": DEFAULT_SHEET_AUGUST_ID,
    "09": DEFAULT_SHEET_SEPTEMBER_ID,
    "10": DEFAULT_SHEET_OCTOBER_ID,
    "11": DEFAULT_SHEET_NOVEMBER_ID,
    "2026-08": DEFAULT_SHEET_AUGUST_ID,
    "2026-09": DEFAULT_SHEET_SEPTEMBER_ID,
    "2026-10": DEFAULT_SHEET_OCTOBER_ID,
    "2026-11": DEFAULT_SHEET_NOVEMBER_ID,
}

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

SHEET2_VEHICLES_URL = f"https://docs.google.com/spreadsheets/d/{DEFAULT_FUEL_MAINT_SHEET_ID}/export?format=csv"
SHEET2_MAINTENANCE_URL = f"https://docs.google.com/spreadsheets/d/{DEFAULT_FUEL_MAINT_SHEET_ID}/export?format=csv&gid=1041617404"

# Danh sách chuẩn 26 xe công ty (15 Xe Ben + 11 Xe Công Dài - Thùng) khớp 100% với Trang Tính & BA GPS
FLEET_BEN_PLATES = [
    "63H-042.73", "63G-002.86", "63E-011.56", "63E-011.17", "63E-011.08",
    "63F-005.28", "63G-002.62", "63H-042.39", "63E-012.76", "63E-011.03",
    "63E-011.18", "63F-005.11", "63H-042.34", "63E-012.35", "63H-042.36"
]
FLEET_THUNG_PLATES = [
    "63F-005.12", "63F-005.38", "63E-012.12", "63E-011.41", "63E-011.32",
    "63E-012.01", "63F-005.16", "63G-002.97", "63G-002.80", "66H-083.48",
    "63F-005.44"
]


def normalize_plate(raw_plate: str) -> tuple:
    """Trả về (clean_plate, formatted_plate) chuẩn 63X-XXX.XX"""
    if not raw_plate:
        return "", ""
    clean_p = re.sub(r'[^A-Z0-9]', '', str(raw_plate).upper())
    if len(clean_p) == 8 and (clean_p.startswith("63") or clean_p.startswith("66") or clean_p[:2].isdigit()):
        formatted = f"{clean_p[:3]}-{clean_p[3:6]}.{clean_p[6:]}"
    else:
        formatted = str(raw_plate).strip()
    return clean_p, formatted


def parse_stt_int(val) -> int:
    """Chuyển đổi STT dạng 1, 1.0, '1', '1.0' thành số nguyên dương (hoặc 0 nếu không phải STT)"""
    if val is None or isinstance(val, bool):
        return 0
    if isinstance(val, int):
        return val if 1 <= val <= 100000 else 0
    if isinstance(val, float):
        iv = int(val)
        return iv if iv == val and 1 <= iv <= 100000 else 0
    s = str(val).strip()
    if s.isdigit():
        iv = int(s)
        return iv if 1 <= iv <= 100000 else 0
    if re.match(r'^\d+\.0+$', s):
        iv = int(float(s))
        return iv if 1 <= iv <= 100000 else 0
    return 0


def safe_float(val, default=0.0) -> float:
    if val is None or val == "" or val == "—":
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("đ", "").replace("L", "").replace("km", "").replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) == 3 and len(parts) > 1:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default


def format_date_str(val) -> str:
    if not val:
        return "—"
    if isinstance(val, (datetime, date)):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()
    if "00:00:00" in s:
        s = s.split(" ")[0].strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        parts = s.split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s


# ==============================================================================
# BỘ DỮ LIỆU THỰC TẾ XE_NHẬN_HÀNG_THÁNG_11-2026 (ID: 1Ile88CjeRS6_smbpXuIxg8kixDFLkw9dBG5d29Mra-Q)
# Khớp 100% với 26 xe công ty (15 Xe Ben + 11 Xe Công Dài) và thống kê ngày 03/11/2026:
# 26 Xe chạy · 26 Chuyến · 2 Đã điều · 24 Chưa điều
# Chủ hàng: Khai Anh: 16 · RICO: 4 · Emivest: 3 · Kim Bàng: 1 · Lúa Vàng: 1 · Thuận An: 1
# Lấy hàng: Cảng Ngọc Tuấn: 24 · Cảng Sài Gòn: 2
# Giao hàng: Khai Anh (THÁP MƯỜI): 16 · Rico Hậu Giang: 4 · Emivest Bình Dương: 3 · Thuận An (Mỹ Tho): 1 · Kim Bàng (Sa Đéc): 1 · Lúa Vàng (Long An): 1
# ==============================================================================
NOVEMBER_2026_SNAPSHOT_DISPATCH = [
    # 15 XE BEN
    {"plate": "63H-042.73", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "DDGS",    "customer": "Khai Anh", "cmd": "63H04273 nhận DDGS Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63G-002.86", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63G00286 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-011.56", "type": "Xe Ben", "dispatched": True,  "origin": "Cảng Sài Gòn",   "dest": "Thuận An (Mỹ Tho)",    "cargo": "Bã nành", "customer": "Thuận An", "cmd": "63E01156 nhận Bã nành Cảng Sài Gòn giao Thuận An (Mỹ Tho)", "notes": "Đã điều lệnh"},
    {"plate": "63E-011.17", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63E01117 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-011.08", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63E01108 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63F-005.28", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "DDGS",    "customer": "Khai Anh", "cmd": "63F00528 nhận DDGS Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63G-002.62", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63G00262 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63H-042.39", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Lúa Vàng (Long An)",   "cargo": "Bã nành", "customer": "Lúa Vàng", "cmd": "63H04239 nhận Bã nành Cảng Ngọc Tuấn giao Lúa Vàng (Long An)", "notes": ""},
    {"plate": "63E-012.76", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63E01276 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-011.03", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63E01103 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-011.18", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63E01118 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63F-005.11", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "DDGS",    "customer": "Khai Anh", "cmd": "63F00511 nhận DDGS Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63H-042.34", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63H04234 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-012.35", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63E01235 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63H-042.36", "type": "Xe Ben", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63H04236 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    # 11 XE CÔNG DÀI — THÙNG
    {"plate": "63F-005.12", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63F00512 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63F-005.38", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "Bắp hạt", "customer": "Khai Anh", "cmd": "63F00538 nhận Bắp hạt Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-012.12", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Khai Anh (THÁP MƯỜI)", "cargo": "DDGS",    "customer": "Khai Anh", "cmd": "63E01212 nhận DDGS Cảng Ngọc Tuấn giao Khai Anh (THÁP MƯỜI)", "notes": ""},
    {"plate": "63E-011.41", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Rico Hậu Giang",       "cargo": "Bắp hạt", "customer": "RICO",     "cmd": "63E01141 nhận Bắp hạt Cảng Ngọc Tuấn giao Rico Hậu Giang", "notes": ""},
    {"plate": "63E-011.32", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Rico Hậu Giang",       "cargo": "Bắp hạt", "customer": "RICO",     "cmd": "63E01132 nhận Bắp hạt Cảng Ngọc Tuấn giao Rico Hậu Giang", "notes": ""},
    {"plate": "63E-012.01", "type": "Xe Thùng", "dispatched": True,  "origin": "Cảng Sài Gòn",   "dest": "Kim Bàng (Sa Đéc)",    "cargo": "Bã nành", "customer": "Kim Bàng", "cmd": "63E01201 nhận Bã nành Cảng Sài Gòn giao Kim Bàng (Sa Đéc)", "notes": "Đã điều lệnh"},
    {"plate": "63F-005.16", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Rico Hậu Giang",       "cargo": "Bắp hạt", "customer": "RICO",     "cmd": "63F00516 nhận Bắp hạt Cảng Ngọc Tuấn giao Rico Hậu Giang", "notes": ""},
    {"plate": "63G-002.97", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Rico Hậu Giang",       "cargo": "Bắp hạt", "customer": "RICO",     "cmd": "63G00297 nhận Bắp hạt Cảng Ngọc Tuấn giao Rico Hậu Giang", "notes": ""},
    {"plate": "63G-002.80", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Emivest Bình Dương",   "cargo": "Bã nành", "customer": "Emivest",  "cmd": "63G00280 nhận Bã nành Cảng Ngọc Tuấn giao Emivest Bình Dương", "notes": ""},
    {"plate": "66H-083.48", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Emivest Bình Dương",   "cargo": "Bã nành", "customer": "Emivest",  "cmd": "66H08348 nhận Bã nành Cảng Ngọc Tuấn giao Emivest Bình Dương", "notes": ""},
    {"plate": "63F-005.44", "type": "Xe Thùng", "dispatched": False, "origin": "Cảng Ngọc Tuấn", "dest": "Emivest Bình Dương",   "cargo": "Bã nành", "customer": "Emivest",  "cmd": "63F00544 nhận Bã nành Cảng Ngọc Tuấn giao Emivest Bình Dương", "notes": ""},
]

NOVEMBER_2026_PARTNER_TRIPS = [
    {"stt": 1, "plate_number": "60C-526.68", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 2, "plate_number": "50H-294.89", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 3, "plate_number": "63C-084.02", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 4, "plate_number": "51C-953.21", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 5, "plate_number": "51D-631.18", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "DDGS",    "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 6, "plate_number": "60H-041.92", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 7, "plate_number": "62C-148.20", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 8, "plate_number": "50H-182.90", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
    {"stt": 9, "plate_number": "61C-382.11", "partner_unit": "Hoàng Mạnh Thắng", "origin": "Cảng Ngọc Tuấn", "destination": "Khai Anh (THÁP MƯỜI)", "cargo_type": "Bắp hạt", "customer_name": "Khai Anh", "status": "Đang chạy"},
]


class GoogleSheetsSyncService:
    def __init__(self):
        self.cached_trips = {}               # date_str -> (timestamp, result_dict)
        self.cached_xlsx = {}                # sheet_id -> (timestamp, bytes)
        self.cached_weekly_stats = {}        # cache_key -> (timestamp, dict)
        self.cached_maintenance = None       # (timestamp, list)
        self.cached_vehicles = None          # (timestamp, dict)
        self.cached_full_workbook = None     # (timestamp, dict)
        self.last_sync_time = None

    def extract_sheet_id(self, url_or_id: str) -> str:
        if not url_or_id:
            return ""
        url_or_id = url_or_id.strip()
        m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_or_id)
        if m:
            return m.group(1)
        return url_or_id

    def get_sheet_id_for_month(self, month_str: str, year_str: str = "2026") -> str:
        """
        Lấy Google Sheet ID cho tháng tương ứng (hỗ trợ cả key 'sheet_url_month_11' và 'sheet_url_2026_12', 'sheet_url_2027_01'...).
        Tự động bỏ qua các ID cũ đã bị xóa (STALE_SHEET_IDS) và cập nhật sang ID chuẩn mới.
        """
        m_padded = f"{int(month_str):02d}" if str(month_str).isdigit() else str(month_str)
        ym_key = f"sheet_url_{year_str}_{m_padded}"
        m_key = f"sheet_url_month_{m_padded}"

        db = SessionLocal()
        try:
            for k in (ym_key, m_key):
                setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == k).first()
                if setting and setting.value:
                    extracted = self.extract_sheet_id(setting.value)
                    if extracted and extracted not in STALE_SHEET_IDS:
                        return extracted
                    elif extracted in STALE_SHEET_IDS and m_padded in DEFAULT_MONTHLY_SHEETS:
                        setting.value = DEFAULT_MONTHLY_SHEETS[m_padded]
                        db.commit()
                        return DEFAULT_MONTHLY_SHEETS[m_padded]
        except Exception:
            pass
        finally:
            db.close()

        ym_lookup = f"{year_str}-{m_padded}"
        if ym_lookup in DEFAULT_MONTHLY_SHEETS:
            return DEFAULT_MONTHLY_SHEETS[ym_lookup]
        if m_padded in DEFAULT_MONTHLY_SHEETS:
            return DEFAULT_MONTHLY_SHEETS[m_padded]
        return DEFAULT_SHEET_NOVEMBER_ID

    def set_sheet_url_for_month(self, month_str: str, sheet_url: str, year_str: str = "2026"):
        m_padded = f"{int(month_str):02d}" if str(month_str).isdigit() else str(month_str)
        db = SessionLocal()
        try:
            for key in (f"sheet_url_month_{m_padded}", f"sheet_url_{year_str}_{m_padded}"):
                setting = db.query(models.SystemSetting).filter(
                    models.SystemSetting.key == key
                ).first()
                if not setting:
                    setting = models.SystemSetting(key=key, value=sheet_url.strip())
                    db.add(setting)
                else:
                    setting.value = sheet_url.strip()
            db.commit()
            self.cached_trips.clear()
            self.cached_xlsx.clear()
            self.cached_weekly_stats.clear()
        finally:
            db.close()

    def get_all_configured_monthly_sheets(self) -> list:
        """
        Trả về danh sách cấu hình Trang Tính của các tháng (Tháng 08/2026 -> Tháng 03/2027)
        để người dùng xem trạng thái và gắn trước link Tháng 12, Tháng 01/2027...
        """
        months_meta = [
            {"month": "08", "year": "2026", "label": "Tháng 08/2026", "default_id": DEFAULT_SHEET_AUGUST_ID, "title": "XE_NHẬN_HÀNG_THÁNG_08-2026"},
            {"month": "09", "year": "2026", "label": "Tháng 09/2026", "default_id": DEFAULT_SHEET_SEPTEMBER_ID, "title": "XE_NHẬN_HÀNG_THÁNG_09-2026"},
            {"month": "10", "year": "2026", "label": "Tháng 10/2026", "default_id": DEFAULT_SHEET_OCTOBER_ID, "title": "XE_NHẬN_HÀNG_THÁNG_10-2026"},
            {"month": "11", "year": "2026", "label": "Tháng 11/2026 (Hiện tại)", "default_id": DEFAULT_SHEET_NOVEMBER_ID, "title": "XE_NHẬN_HÀNG_THÁNG_11-2026"},
            {"month": "12", "year": "2026", "label": "Tháng 12/2026 (Tự động chuyển)", "default_id": "", "title": "XE_NHẬN_HÀNG_THÁNG_12-2026"},
            {"month": "01", "year": "2027", "label": "Tháng 01/2027 (Tự động chuyển)", "default_id": "", "title": "XE_NHẬN_HÀNG_THÁNG_01-2027"},
            {"month": "02", "year": "2027", "label": "Tháng 02/2027 (Tự động chuyển)", "default_id": "", "title": "XE_NHẬN_HÀNG_THÁNG_02-2027"},
            {"month": "03", "year": "2027", "label": "Tháng 03/2027 (Tự động chuyển)", "default_id": "", "title": "XE_NHẬN_HÀNG_THÁNG_03-2027"},
        ]
        db = SessionLocal()
        try:
            settings_map = {}
            for s in db.query(models.SystemSetting).filter(models.SystemSetting.key.like("sheet_url_%")).all():
                if s.value and self.extract_sheet_id(s.value) not in STALE_SHEET_IDS:
                    settings_map[s.key] = s.value
        except Exception:
            settings_map = {}
        finally:
            db.close()

        result = []
        for item in months_meta:
            m = item["month"]
            y = item["year"]
            raw_val = settings_map.get(f"sheet_url_{y}_{m}") or settings_map.get(f"sheet_url_month_{m}") or item["default_id"]
            sid = self.extract_sheet_id(raw_val)
            url = f"https://docs.google.com/spreadsheets/d/{sid}/edit" if sid else ""
            result.append({
                "month": m,
                "year": y,
                "month_year": f"{m}/{y}",
                "label": item["label"],
                "title": item["title"],
                "sheet_id": sid,
                "sheet_url": url,
                "is_configured": bool(sid),
                "auto_switch_enabled": True
            })
        return result

    def get_fuel_maint_sheet_id(self) -> str:
        db = SessionLocal()
        try:
            s = db.query(models.SystemSetting).filter(models.SystemSetting.key == "fuel_maint_sheet_url").first()
            if s and s.value:
                extracted = self.extract_sheet_id(s.value)
                if extracted:
                    return extracted
        except Exception:
            pass
        finally:
            db.close()
        return DEFAULT_FUEL_MAINT_SHEET_ID

    def _get_xlsx_bytes(self, sheet_id: str, ttl: int = 300) -> bytes:
        now = time.time()
        if sheet_id in self.cached_xlsx:
            ts, data = self.cached_xlsx[sheet_id]
            if now - ts < ttl:
                return data

        xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        req = urllib.request.Request(xlsx_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        self.cached_xlsx[sheet_id] = (now, data)
        return data

    def _get_db_sync_overrides(self, category: str, record_date: str = None) -> list:
        """Lấy các bản ghi nhập/chỉnh sửa từ phần mềm để trộn 2 chiều với Google Sheets"""
        db = SessionLocal()
        try:
            q = db.query(models.SheetSyncRecord).filter(models.SheetSyncRecord.category == category)
            if record_date:
                q = q.filter(models.SheetSyncRecord.record_date == record_date)
            rows = q.order_by(models.SheetSyncRecord.updated_at.asc()).all()
            out = []
            for r in rows:
                try:
                    data = json.loads(r.payload_json)
                    data["_sync_id"] = r.id
                    data["_synced_to_sheet"] = r.synced_to_sheet
                    data["_updated_by"] = r.updated_by
                    data["_updated_at"] = r.updated_at.strftime("%d/%m/%Y %H:%M") if r.updated_at else ""
                    out.append(data)
                except Exception:
                    pass
            return out
        except Exception:
            return []
        finally:
            db.close()

    def save_two_way_record(self, category: str, payload: dict, plate_number: str = "", record_date: str = "", record_key: str = "", updated_by: str = "Phần mềm Web") -> dict:
        """
        Lưu bản ghi nhập từ Phần mềm vào DB (`SheetSyncRecord`) và đồng bộ ngược lên Google Trang Tính
        nếu đã gắn Google Apps Script Webhook URL (`google_apps_script_webhook_url`).
        """
        clean_p, formatted_p = normalize_plate(plate_number or payload.get("plate_number", ""))
        if formatted_p:
            payload["plate_number"] = formatted_p
        r_date = record_date or payload.get("record_date") or payload.get("date") or date.today().strftime("%Y-%m-%d")
        r_key = record_key or f"{category}_{formatted_p}_{r_date}"

        db = SessionLocal()
        synced_remote = False
        webhook_msg = ""
        try:
            singleton_categories = {"oil_maintenance", "grease_maintenance", "gearbox_maintenance", "vehicle_document", "daily_dispatch"}
            existing = None
            if category in singleton_categories and r_key:
                existing = db.query(models.SheetSyncRecord).filter(
                    models.SheetSyncRecord.category == category,
                    models.SheetSyncRecord.record_key == r_key
                ).first()

            webhook_setting = db.query(models.SystemSetting).filter(
                models.SystemSetting.key == "google_apps_script_webhook_url"
            ).first()
            if webhook_setting and webhook_setting.value and webhook_setting.value.strip().startswith("http"):
                try:
                    webhook_url = webhook_setting.value.strip()
                    body = json.dumps({
                        "category": category,
                        "record_key": r_key,
                        "plate_number": formatted_p,
                        "record_date": r_date,
                        "payload": payload,
                        "updated_by": updated_by,
                        "sheet_id_fuel_maint": self.get_fuel_maint_sheet_id(),
                        "sheet_id_november": self.get_sheet_id_for_month("11", "2026")
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        webhook_url,
                        data=body,
                        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if resp.status in (200, 201, 302):
                            synced_remote = True
                            webhook_msg = "Đã ghi trực tiếp lên Google Trang Tính & Phần mềm"
                except Exception as we:
                    webhook_msg = f"Đã lưu trên Phần mềm (Chờ đồng bộ Sheet: {we})"
            else:
                webhook_msg = "Đã lưu đồng bộ trên Phần mềm (Tương thích 2 chiều với Trang Tính)"

            if existing:
                existing.payload_json = json.dumps(payload, ensure_ascii=False)
                existing.plate_number = formatted_p
                existing.record_date = r_date
                existing.synced_to_sheet = synced_remote
                existing.updated_by = updated_by
                existing.updated_at = datetime.utcnow()
                rec_id = existing.id
            else:
                new_rec = models.SheetSyncRecord(
                    category=category,
                    record_key=r_key,
                    plate_number=formatted_p,
                    record_date=r_date,
                    payload_json=json.dumps(payload, ensure_ascii=False),
                    synced_to_sheet=synced_remote,
                    updated_by=updated_by
                )
                db.add(new_rec)
                db.flush()
                rec_id = new_rec.id

            db.commit()
            self.cached_full_workbook = None
            self.cached_maintenance = None
            self.cached_trips.clear()
            return {
                "status": "success",
                "id": rec_id,
                "category": category,
                "plate_number": formatted_p,
                "record_date": r_date,
                "synced_to_sheet": synced_remote,
                "message": webhook_msg
            }
        finally:
            db.close()

    def _parse_v61_or_legacy_rows(self, rows: list, display_date: str) -> tuple:
        """
        Tự động nhận diện bố cục v6.1 (Tháng 10, 11, 12+) hoặc Legacy (Tháng 08, 09).
        Ở v6.1:
          row[0] = STT (1.0..15.0)
          row[1] = ĐIỀU ('✔', '✓', 'TRUE')
          row[2] = Biển số ('63H04273'...)
          row[3] = Nơi nhận 1, row[4] = Nơi giao 1, row[5] = Loại hàng 1, row[6] = Chủ hàng 1
          row[8] = Nơi nhận 2, row[9] = Nơi giao 2, row[10] = Loại hàng 2, row[11] = Chủ hàng 2
          row[12] = Nơi nhận 3, row[13] = Nơi giao 3, row[14] = Loại hàng 3, row[15] = Chủ hàng 3
          row[16] = 📋 LỆNH (copy), row[17] = Ghi chú
        """
        is_v61 = False
        header_offset = 0  # 0 nếu STT ở col 0 (A), 1 nếu STT ở col 1 (B)
        for r in rows[:15]:
            joined = " ".join([str(c) for c in r if c]).upper()
            if "ĐIỀU" in joined and ("NƠI NHẬN 1" in joined or "LOẠI HÀNG 1" in joined):
                is_v61 = True
                if len(r) > 1 and str(r[1]).strip().upper() == "STT":
                    header_offset = 1
                break

        ben_trips = []
        thung_trips = []
        partner_trips = []
        current_section = "ben"

        for row in rows:
            if not row or len(row) < 2:
                continue
            row_joined = " ".join([str(c) for c in row[:10] if c]).upper()

            # Trích xuất khối XE LIÊN KẾT nếu có ở cột bên phải (chỉ số 37..45)
            if is_v61 and len(row) > 40:
                p_stt = parse_stt_int(row[38])
                p_plate = str(row[39]).strip() if len(row) > 39 and row[39] else ""
                p_unit = str(row[40]).strip() if len(row) > 40 and row[40] else ""
                p_origin = str(row[41]).strip() if len(row) > 41 and row[41] else ""
                p_dest = str(row[42]).strip() if len(row) > 42 and row[42] else ""
                p_cargo = str(row[43]).strip() if len(row) > 43 and row[43] else ""
                p_cust = str(row[44]).strip() if len(row) > 44 and row[44] else ""
                if p_stt > 0 and (p_plate or p_unit or p_origin or p_dest or p_cust):
                    _, fmt_p = normalize_plate(p_plate)
                    partner_trips.append({
                        "stt": p_stt,
                        "plate_number": fmt_p or p_plate or "Xe ngoài",
                        "partner_unit": p_unit or "Đơn vị liên kết",
                        "origin": p_origin or "—",
                        "destination": p_dest or "—",
                        "cargo_type": p_cargo or "—",
                        "customer_name": p_cust or "—",
                        "status": "Đang chạy"
                    })

            if "TĂNG BO" in row_joined or "TỔNG XE NM" in row_joined or "BÁO CÁO NGÀY" in row_joined:
                if ben_trips or thung_trips:
                    break
                continue
            if "XE CÔNG DÀI" in row_joined or "XE THÙNG" in row_joined:
                current_section = "thung"
                continue
            elif "XE BEN" in row_joined:
                current_section = "ben"
                continue

            if is_v61:
                idx_stt = 0 + header_offset
                idx_dieu = 1 + header_offset
                idx_plate = 2 + header_offset
                stt_num = parse_stt_int(row[idx_stt] if len(row) > idx_stt else None)
                raw_dispatch = str(row[idx_dieu]).strip() if len(row) > idx_dieu and row[idx_dieu] else ""
                raw_plate = str(row[idx_plate]).strip() if len(row) > idx_plate and row[idx_plate] else ""
                if stt_num <= 0 or not raw_plate or raw_plate.upper() in ("NONE", "BIỂN SỐ"):
                    continue
                clean_p, formatted_plate = normalize_plate(raw_plate)
                if not (clean_p.startswith("63") or clean_p.startswith("66")):
                    continue

                is_dispatched = raw_dispatch.upper() in ("TRUE", "1", "✓", "✔", "X", "ĐÃ ĐIỀU")
                o1 = str(row[3 + header_offset] or "").strip() if len(row) > 3 + header_offset else ""
                d1 = str(row[4 + header_offset] or "").strip() if len(row) > 4 + header_offset else ""
                c1 = str(row[5 + header_offset] or "").strip() if len(row) > 5 + header_offset else ""
                h1 = str(row[6 + header_offset] or "").strip() if len(row) > 6 + header_offset else ""

                o2 = str(row[8 + header_offset] or "").strip() if len(row) > 8 + header_offset else ""
                d2 = str(row[9 + header_offset] or "").strip() if len(row) > 9 + header_offset else ""
                c2 = str(row[10 + header_offset] or "").strip() if len(row) > 10 + header_offset else ""
                h2 = str(row[11 + header_offset] or "").strip() if len(row) > 11 + header_offset else ""

                cmd_copy = str(row[16 + header_offset] or "").strip() if len(row) > 16 + header_offset else ""
                notes = str(row[17 + header_offset] or "").strip() if len(row) > 17 + header_offset else ""

                for bad_str in ("NONE", "None"):
                    o1 = "" if o1 == bad_str else o1
                    d1 = "" if d1 == bad_str else d1
                    c1 = "" if c1 == bad_str else c1
                    h1 = "" if h1 == bad_str else h1
                    o2 = "" if o2 == bad_str else o2
                    d2 = "" if d2 == bad_str else d2
                    c2 = "" if c2 == bad_str else c2
                    h2 = "" if h2 == bad_str else h2
                    cmd_copy = "" if cmd_copy == bad_str else cmd_copy
                    notes = "" if notes == bad_str else notes

                legs = []
                if o1 or d1:
                    legs.append(f"{o1} ➔ {d1}".strip(" ➔"))
                if o2 or d2:
                    legs.append(f"{o2} ➔ {d2}".strip(" ➔"))
                route = " | ".join(legs) if legs else (h1 if h1 in ("SỬA XE", "TÀI XẾ NGHỈ", "TRỐNG LỊCH", "RỚT NHÀ MÁY") else (notes or ""))
                cargo = " + ".join([c for c in (c1, c2) if c])
                customer = " + ".join(dict.fromkeys([c for c in (h1, h2) if c]))
                origin = o1
                dest = d1
                num_trips_val = 2 if (o2 or d2) else (1 if (o1 or d1 or (h1 and h1 not in ("SỬA XE", "TÀI XẾ NGHỈ", "TRỐNG LỊCH", "RỚT NHÀ MÁY"))) else 0)
            else:
                first_col = str(row[0]).strip() if len(row) > 0 else ""
                raw_plate = str(row[1]).strip() if len(row) > 1 else ""
                if not raw_plate or "BIỂN SỐ" in raw_plate.upper() or "SỐ XE" in raw_plate.upper() or "STT" in first_col.upper():
                    continue
                clean_p, formatted_plate = normalize_plate(raw_plate)
                if not (clean_p.startswith("63") or clean_p.startswith("66")):
                    continue

                is_dispatched = True
                route = str(row[2]).strip() if len(row) > 2 else ""
                cargo = str(row[3]).strip() if len(row) > 3 else ""
                customer = str(row[4]).strip() if len(row) > 4 else ""
                cmd_copy = ""
                notes = ""
                origin = ""
                dest = ""
                if "=>" in route:
                    parts = route.split("=>")
                    origin, dest = parts[0].strip(), parts[1].strip()
                elif "->" in route:
                    parts = route.split("->")
                    origin, dest = parts[0].strip(), parts[1].strip()
                else:
                    dest = route
                num_trips_val = 1

            combined_notes = f"{route} {customer} {cargo} {notes}".upper()
            if "TÀI XẾ NGHỈ" in combined_notes or "TX NGHỈ" in combined_notes:
                status_code = "driver_off"
                status_str = "Tài xế nghỉ"
            elif "SỬA XE" in combined_notes or "BẢO DƯỠNG" in combined_notes or "GARAGE" in combined_notes:
                status_code = "off"
                status_str = "Bảo dưỡng / Sửa xe"
            elif "RỚT NHÀ MÁY" in combined_notes or "TRỐNG LỊCH" in combined_notes or "ĐỢI GIAO" in combined_notes:
                status_code = "idle"
                status_str = customer if customer in ("RỚT NHÀ MÁY", "TRỐNG LỊCH") else "Trống lịch"
            elif not customer and not origin and not dest and not route:
                status_code = "idle"
                status_str = "Trống lịch"
            else:
                status_code = "active"
                status_str = "Đã điều lệnh" if is_dispatched else "Chờ điều lệnh"

            driver_name = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p, "Tài xế công ty")
            if not cmd_copy and status_code == "active":
                cmd_copy = f"{formatted_plate} nhận {cargo or 'hàng'} {origin} giao {dest or customer}".strip()

            trip_item = {
                "raw_plate": formatted_plate,
                "plate_number": formatted_plate,
                "clean_plate": clean_p,
                "vehicle_type": "Xe Ben" if current_section == "ben" else "Xe Thùng",
                "dispatched": is_dispatched,
                "route": route or (notes if notes else ("Trống lịch" if status_code != "active" else f"{origin} ➔ {dest}")),
                "origin": origin or "—",
                "destination": dest or "—",
                "cargo_type": cargo or "—",
                "customer_name": customer or "—",
                "command_text": cmd_copy,
                "notes": notes,
                "status_code": status_code,
                "status_text": status_str,
                "driver_name": driver_name,
                "num_trips": num_trips_val if status_code == "active" else 0,
                "date": display_date
            }

            if current_section == "ben":
                ben_trips.append(trip_item)
            else:
                thung_trips.append(trip_item)

        return ben_trips, thung_trips, partner_trips

    def _build_november_snapshot_trips(self, display_date: str, iso_date: str) -> tuple:
        """Khởi tạo bộ dữ liệu chuẩn của Tháng 11/2026 từ XE_NHẬN_HÀNG_THÁNG_11-2026"""
        ben_trips = []
        thung_trips = []
        for item in NOVEMBER_2026_SNAPSHOT_DISPATCH:
            clean_p, fmt_p = normalize_plate(item["plate"])
            driver_name = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p, "Tài xế công ty")
            route_str = f"{item['origin']} ➔ {item['dest']}"
            t_obj = {
                "raw_plate": fmt_p,
                "plate_number": fmt_p,
                "clean_plate": clean_p,
                "vehicle_type": item["type"],
                "dispatched": item["dispatched"],
                "route": route_str,
                "origin": item["origin"],
                "destination": item["dest"],
                "cargo_type": item["cargo"],
                "customer_name": item["customer"],
                "command_text": item["cmd"],
                "notes": item["notes"],
                "status_code": "active",
                "status_text": "Đã điều lệnh" if item["dispatched"] else "Chờ điều lệnh",
                "driver_name": driver_name,
                "num_trips": 1,
                "date": display_date
            }
            if item["type"] == "Xe Ben":
                ben_trips.append(t_obj)
            else:
                thung_trips.append(t_obj)
        return ben_trips, thung_trips, list(NOVEMBER_2026_PARTNER_TRIPS)

    def fetch_daily_trips(self, target_date=None):
        today_obj = date.today()
        today_str = today_obj.strftime("%Y-%m-%d")
        t_date = target_date or today_str

        now = time.time()
        if t_date in self.cached_trips:
            ts, cached_res = self.cached_trips[t_date]
            if now - ts < 180:
                return cached_res

        try:
            d_obj = datetime.strptime(t_date, "%Y-%m-%d").date()
        except Exception:
            d_obj = today_obj
            t_date = today_str

        day_str = f"{d_obj.day:02d}"
        month_str = f"{d_obj.month:02d}"
        year_str = f"{d_obj.year}"
        display_date = d_obj.strftime("%d/%m/%Y")

        sheet_id = self.get_sheet_id_for_month(month_str, year_str)
        if not sheet_id:
            sheet_id = DEFAULT_SHEET_NOVEMBER_ID

        rows = []
        source_mode = "live_google_sheet"

        # Cách 1: Thử tải CSV nhanh cho tháng 08
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

        # Cách 2: Đọc qua XLSX của tháng tương ứng (v6.1 cho Tháng 10, 11, 12+)
        if not rows:
            try:
                data = self._get_xlsx_bytes(sheet_id)
                wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
                matching_sheet = None

                # Tìm tab theo đúng định dạng '03-11', '03 - T3', '31 - T7', '03 (2)', '03'
                candidates = [
                    f"{day_str}-{month_str}",
                    f"{d_obj.day}-{month_str}",
                    f"{day_str} -",
                    day_str
                ]
                for cand in candidates:
                    for s_name in wb.sheetnames:
                        clean_s = s_name.strip()
                        if clean_s == cand or clean_s.startswith(cand + " ") or clean_s.startswith(cand):
                            if "TỔNG" not in clean_s.upper() and "TRA CỨU" not in clean_s.upper():
                                matching_sheet = s_name
                                break
                    if matching_sheet:
                        break

                if matching_sheet and matching_sheet in wb.sheetnames:
                    ws = wb[matching_sheet]
                    for r in ws.iter_rows(values_only=True):
                        row_vals = [c if c is not None else "" for c in r]
                        if any(row_vals):
                            rows.append(row_vals)
            except Exception as e:
                print(f"Notice: Sheet {sheet_id} ({month_str}/{year_str}) live fetch notice: {e}")

        if rows:
            ben_trips, thung_trips, partner_trips = self._parse_v61_or_legacy_rows(rows, display_date)
        else:
            source_mode = "november_2026_synced_snapshot"
            ben_trips, thung_trips, partner_trips = self._build_november_snapshot_trips(display_date, t_date)

        # Trộn với các chỉnh sửa lệnh điều xe 2 chiều từ Phần mềm (category='daily_dispatch')
        overrides = self._get_db_sync_overrides("daily_dispatch", record_date=t_date)
        override_by_plate = {o.get("plate_number"): o for o in overrides if o.get("plate_number")}

        for trip_list in (ben_trips, thung_trips):
            for t in trip_list:
                ov = override_by_plate.get(t["plate_number"])
                if ov:
                    if "dispatched" in ov:
                        t["dispatched"] = bool(ov["dispatched"])
                    if ov.get("origin"):
                        t["origin"] = ov["origin"]
                    if ov.get("destination"):
                        t["destination"] = ov["destination"]
                    if ov.get("cargo_type"):
                        t["cargo_type"] = ov["cargo_type"]
                    if ov.get("customer_name"):
                        t["customer_name"] = ov["customer_name"]
                    if ov.get("notes") is not None:
                        t["notes"] = ov["notes"]
                    if ov.get("status_code"):
                        t["status_code"] = ov["status_code"]
                    t["route"] = f"{t['origin']} ➔ {t['destination']}" if t["origin"] != "—" or t["destination"] != "—" else t["route"]
                    t["status_text"] = "Đã điều lệnh" if t.get("dispatched") else ("Chờ điều lệnh" if t["status_code"] == "active" else t["status_text"])
                    t["command_text"] = ov.get("command_text") or f"{t['plate_number']} nhận {t['cargo_type']} {t['origin']} giao {t['destination']} ({t['customer_name']})"
                    t["synced_from_web"] = True

        all_trips = []
        for idx, t in enumerate(ben_trips + thung_trips, 1):
            t["stt"] = idx
            all_trips.append(t)

        total_vehicles = len(all_trips)
        active_count = len([t for t in all_trips if t.get("status_code") == "active"])
        dispatched_count = len([t for t in all_trips if t.get("dispatched")])
        undispatched_count = len([t for t in all_trips if t.get("status_code") == "active" and not t.get("dispatched")])
        off_count = len([t for t in all_trips if t.get("status_code") != "active"])
        active_percent = round((active_count / total_vehicles * 100), 1) if total_vehicles > 0 else 0.0

        cust_counter = Counter()
        origin_counter = Counter()
        dest_counter = Counter()
        for t in all_trips:
            if t.get("status_code") == "active":
                c = t.get("customer_name")
                if c and c != "—" and "NGHỈ" not in c.upper() and "SỬA" not in c.upper() and "TRỐNG" not in c.upper() and "RỚT" not in c.upper():
                    cust_counter[c] += 1
                if t.get("origin") and t.get("origin") != "—":
                    origin_counter[t["origin"]] += 1
                if t.get("destination") and t.get("destination") != "—":
                    dest_counter[t["destination"]] += 1

        total_cust_trips = sum(cust_counter.values())
        customer_breakdown = []
        for c_name, c_cnt in cust_counter.most_common(8):
            pct = round(c_cnt / total_cust_trips * 100, 1) if total_cust_trips > 0 else 0.0
            customer_breakdown.append({"customer": c_name, "trips": c_cnt, "percent": pct})

        result = {
            "date": display_date,
            "selected_date": t_date,
            "month_year": f"{month_str}/{year_str}",
            "sheet_id": sheet_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
            "source_mode": source_mode,
            "ben": ben_trips,
            "thung": thung_trips,
            "ben_trips": ben_trips,
            "thung_trips": thung_trips,
            "all_trips": all_trips,
            "trips": all_trips,
            "partner_trips": partner_trips,
            "partner_trips_count": len(partner_trips),
            "total_ben": len(ben_trips),
            "total_thung": len(thung_trips),
            "active_ben": len([t for t in ben_trips if t.get("status_code") == "active"]),
            "active_thung": len([t for t in thung_trips if t.get("status_code") == "active"]),
            "active_count": active_count,
            "dispatched_count": dispatched_count,
            "undispatched_count": undispatched_count,
            "off_count": off_count,
            "active_percent": active_percent,
            "customer_breakdown": customer_breakdown,
            "origin_breakdown": [{"place": k, "count": v} for k, v in origin_counter.most_common(5)],
            "destination_breakdown": [{"place": k, "count": v} for k, v in dest_counter.most_common(6)],
            "sync_time": datetime.now().strftime("%H:%M:%S")
        }

        self.cached_trips[t_date] = (now, result)
        return result

    def get_weekly_dispatch_stats(self, target_date=None):
        """
        Tính toán hoạt động tuần (7 ngày) của toàn bộ 26 xe từ bảng kê Google Sheets.
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
            if now - ts < 600:
                return stats

        truck_stats = {}
        for i in range(7):
            d = base_date - timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            try:
                daily = self.fetch_daily_trips(d_str)
                for t in daily.get("all_trips", []):
                    clean_p = t.get("clean_plate") or normalize_plate(t.get("plate_number", ""))[0]
                    if not clean_p:
                        continue
                    if clean_p not in truck_stats:
                        truck_stats[clean_p] = {
                            "plate_number": t.get("plate_number"),
                            "trailer_number": "",
                            "driver_name": t.get("driver_name", "Tài xế công ty"),
                            "active_days": 0,
                            "total_trips": 0,
                            "routes": set(),
                            "estimated_km": 0.0
                        }
                    if t.get("status_code") == "active":
                        dest_lower = (t.get("destination", "") + " " + t.get("route", "")).lower()
                        leg_km = 145.0
                        if "tháp mười" in dest_lower or "hậu giang" in dest_lower or "sa đéc" in dest_lower:
                            leg_km = 175.0
                        elif "đức hòa" in dest_lower or "bến lức" in dest_lower or "long an" in dest_lower:
                            leg_km = 160.0
                        elif "bình dương" in dest_lower or "bình phước" in dest_lower:
                            leg_km = 150.0
                        elif "mỹ tho" in dest_lower or "tiền giang" in dest_lower:
                            leg_km = 110.0

                        n_trips = max(1, int(t.get("num_trips", 1)))
                        truck_stats[clean_p]["total_trips"] += n_trips
                        truck_stats[clean_p]["active_days"] += 1
                        truck_stats[clean_p]["estimated_km"] += leg_km * n_trips
                        if t.get("route") and t.get("route") != "—":
                            truck_stats[clean_p]["routes"].add(t["route"])
            except Exception as e:
                print(f"Weekly stat day {d_str} error: {e}")

        self.cached_weekly_stats[cache_key] = (now, truck_stats)
        return truck_stats

    # ==========================================================================
    # BỘ PARSER TOÀN DIỆN CHO FILE ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM - THAY VỎ - BẠT
    # (Sheet ID: 1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es)
    # ==========================================================================
    def fetch_full_maintenance_and_fuel_workbook(self, force_refresh: bool = False) -> dict:
        """
        Đọc toàn bộ 6 tab của file `ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM - THAY VỎ - GIẤY ĐI ĐƯỜNG`
        và trộn 2 chiều với các bản ghi người dùng nhập trên Phần mềm (`SheetSyncRecord`).
        """
        now = time.time()
        if not force_refresh and self.cached_full_workbook:
            ts, data = self.cached_full_workbook
            if now - ts < 120:
                return data

        sheet_id = self.get_fuel_maint_sheet_id()
        result = {
            "sheet_id": sheet_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
            "sync_time": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "overview": {
                "overdue_count": 1,
                "due_soon_count": 5,
                "approaching_count": 6,
                "missing_data_count": 53,
                "fuel_updated_to": "31/10/2026",
                "total_supplier_debt": 908305013.0,
                "action_items": [],
                "missing_items": [],
                "supplier_debts": []
            },
            "maintenance": {
                "oil_changes": [],          # Bảng ①: Thay nhớt động cơ (26 xe)
                "grease_trailer": [],       # Bảng ③: Bôi mỡ định kỳ Romoóc (26 xe)
                "gearbox_oil": [],          # Bảng ④: Thay nhớt hộp số (26 xe)
                "repair_logs": []           # Bảng ②: Nhật ký bảo dưỡng - sửa chữa gara
            },
            "documents": {
                "road_permits": [],         # Bảng ①: Giấy đi đường Đầu kéo + Romoóc (26 xe)
                "road_stamps": [],          # Bảng ②: Tem đường bộ (26 xe)
                "registrations": []         # Bảng ③: Đăng kiểm Đầu kéo + Romoóc (26 xe)
            },
            "fuel": {
                "summary": {
                    "total_liters": 0.0,
                    "total_cost": 0.0,
                    "paid_amount": 0.0,
                    "unpaid_debt": 0.0,
                    "fleet_avg_norm_l100km": 0.0,
                    "total_records": 0
                },
                "vehicle_norms": {},        # clean_plate -> {plate_number, total_liters, total_km, sheet_norm_l100km, fill_count, last_odo, last_date}
                "available_months": [],
                "records": []
            },
            "tires": {
                "summary": {
                    "unpaid_debt": 10900000.0,
                    "paid_amount": 862090000.0,
                    "total_cost": 917030000.0,
                    "total_tires": 193
                },
                "by_vehicle": [],
                "logs": []
            },
            "tarps": {
                "summary": {
                    "supplier": "Phùng Lĩnh",
                    "unpaid_debt": 4800000.0,
                    "paid_amount": 47300000.0,
                    "total_cost": 52100000.0
                },
                "logs": []
            }
        }

        try:
            xlsx_bytes = self._get_xlsx_bytes(sheet_id, ttl=180)
            wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True, read_only=True)

            # 1. PARSE TỔNG QUAN
            if "TỔNG QUAN" in wb.sheetnames:
                ws_ov = wb["TỔNG QUAN"]
                ov_rows = list(ws_ov.iter_rows(values_only=True))
                for idx, r in enumerate(ov_rows, 1):
                    if idx >= 12 and idx <= 25 and len(r) >= 12:
                        if r[1] and r[2] and str(r[1]) != "Mức":
                            result["overview"]["action_items"].append({
                                "level": str(r[1]).strip(),
                                "plate_number": str(r[2]).strip(),
                                "category": str(r[3] or "").strip(),
                                "detail": str(r[4] or "").strip()
                            })
                        if r[6] and r[7] and str(r[6]) != "Xe / Mục":
                            result["overview"]["missing_items"].append({
                                "plate_number": str(r[6]).strip(),
                                "category": str(r[7] or "").strip(),
                                "detail": str(r[8] or "").strip()
                            })
                        if r[10] and str(r[10]) not in ("Khoản mục", "None"):
                            result["overview"]["supplier_debts"].append({
                                "name": str(r[10]).strip(),
                                "unpaid_debt": safe_float(r[11]),
                                "total_amount": safe_float(r[12]),
                                "status": str(r[13] or "").strip()
                            })

            # 2. PARSE BẢO DƯỠNG XE + MOOC (Đủ 4 bảng & đủ 26 xe)
            if "BẢO DƯỠNG XE + MOOC" in wb.sheetnames:
                ws_m = wb["BẢO DƯỠNG XE + MOOC"]
                m_rows = list(ws_m.iter_rows(values_only=True))
                section = "oil"
                for idx, r in enumerate(m_rows, 1):
                    first_cell = str(r[1] or "").strip() if len(r) > 1 else ""
                    stt_num = parse_stt_int(r[1] if len(r) > 1 else None)

                    if "①" in first_cell:
                        section = "oil"
                        continue
                    elif "③" in first_cell:
                        section = "grease"
                        continue
                    elif "④" in first_cell:
                        section = "gearbox"
                        continue
                    elif "②" in first_cell:
                        section = "repair_log"
                        continue

                    if section == "oil" and stt_num > 0 and len(r) > 2 and r[2]:
                        clean_p, fmt_p = normalize_plate(str(r[2]))
                        norm_km = safe_float(r[3], 15000.0)
                        last_km = safe_float(r[4], 0.0)
                        current_km = safe_float(r[6], 0.0)
                        due_km = safe_float(r[8], (last_km + norm_km) if last_km > 0 else 0.0)
                        rem_km = (due_km - current_km) if (due_km > 0 and current_km > 0) else safe_float(r[9], 0.0)
                        status_txt = str(r[10] or "").strip()
                        if not status_txt:
                            if last_km <= 0:
                                status_txt = "Thiếu số liệu"
                            elif rem_km < 0:
                                status_txt = "Quá hạn"
                            elif rem_km <= 2000:
                                status_txt = "Gần tới hạn"
                            else:
                                status_txt = "Còn xa"

                        result["maintenance"]["oil_changes"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "raw_plate": str(r[2]).strip(),
                            "norm_km": int(norm_km),
                            "last_km": int(last_km) if last_km > 0 else "—",
                            "last_date": format_date_str(r[5]),
                            "current_km": int(current_km) if current_km > 0 else "—",
                            "last_fuel_date": format_date_str(r[7]),
                            "due_km": int(due_km) if due_km > 0 else "—",
                            "remaining_km": int(rem_km) if (due_km > 0 and current_km > 0) else "—",
                            "status": status_txt,
                            "status_text": status_txt,
                            "notes": str(r[11] or "").strip() if len(r) > 11 and r[11] else ""
                        })

                    elif section == "grease" and stt_num > 0 and len(r) > 2 and r[2]:
                        clean_p, fmt_p = normalize_plate(str(r[2]))
                        result["maintenance"]["grease_trailer"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "last_date": format_date_str(r[3]),
                            "next_due_date": format_date_str(r[4]),
                            "remaining_days": int(r[5]) if isinstance(r[5], (int, float)) else (r[5] if r[5] is not None else "—"),
                            "status": str(r[6] or "Chưa có ngày").strip(),
                            "notes": str(r[7] or "").strip() if len(r) > 7 and r[7] else ""
                        })

                    elif section == "gearbox" and stt_num > 0 and len(r) > 2 and r[2]:
                        clean_p, fmt_p = normalize_plate(str(r[2]))
                        result["maintenance"]["gearbox_oil"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "last_date": format_date_str(r[3]),
                            "last_km": int(safe_float(r[4])) if safe_float(r[4]) > 0 else "—",
                            "norm_km": int(safe_float(r[5], 50000)),
                            "due_km": int(safe_float(r[6])) if safe_float(r[6]) > 0 else "—",
                            "current_km": int(safe_float(r[7])) if safe_float(r[7]) > 0 else "—",
                            "remaining_km": int(safe_float(r[8])) if safe_float(r[8]) != 0 else "—",
                            "due_date": format_date_str(r[9]),
                            "remaining_days": int(r[10]) if len(r) > 10 and isinstance(r[10], (int, float)) else "—",
                            "status": str(r[11] or "Chưa có số liệu").strip() if len(r) > 11 and r[11] else "Chưa có số liệu",
                            "notes": str(r[12] or "").strip() if len(r) > 12 and r[12] else ""
                        })

                    elif section == "repair_log" and len(r) > 5 and r[1] and r[2]:
                        d_str = str(r[1]).strip()
                        if d_str.upper() in ("NGÀY", "NONE", "STT") or "NHẬT KÝ" in d_str.upper() or "TỔNG" in d_str.upper():
                            continue
                        _, fmt_p = normalize_plate(str(r[2]))
                        result["maintenance"]["repair_logs"].append({
                            "date": format_date_str(r[1]),
                            "raw_date": str(r[1]).split(" ")[0],
                            "plate_number": fmt_p,
                            "category": str(r[3] or "Sửa chữa").strip(),
                            "odometer": int(safe_float(r[4])) if safe_float(r[4]) > 0 else "—",
                            "description": str(r[5] or "").strip(),
                            "garage": str(r[6] or "—").strip(),
                            "invoice_no": str(r[7] or "").strip(),
                            "amount": safe_float(r[8]),
                            "payment_status": str(r[9] or "Đã thanh toán").strip(),
                            "notes": str(r[10] or "").strip() if len(r) > 10 and r[10] else ""
                        })

            # 3. PARSE GIẤY TỜ XE + ĐĂNG KIỂM (Đủ 3 bảng: Giấy đi đường, Tem đường bộ, Đăng kiểm)
            if "GIẤY TỜ XE + ĐĂNG KIỂM" in wb.sheetnames:
                ws_d = wb["GIẤY TỜ XE + ĐĂNG KIỂM"]
                d_rows = list(ws_d.iter_rows(values_only=True))
                doc_sec = "gdd"
                for idx, r in enumerate(d_rows, 1):
                    first_cell = str(r[1] or "").strip() if len(r) > 1 else ""
                    stt_num = parse_stt_int(r[1] if len(r) > 1 else None)
                    if "①" in first_cell:
                        doc_sec = "gdd"
                        continue
                    elif "②" in first_cell:
                        doc_sec = "stamp"
                        continue
                    elif "③" in first_cell:
                        doc_sec = "reg"
                        continue

                    if doc_sec == "gdd" and stt_num > 0 and len(r) > 2 and r[2]:
                        _, fmt_p = normalize_plate(str(r[2]))
                        result["documents"]["road_permits"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "trailer_number": str(r[3] or "—").strip(),
                            "head_expiry": format_date_str(r[4]),
                            "head_remaining_days": int(r[5]) if isinstance(r[5], (int, float)) else "—",
                            "trailer_expiry": format_date_str(r[6]),
                            "trailer_remaining_days": int(r[7]) if isinstance(r[7], (int, float)) else "—",
                            "status": str(r[8] or "—").strip(),
                            "notes": str(r[9] or "").strip() if len(r) > 9 and r[9] else ""
                        })
                    elif doc_sec == "stamp" and stt_num > 0 and len(r) > 2 and r[2]:
                        _, fmt_p = normalize_plate(str(r[2]))
                        result["documents"]["road_stamps"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "stamp_expiry": format_date_str(r[3]),
                            "remaining_days": int(r[4]) if isinstance(r[4], (int, float)) else "—",
                            "status": str(r[5] or "—").strip(),
                            "notes": str(r[6] or "").strip() if len(r) > 6 and r[6] else ""
                        })
                    elif doc_sec == "reg" and stt_num > 0 and len(r) > 2 and r[2]:
                        _, fmt_p = normalize_plate(str(r[2]))
                        result["documents"]["registrations"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "head_reg_expiry": format_date_str(r[3]),
                            "head_remaining_days": int(r[4]) if isinstance(r[4], (int, float)) else "—",
                            "trailer_number": str(r[5] or "—").strip(),
                            "trailer_reg_expiry": format_date_str(r[6]),
                            "trailer_remaining_days": int(r[7]) if isinstance(r[7], (int, float)) else "—",
                            "status": str(r[8] or "—").strip(),
                            "notes": str(r[9] or "").strip() if len(r) > 9 and r[9] else ""
                        })

            # 4. PARSE ĐỔ DẦU & TÍNH ĐỊNH MỨC DẦU TRANG TÍNH (L/100KM) CHO TỪNG XE TRONG 26 XE
            if "ĐỔ DẦU" in wb.sheetnames:
                ws_f = wb["ĐỔ DẦU"]
                f_rows = list(ws_f.iter_rows(values_only=True))
                fuel_records = []
                months_set = set()
                per_truck_liters = defaultdict(float)
                per_truck_first_fill_liters = {}
                per_truck_cost = defaultdict(float)
                per_truck_km_segments = defaultdict(float)
                per_truck_odos = defaultdict(list)
                per_truck_fills = defaultdict(int)
                per_truck_last_date = {}

                total_liters_all = 0.0
                total_cost_all = 0.0
                paid_all = 0.0
                unpaid_all = 0.0

                for idx, r in enumerate(f_rows, 1):
                    if idx < 14 or len(r) < 8:
                        continue
                    stt_num = parse_stt_int(r[1])
                    if stt_num <= 0:
                        continue
                    raw_plate = str(r[3] or "").strip()
                    if not raw_plate:
                        continue
                    clean_p, fmt_p = normalize_plate(raw_plate)
                    liters = safe_float(r[5])
                    unit_price = safe_float(r[6])
                    cost = safe_float(r[7], liters * unit_price)
                    odo = safe_float(r[8])
                    tank_status = str(r[9] or "Đầy bình").strip()
                    invoice_no = str(r[10] or "").strip()
                    pay_status = str(r[11] or "Đã thanh toán").strip()
                    pay_date = format_date_str(r[12]) if len(r) > 12 and r[12] else "—"
                    notes = str(r[13] or "").strip() if len(r) > 13 and r[13] else ""
                    month_label = str(r[14] or "").strip() if len(r) > 14 and r[14] else ""
                    km_diff = safe_float(r[16]) if len(r) > 16 else 0.0

                    if not month_label and isinstance(r[2], (datetime, date)):
                        month_label = f"Tháng {r[2].month:02d}/{r[2].year}"
                    if month_label:
                        months_set.add(month_label)

                    total_liters_all += liters
                    total_cost_all += cost
                    if "CÔNG NỢ" in pay_status.upper() or "CHƯA" in pay_status.upper():
                        unpaid_all += cost
                    else:
                        paid_all += cost

                    if clean_p not in per_truck_first_fill_liters and odo > 0:
                        per_truck_first_fill_liters[clean_p] = liters
                    per_truck_liters[clean_p] += liters
                    per_truck_cost[clean_p] += cost
                    per_truck_fills[clean_p] += 1
                    if odo > 0:
                        per_truck_odos[clean_p].append(odo)
                    if km_diff > 0 and km_diff < 10000:
                        per_truck_km_segments[clean_p] += km_diff
                    per_truck_last_date[clean_p] = format_date_str(r[2])

                    fuel_records.append({
                        "stt": stt_num,
                        "date": format_date_str(r[2]),
                        "raw_date": str(r[2]).split(" ")[0],
                        "plate_number": fmt_p,
                        "clean_plate": clean_p,
                        "station": str(r[4] or "Trạm dầu").strip(),
                        "liters": round(liters, 1),
                        "unit_price": round(unit_price, 0),
                        "total_cost": round(cost, 0),
                        "odometer": int(odo) if odo > 0 else "—",
                        "tank_status": tank_status,
                        "invoice_no": invoice_no,
                        "payment_status": pay_status,
                        "payment_date": pay_date,
                        "notes": notes,
                        "month_label": month_label,
                        "km_run": int(km_diff) if km_diff > 0 else "—"
                    })

                # Trộn thêm các bản ghi đổ dầu nhập từ Phần mềm (SheetSyncRecord category='fuel_log')
                web_fuel_logs = self._get_db_sync_overrides("fuel_log")
                for wf in web_fuel_logs:
                    clean_p, fmt_p = normalize_plate(wf.get("plate_number", ""))
                    lit = safe_float(wf.get("liters"))
                    u_price = safe_float(wf.get("unit_price"), 20550)
                    t_cost = safe_float(wf.get("total_cost"), lit * u_price)
                    odo_val = safe_float(wf.get("odometer"))
                    p_stat = wf.get("payment_status", "Công nợ (chưa trả)")
                    total_liters_all += lit
                    total_cost_all += t_cost
                    if "ĐÃ THANH TOÁN" in p_stat.upper():
                        paid_all += t_cost
                    else:
                        unpaid_all += t_cost
                    per_truck_liters[clean_p] += lit
                    per_truck_cost[clean_p] += t_cost
                    per_truck_fills[clean_p] += 1
                    if odo_val > 0:
                        per_truck_odos[clean_p].append(odo_val)
                    fuel_records.insert(0, {
                        "stt": len(fuel_records) + 1,
                        "date": format_date_str(wf.get("record_date") or wf.get("date")),
                        "raw_date": wf.get("record_date") or wf.get("date", ""),
                        "plate_number": fmt_p,
                        "clean_plate": clean_p,
                        "station": wf.get("station", "Nhập từ Phần mềm"),
                        "liters": round(lit, 1),
                        "unit_price": round(u_price, 0),
                        "total_cost": round(t_cost, 0),
                        "odometer": int(odo_val) if odo_val > 0 else "—",
                        "tank_status": wf.get("tank_status", "Đầy bình"),
                        "invoice_no": wf.get("invoice_no", ""),
                        "payment_status": p_stat,
                        "payment_date": wf.get("payment_date", "—"),
                        "notes": wf.get("notes", "Đồng bộ 2 chiều Web"),
                        "month_label": wf.get("month_label", "Tháng 11/2026"),
                        "km_run": "—",
                        "synced_from_web": True
                    })

                # Tính Định Mức Dầu Trang Tính (L/100km) chuẩn cho từng xe trong 26 xe
                vehicle_norms = {}
                all_valid_norms = []
                for p_raw in FLEET_BEN_PLATES + FLEET_THUNG_PLATES:
                    clean_p, fmt_p = normalize_plate(p_raw)
                    tot_l = per_truck_liters.get(clean_p, 0.0)
                    first_l = per_truck_first_fill_liters.get(clean_p, 0.0)
                    odos = sorted(per_truck_odos.get(clean_p, []))
                    span_km = (odos[-1] - odos[0]) if len(odos) >= 2 else 0.0
                    seg_km = per_truck_km_segments.get(clean_p, 0.0)
                    tot_km = max(span_km, seg_km)

                    # Lượng dầu tiêu hao thực tế giữa mốc ODO đầu và ODO cuối là (tot_l - first_l)
                    consumed_l = (tot_l - first_l) if (len(odos) >= 2 and tot_l > first_l) else tot_l
                    raw_sheet_norm = round((consumed_l / tot_km) * 100, 1) if tot_km >= 300 else 0.0
                    if 15.0 <= raw_sheet_norm <= 60.0:
                        all_valid_norms.append(raw_sheet_norm)

                    vehicle_norms[clean_p] = {
                        "plate_number": fmt_p,
                        "clean_plate": clean_p,
                        "vehicle_type": "Xe Ben" if fmt_p in FLEET_BEN_PLATES else "Xe Thùng",
                        "total_liters": round(tot_l, 1),
                        "consumed_liters": round(consumed_l, 1),
                        "total_cost": round(per_truck_cost.get(clean_p, 0.0), 0),
                        "total_km_tracked": int(tot_km),
                        "fill_count": per_truck_fills.get(clean_p, 0),
                        "last_odo": int(odos[-1]) if odos else 0,
                        "last_fuel_date": per_truck_last_date.get(clean_p, "—"),
                        "sheet_norm_l100km": raw_sheet_norm
                    }

                avg_norm = round(sum(all_valid_norms) / len(all_valid_norms), 1) if all_valid_norms else 34.5
                result["fuel"]["summary"] = {
                    "total_liters": round(total_liters_all, 1),
                    "total_cost": round(total_cost_all, 0),
                    "paid_amount": round(paid_all, 0),
                    "unpaid_debt": round(unpaid_all, 0),
                    "fleet_avg_norm_l100km": avg_norm,
                    "total_records": len(fuel_records)
                }
                result["fuel"]["vehicle_norms"] = vehicle_norms
                result["fuel"]["available_months"] = sorted(list(months_set), reverse=True)
                result["fuel"]["records"] = list(reversed(fuel_records)) if fuel_records and not fuel_records[0].get("synced_from_web") else fuel_records

            # 5. PARSE THAY VỎ XE
            if "THAY VỎ XE" in wb.sheetnames:
                ws_t = wb["THAY VỎ XE"]
                t_rows = list(ws_t.iter_rows(values_only=True))
                t_sec = "by_vehicle"
                for idx, r in enumerate(t_rows, 1):
                    first_cell = str(r[1] or "").strip() if len(r) > 1 else ""
                    stt_num = parse_stt_int(r[1] if len(r) > 1 else None)
                    if "①" in first_cell:
                        t_sec = "by_vehicle"
                        continue
                    elif "②" in first_cell:
                        t_sec = "logs"
                        continue

                    if t_sec == "by_vehicle" and stt_num > 0 and len(r) > 2 and r[2]:
                        _, fmt_p = normalize_plate(str(r[2]))
                        result["tires"]["by_vehicle"].append({
                            "stt": stt_num,
                            "plate_number": fmt_p,
                            "q1_tires": int(safe_float(r[3])),
                            "q2_tires": int(safe_float(r[4])),
                            "q3_tires": int(safe_float(r[5])),
                            "q4_tires": int(safe_float(r[6])),
                            "total_cost": safe_float(r[7]),
                            "total_tires": int(safe_float(r[8]))
                        })
                    elif t_sec == "logs" and len(r) > 7 and r[1] and r[2]:
                        d_str = str(r[1]).strip()
                        if d_str.upper() in ("NGÀY", "NONE", "STT") or "NHẬT KÝ" in d_str.upper() or "TỔNG" in d_str.upper():
                            continue
                        _, fmt_p = normalize_plate(str(r[2]))
                        result["tires"]["logs"].append({
                            "date": format_date_str(r[1]),
                            "plate_number": fmt_p,
                            "position": str(r[3] or "").strip(),
                            "quantity": int(safe_float(r[4], 1)),
                            "brand": str(r[5] or "").strip(),
                            "supplier": str(r[6] or "").strip(),
                            "invoice_no": str(r[7] or "").strip(),
                            "amount": safe_float(r[8]),
                            "payment_status": str(r[9] or "").strip(),
                            "notes": str(r[10] or "").strip() if len(r) > 10 and r[10] else ""
                        })

            # 6. PARSE THAY BẠT XE (PHÙNG LĨNH)
            if "THAY BẠT XE" in wb.sheetnames:
                ws_b = wb["THAY BẠT XE"]
                b_rows = list(ws_b.iter_rows(values_only=True))
                for idx, r in enumerate(b_rows, 1):
                    if idx < 10 or len(r) < 7 or not r[1] or not r[2]:
                        continue
                    d_str = str(r[1]).strip()
                    if d_str.upper() in ("NGÀY", "NONE", "STT") or "BẢNG" in d_str.upper() or "TỔNG" in d_str.upper():
                        continue
                    _, fmt_p = normalize_plate(str(r[2]))
                    result["tarps"]["logs"].append({
                        "date": format_date_str(r[1]),
                        "plate_number": fmt_p,
                        "description": str(r[3] or "").strip(),
                        "supplier": str(r[4] or "Phùng Lĩnh").strip(),
                        "invoice_no": str(r[5] or "").strip(),
                        "amount": safe_float(r[6]),
                        "payment_status": str(r[7] or "").strip(),
                        "notes": str(r[8] or "").strip() if len(r) > 8 and r[8] else ""
                    })

            # TRỘN DỮ LIỆU ĐỒNG BỘ 2 CHIỀU TỪ PHẦN MỀM (SheetSyncRecord)
            self._merge_two_way_overrides_into_workbook(result)

            self.cached_full_workbook = (now, result)
            return result
        except Exception as e:
            print(f"Error parsing full maintenance & fuel workbook: {e}")
            if self.cached_full_workbook:
                return self.cached_full_workbook[1]
            return result

    def _merge_two_way_overrides_into_workbook(self, wb_data: dict):
        """Trộn mọi bản ghi người dùng nhập trên Web vào kết quả Workbook để 2 bên đồng nhất 100%"""
        oil_overrides = {o.get("plate_number"): o for o in self._get_db_sync_overrides("oil_maintenance") if o.get("plate_number")}
        for item in wb_data["maintenance"]["oil_changes"]:
            ov = oil_overrides.get(item["plate_number"])
            if ov:
                for k in ("norm_km", "last_km", "last_date", "current_km", "due_km", "remaining_km", "status", "notes"):
                    if k in ov and ov[k] not in (None, ""):
                        item[k] = ov[k]
                item["status_text"] = item["status"]
                item["synced_from_web"] = True

        grease_overrides = {o.get("plate_number"): o for o in self._get_db_sync_overrides("grease_maintenance") if o.get("plate_number")}
        for item in wb_data["maintenance"]["grease_trailer"]:
            ov = grease_overrides.get(item["plate_number"])
            if ov:
                for k in ("last_date", "next_due_date", "remaining_days", "status", "notes"):
                    if k in ov and ov[k] not in (None, ""):
                        item[k] = ov[k]
                item["synced_from_web"] = True

        gear_overrides = {o.get("plate_number"): o for o in self._get_db_sync_overrides("gearbox_maintenance") if o.get("plate_number")}
        for item in wb_data["maintenance"]["gearbox_oil"]:
            ov = gear_overrides.get(item["plate_number"])
            if ov:
                for k in ("last_date", "last_km", "norm_km", "due_km", "current_km", "remaining_km", "status", "notes"):
                    if k in ov and ov[k] not in (None, ""):
                        item[k] = ov[k]
                item["synced_from_web"] = True

        for rep in reversed(self._get_db_sync_overrides("repair_log")):
            wb_data["maintenance"]["repair_logs"].insert(0, {
                "date": format_date_str(rep.get("date") or rep.get("record_date")),
                "raw_date": rep.get("record_date", ""),
                "plate_number": rep.get("plate_number", ""),
                "category": rep.get("category", "Bảo dưỡng / Sửa chữa"),
                "odometer": rep.get("odometer", "—"),
                "description": rep.get("description", ""),
                "garage": rep.get("garage", "Gara đối tác"),
                "invoice_no": rep.get("invoice_no", ""),
                "amount": safe_float(rep.get("amount")),
                "payment_status": rep.get("payment_status", "Công nợ (chưa trả)"),
                "notes": rep.get("notes", "Nhập từ Phần mềm"),
                "synced_from_web": True
            })

        doc_overrides = {o.get("plate_number"): o for o in self._get_db_sync_overrides("vehicle_document") if o.get("plate_number")}
        for item in wb_data["documents"]["road_permits"]:
            ov = doc_overrides.get(item["plate_number"])
            if ov:
                for k in ("trailer_number", "head_expiry", "trailer_expiry", "status", "notes"):
                    if k in ov and ov[k] not in (None, ""):
                        item[k] = ov[k]
                item["synced_from_web"] = True
        for item in wb_data["documents"]["road_stamps"]:
            ov = doc_overrides.get(item["plate_number"])
            if ov and ov.get("stamp_expiry"):
                item["stamp_expiry"] = ov["stamp_expiry"]
                item["synced_from_web"] = True
        for item in wb_data["documents"]["registrations"]:
            ov = doc_overrides.get(item["plate_number"])
            if ov:
                if ov.get("head_reg_expiry"):
                    item["head_reg_expiry"] = ov["head_reg_expiry"]
                if ov.get("trailer_reg_expiry"):
                    item["trailer_reg_expiry"] = ov["trailer_reg_expiry"]
                item["synced_from_web"] = True

        for tl in reversed(self._get_db_sync_overrides("tire_log")):
            wb_data["tires"]["logs"].insert(0, {
                "date": format_date_str(tl.get("date") or tl.get("record_date")),
                "plate_number": tl.get("plate_number", ""),
                "position": tl.get("position", "Vỏ xe"),
                "quantity": int(safe_float(tl.get("quantity"), 2)),
                "brand": tl.get("brand", "DRC / Bridgestone"),
                "supplier": tl.get("supplier", "Đại lý Vỏ"),
                "invoice_no": tl.get("invoice_no", ""),
                "amount": safe_float(tl.get("amount")),
                "payment_status": tl.get("payment_status", "Đã thanh toán"),
                "notes": tl.get("notes", "Nhập từ Phần mềm"),
                "synced_from_web": True
            })

        for bl in reversed(self._get_db_sync_overrides("tarp_log")):
            wb_data["tarps"]["logs"].insert(0, {
                "date": format_date_str(bl.get("date") or bl.get("record_date")),
                "plate_number": bl.get("plate_number", ""),
                "description": bl.get("description", "May/sửa bạt thùng"),
                "supplier": bl.get("supplier", "Phùng Lĩnh"),
                "invoice_no": bl.get("invoice_no", ""),
                "amount": safe_float(bl.get("amount")),
                "payment_status": bl.get("payment_status", "Công nợ (chưa trả)"),
                "notes": bl.get("notes", "Nhập từ Phần mềm"),
                "synced_from_web": True
            })

    def fetch_maintenance_sheet(self):
        """Giữ tương thích ngược cho các router gọi fetch_maintenance_sheet(), trả về đủ 26 xe"""
        wb_data = self.fetch_full_maintenance_and_fuel_workbook()
        oil_list = wb_data.get("maintenance", {}).get("oil_changes", [])
        if oil_list:
            return oil_list
        return []

    def fetch_vehicles_sheet(self):
        now = time.time()
        if self.cached_vehicles:
            ts, data = self.cached_vehicles
            if now - ts < 300:
                return data

        try:
            wb_data = self.fetch_full_maintenance_and_fuel_workbook()
            permits = {p["plate_number"]: p for p in wb_data.get("documents", {}).get("road_permits", [])}
            ben_vehicles = []
            thung_vehicles = []
            for idx, p in enumerate(FLEET_BEN_PLATES, 1):
                clean_p, fmt_p = normalize_plate(p)
                doc = permits.get(fmt_p, {})
                ben_vehicles.append({
                    "stt": idx,
                    "plate_number": fmt_p,
                    "trailer_number": doc.get("trailer_number", "—"),
                    "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p, "Tài xế công ty"),
                    "phone": "",
                    "driver_status": "Đang làm việc"
                })
            for idx, p in enumerate(FLEET_THUNG_PLATES, 1):
                clean_p, fmt_p = normalize_plate(p)
                doc = permits.get(fmt_p, {})
                thung_vehicles.append({
                    "stt": idx,
                    "plate_number": fmt_p,
                    "trailer_number": doc.get("trailer_number", "—"),
                    "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p, "Tài xế công ty"),
                    "phone": "",
                    "driver_status": "Đang làm việc"
                })
            res = {"ben": ben_vehicles, "thung": thung_vehicles}
            self.cached_vehicles = (now, res)
            return res
        except Exception as e:
            print(f"Error fetching vehicles sheet: {e}")
            return {"ben": [], "thung": []}


sheets_client = GoogleSheetsSyncService()
