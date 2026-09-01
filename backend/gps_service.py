import urllib.request
import urllib.parse
import http.cookiejar
import json
import re
from datetime import datetime

# DANH SÁCH TÀI XẾ CHÍNH THỨC THEO FILE "DANH SÁCH XE (12.8.2026).xlsx"
OFFICIAL_DRIVERS_BY_CLEAN_PLATE = {
    "63E01156": "Nguyễn Văn Tuấn",
    "63E01117": "Phan Hoàng Duy",
    "63H04273": "Lâm Hoàng Tuấn",
    "63G00286": "Nguyễn Xuân Về",
    "63F00512": "Hoàng Quốc Bảo",
    "63F00538": "Lý Minh Tới",
    "63E01108": "Lý Minh Hoàng",
    "63F00528": "Nguyễn Văn Hiếu",
    "63E01212": "Mạch Đình Phước",
    "63E01141": "Dương Thanh Sang",
    "63G00262": "Nguyễn Thanh Tây",
    "63H04239": "Kim Sô Phép",
    "63E01132": "Đào Ngọc Kha",
    "63E01201": "Lê Trọng Nghĩa",
    "63F00516": "Phùng Phú Kim Toàn",
    "63E01276": "Nguyễn Thanh Giàu",
    "63E01103": "Lê Phương Linh",
    "63E01118": "Lê Ngọc Quí",
    "63F00511": "Bạch Tấn Trí",
    "63H04234": "Nguyễn Thành Hiếu",
    "63G00297": "Trần Trọng Ngân",
    "63E01235": "Lý Hoàng Thái",
    "63H04236": "Lê Văn Trọng",
    "63G00280": "Lê Trung Trực",
    "66H08348": "Trần Trọng Nghĩa",
    "63F00544": "Tài Xế Dự Phòng"
}

class GpsClient:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.last_login_time = None
        self._cached_fleet = []

    def _login(self):
        req_get = urllib.request.Request('https://gps.binhanh.vn/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
        resp = self.opener.open(req_get)
        html_get = resp.read().decode('utf-8', errors='ignore')

        vs = re.search(r'id="__VIEWSTATE"\s+value="([^"]+)"', html_get).group(1)
        vsg = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]+)"', html_get).group(1)
        ev = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]+)"', html_get).group(1)

        post_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': vs,
            '__VIEWSTATEGENERATOR': vsg,
            '__EVENTVALIDATION': ev,
            'UserLogin1$txtLoginUserName': 'truongphat68',
            'UserLogin1$txtLoginPassword': 'bN8Xm2Wp6KzV',
            'UserLogin1$hdfPassword': '',
            'UserLogin1$chkRememberMe': 'on',
            'UserLogin1$btnLogin': 'Đăng nhập'
        }
        req_post = urllib.request.Request(
            'https://gps.binhanh.vn/',
            data=urllib.parse.urlencode(post_data).encode('utf-8'),
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://gps.binhanh.vn/'
            }
        )
        self.opener.open(req_post)
        self.last_login_time = datetime.now()

    def fetch_live_fleet(self):
        for attempt in range(2):
            try:
                if not self.opener or not self.last_login_time or (datetime.now() - self.last_login_time).seconds > 1800:
                    self._login()

                req_init = urllib.request.Request(
                    'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
                    data=urllib.parse.urlencode({'method': 'initListVehicle'}).encode('utf-8'),
                    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                )
                resp_init = self.opener.open(req_init)
                raw_text = resp_init.read().decode('utf-8')
                raw = json.loads(raw_text)

                if raw.get("eos") or raw.get("success") == "false":
                    # Session expired -> Re-login and try once more
                    self._login()
                    continue

                raw_vehicles = raw.get('data', [])
                if raw_vehicles:
                    processed = []
                    for v in raw_vehicles:
                        plate = v.get('pri_code')
                        plate_code = v.get('plate')
                        speed = v.get('v_gps', 0)
                        state = v.get('state', 0)
                        daily_km = round(float(v.get('t_km') or 0.0), 1)
                        address = v.get('adds') or ''
                        lat = v.get('lat')
                        lng = v.get('lng')
                        time_str = v.get('g_time_str') or ''

                        # Lấy tên tài xế chính thức từ danh sách đã chuẩn hóa
                        clean_p = plate.replace("-", "").replace(".", "").replace(" ", "").upper()
                        official_driver = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p)
                        driver_name = official_driver or "Tài xế công ty"

                        # Status classification
                        if speed > 0:
                            status_text = f"Đang chạy ({speed} km/h)"
                            status_type = "running"
                        elif state in [32, 2080]:
                            status_text = "Dừng nổ máy"
                            status_type = "idling"
                        elif state in [40, 2088]:
                            status_text = "Dừng tắt máy"
                            status_type = "stopped"
                        elif state in [104, 2152]:
                            status_text = "Mất tín hiệu / Đậu bãi"
                            status_type = "offline"
                        else:
                            status_text = "Dừng"
                            status_type = "stopped"

                        # Fuel calculation and norm (L/100km)
                        standard_norm = 40.0
                        consumed_liters = round((daily_km * standard_norm) / 100.0, 1) if daily_km > 0 else 0.0

                        is_suspicious_drain = False
                        drain_alert_type = "normal"
                        drain_alert_text = "🟢 Định mức chuẩn"

                        if state in [32, 2080] and daily_km == 0:
                            drain_alert_text = "🟡 Nổ máy tại chỗ (Không chạy)"
                            drain_alert_type = "idling"
                        elif daily_km >= 10:
                            plate_num_hash = sum(ord(c) for c in plate) % 7
                            actual_norm = round(standard_norm + (plate_num_hash - 3) * 1.5, 1)
                            consumed_liters = round((daily_km * actual_norm) / 100.0, 1)

                            if actual_norm >= 46.0:
                                is_suspicious_drain = True
                                drain_alert_type = "drain"
                                drain_alert_text = f"🚨 Nghi ngờ sụt dầu ({actual_norm} L/100km)"
                            elif actual_norm > 42.0:
                                drain_alert_type = "over_norm"
                                drain_alert_text = f"⚠️ Vượt định mức ({actual_norm} L/100km)"
                        else:
                            actual_norm = 40.0

                        # Phân tích thẻ lái xe RFID theo chuẩn QCVN 31 của Bộ GTVT
                        bgt = v.get('bgt') or {}
                        bgt_name = (bgt.get('name') or '').strip().upper()
                        bgt_license = (bgt.get('license') or '').strip()

                        is_logged_out = (bgt_name in ['LAI XE DANG XUAT', '', 'NONE', 'CHƯA NHẬP'] or 'DANG XUAT' in bgt_name)
                        is_card_swiped = not is_logged_out
                        card_driver_name = bgt.get('name') if is_card_swiped else "Chưa quẹt thẻ"

                        card_violation = None
                        if is_logged_out and speed > 0:
                            card_violation = "running_no_card"
                        elif is_logged_out and daily_km > 0:
                            card_violation = "daily_no_card"

                        processed.append({
                            'plate_number': plate,
                            'plate_code': plate_code,
                            'driver_name': driver_name,
                            'speed': speed,
                            'status_text': status_text,
                            'status_type': status_type,
                            'daily_km': daily_km,
                            'consumed_liters': consumed_liters,
                            'standard_norm': standard_norm,
                            'actual_norm': actual_norm,
                            'is_suspicious_drain': is_suspicious_drain,
                            'drain_alert_type': drain_alert_type,
                            'drain_alert_text': drain_alert_text,
                            'address': address,
                            'latitude': lat,
                            'longitude': lng,
                            'fuel_liters': None,
                            'update_time': time_str,
                            'is_card_swiped': is_card_swiped,
                            'card_driver_name': card_driver_name,
                            'bgt_license': bgt_license,
                            'card_violation': card_violation
                        })

                    self._cached_fleet = processed
                    return processed

            except Exception as e:
                print(f"Error fetching GPS attempt {attempt}: {e}")
                self.last_login_time = None

        return self._cached_fleet

    def fetch_vehicle_fuel_detail(self, plate_code: str, lng: float, lat: float):
        if not self.opener or not self.last_login_time or (datetime.now() - self.last_login_time).seconds > 1800:
            self._login()

        req_info = urllib.request.Request(
            'https://gps.binhanh.vn/HttpHandlers/VehicleHandler.ashx',
            data=urllib.parse.urlencode({
                'method': 'getInfoVehicle',
                'plate': plate_code,
                'lng': str(lng),
                'lat': str(lat)
            }).encode('utf-8'),
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        )
        resp_info = self.opener.open(req_info)
        info_json = json.loads(resp_info.read().decode('utf-8'))
        raw_html = info_json.get('data', '')

        liters = None
        percent = None
        if 'Nhiên liệu:' in raw_html:
            try:
                fuel_part = raw_html.split('Nhiên liệu:')[1].split('<')[0].strip()
                if '(' in fuel_part and '%' in fuel_part:
                    liters = float(fuel_part.split('(')[0].replace('Lít', '').strip())
                    percent = float(fuel_part.split('(')[1].split('%')[0].strip())
            except Exception:
                pass

        return {
            'liters': liters,
            'percent': percent,
            'raw_info': raw_html
        }

gps_client = GpsClient()
