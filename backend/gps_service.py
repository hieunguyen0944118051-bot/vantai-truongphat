"""Đọc vị trí / km / thẻ lái xe từ GPS Bình Anh.

- Tài khoản lấy từ biến môi trường BA_USERNAME / BA_PASSWORD (không ghi trong code).
- Không tính "định mức dầu" hay "nghi hút dầu" — GPS không đo dầu; các số đó trước đây là bịa.
- Mỗi xe mang giờ GPS GỐC (gps_time) và cờ is_stale khi tín hiệu cũ hơn STALE_MINUTES.
"""
import http.cookiejar
import json
import os
import re
import threading
import urllib.parse
import urllib.request
from datetime import datetime

from fleet import DRIVER_BY_CLEAN_PLATE, clean_plate

# Giữ tên cũ để code khác không vỡ; nguồn thật là fleet.py
OFFICIAL_DRIVERS_BY_CLEAN_PLATE = DRIVER_BY_CLEAN_PLATE

BA_URL = "https://gps.binhanh.vn/"
STALE_MINUTES = 30
REFRESH_SECONDS = 15
CACHE_PATH = os.path.join(os.path.dirname(__file__), "live_ba_fleet_cache.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def _parse_ba_time(s: str):
    """'2026-09-02T18:09:14' -> datetime; lỗi -> None."""
    try:
        return datetime.fromisoformat((s or "")[:19])
    except ValueError:
        return None


class GpsClient:
    def __init__(self):
        self.username = os.environ.get("BA_USERNAME", "").strip()
        self.password = os.environ.get("BA_PASSWORD", "").strip()
        self.configured = bool(self.username and self.password)
        if not self.configured:
            print("[gps] Chưa đặt BA_USERNAME / BA_PASSWORD — chỉ hiển thị dữ liệu GPS lưu tạm.")
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.last_login_time = None
        self.last_fetch_time = None          # lần lấy GPS thành công gần nhất
        self.last_error = None
        self._is_updating = False
        self._lock = threading.Lock()
        self._raw_vehicles = self._load_cache()

    # ---------- dữ liệu ----------
    def _load_cache(self):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return (json.load(f) or {}).get("data") or []
        except (OSError, ValueError):
            return []

    def _parse_ba_vehicles(self, raw_vehicles, now=None):
        now = now or datetime.now()
        processed = []
        for v in raw_vehicles:
            pri_code = v.get("pri_code") or v.get("plate") or ""
            if len(pri_code) == 8 and "-" not in pri_code:
                plate = f"{pri_code[:3]}-{pri_code[3:6]}.{pri_code[6:]}"
            else:
                plate = pri_code.replace("_C", "")
            clean_p = clean_plate(plate)

            gps_dt = _parse_ba_time(v.get("g_time"))
            age_min = int((now - gps_dt).total_seconds() // 60) if gps_dt else None
            is_today = bool(gps_dt) and gps_dt.date() == now.date()
            is_stale = age_min is None or age_min > STALE_MINUTES

            if not is_today:
                speed, daily_km = 0, 0.0
                status_type, status_text = "stopped", "Dừng bãi (không có tín hiệu hôm nay)"
            else:
                speed = int(v.get("v_gps", 0) or 0)
                state = v.get("state", 0)
                daily_km = round(float(v.get("t_km") or 0.0), 1)
                if speed > 0:
                    status_type, status_text = "running", f"Đang chạy ({speed} km/h)"
                elif state in (32, 2080):
                    status_type, status_text = "idling", "Dừng nổ máy"
                else:
                    status_type, status_text = "stopped", "Dừng tắt máy"
            if is_stale and is_today:
                speed = 0  # tín hiệu cũ: không coi là đang chạy

            bgt = v.get("bgt") or {}
            bgt_name = (bgt.get("name") or "").strip().upper()
            is_logged_out = bgt_name in ("LAI XE DANG XUAT", "", "NONE", "CHƯA NHẬP") or "DANG XUAT" in bgt_name
            is_card_swiped = (not is_logged_out) and is_today
            card_violation = None
            if is_today and is_logged_out and speed > 0:
                card_violation = "running_no_card"
            elif is_today and is_logged_out and daily_km > 0:
                card_violation = "daily_no_card"

            processed.append({
                "plate_number": plate,
                "plate_code": v.get("plate") or pri_code,
                "driver_name": DRIVER_BY_CLEAN_PLATE.get(clean_p, "Chưa phân công"),
                "speed": speed,
                "status_text": status_text,
                "status_type": status_type,
                "daily_km": daily_km,
                "address": v.get("adds") or "",
                "latitude": v.get("lat"),
                "longitude": v.get("lng"),
                "gps_time": gps_dt.strftime("%H:%M %d/%m/%Y") if gps_dt else None,
                "gps_age_minutes": age_min,
                "is_stale": is_stale,
                # giữ tên cũ cho giao diện
                "update_time": gps_dt.strftime("%H:%M:%S %d-%m-%Y") if gps_dt else "—",
                "is_card_swiped": is_card_swiped,
                "card_driver_name": bgt.get("name") if is_card_swiped else "Chưa quẹt thẻ",
                "card_violation": card_violation,
            })
        return processed

    def fetch_live_fleet(self):
        """Trả danh sách xe ngay (không chờ mạng); làm mới nền nếu dữ liệu cũ hơn REFRESH_SECONDS."""
        if self.configured and not self._is_updating and (
                self.last_fetch_time is None
                or (datetime.now() - self.last_fetch_time).total_seconds() > REFRESH_SECONDS):
            threading.Thread(target=self._background_refresh, daemon=True).start()
        return self._parse_ba_vehicles(self._raw_vehicles)

    def status(self):
        fleet = self._parse_ba_vehicles(self._raw_vehicles)
        times = [_parse_ba_time(v.get("g_time")) for v in self._raw_vehicles]
        times = [t for t in times if t]
        return {
            "configured": self.configured,
            "last_fetch": self.last_fetch_time.strftime("%H:%M:%S %d/%m/%Y") if self.last_fetch_time else None,
            "newest_gps_time": max(times).strftime("%H:%M %d/%m/%Y") if times else None,
            "total": len(fleet),
            "stale_count": sum(1 for v in fleet if v["is_stale"]),
            "last_error": self.last_error,
        }

    # ---------- kết nối Bình Anh ----------
    def _login(self):
        html_get = self.opener.open(urllib.request.Request(BA_URL, headers={"User-Agent": UA}), timeout=10) \
            .read().decode("utf-8", errors="ignore")

        def field(name):
            m = re.search(rf'id="{name}"\s+value="([^"]*)"', html_get)
            return m.group(1) if m else ""

        post_data = {
            "__LASTFOCUS": "", "__EVENTTARGET": "", "__EVENTARGUMENT": "",
            "__VIEWSTATE": field("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": field("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": field("__EVENTVALIDATION"),
            "UserLogin1$txtLoginUserName": self.username,
            "UserLogin1$txtLoginPassword": self.password,
            "UserLogin1$hdfPassword": "",
            "UserLogin1$chkRememberMe": "on",
            "UserLogin1$btnLogin": "Đăng nhập",
        }
        req = urllib.request.Request(
            BA_URL, data=urllib.parse.urlencode(post_data).encode("utf-8"),
            headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", "Referer": BA_URL})
        self.opener.open(req, timeout=10)
        self.last_login_time = datetime.now()

    def _post(self, handler, data):
        req = urllib.request.Request(
            f"{BA_URL}HttpHandlers/{handler}", data=urllib.parse.urlencode(data).encode("utf-8"),
            headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        return json.loads(self.opener.open(req, timeout=8).read().decode("utf-8"))

    def _ensure_login(self):
        if self.last_login_time is None or (datetime.now() - self.last_login_time).total_seconds() > 1800:
            self._login()

    def _background_refresh(self):
        with self._lock:
            if self._is_updating:
                return
            self._is_updating = True
        try:
            self._ensure_login()
            raw = self._post("OnlineHandler.ashx", {"method": "initListVehicle"})
            if raw.get("eos") or str(raw.get("success")).lower() == "false":
                self._login()
                raw = self._post("OnlineHandler.ashx", {"method": "initListVehicle"})
            vehicles = raw.get("data") or []
            if vehicles:
                self._raw_vehicles = vehicles
                self.last_fetch_time = datetime.now()
                self.last_error = None
                try:
                    with open(CACHE_PATH, "w", encoding="utf-8") as f:
                        json.dump(raw, f, ensure_ascii=False)
                except OSError:
                    pass
            else:
                self.last_error = "Bình Anh trả về danh sách rỗng"
        except Exception as e:  # mạng / đăng nhập lỗi: ghi lại để hiện trên app, không bịa số
            self.last_error = f"{type(e).__name__}: {e}"[:200]
            print(f"[gps] Lỗi lấy dữ liệu Bình Anh: {self.last_error}")
        finally:
            self._is_updating = False

    def fetch_vehicle_fuel_detail(self, plate_code: str, lng: float, lat: float):
        """Mức nhiên liệu do thiết bị Bình Anh báo (nếu xe có cảm biến dầu)."""
        if not self.configured:
            raise RuntimeError("Chưa cấu hình tài khoản Bình Anh (BA_USERNAME / BA_PASSWORD)")
        self._ensure_login()
        info = self._post("VehicleHandler.ashx",
                          {"method": "getInfoVehicle", "plate": plate_code, "lng": str(lng), "lat": str(lat)})
        raw_html = info.get("data", "")
        liters = percent = None
        if "Nhiên liệu:" in raw_html:
            try:
                part = raw_html.split("Nhiên liệu:")[1].split("<")[0].strip()
                if "(" in part and "%" in part:
                    liters = float(part.split("(")[0].replace("Lít", "").strip())
                    percent = float(part.split("(")[1].split("%")[0].strip())
            except (IndexError, ValueError):
                pass
        return {"liters": liters, "percent": percent, "raw_info": raw_html}


gps_client = GpsClient()
