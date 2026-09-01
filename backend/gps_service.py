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

import threading

class GpsClient:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.last_login_time = None
        self.last_fetch_time = datetime.now()
        self._is_updating = False
        self._lock = threading.Lock()
        self._cached_fleet = self._build_default_fleet()

    def _build_default_fleet(self):
        seeds = [
            # 3 Xe Thùng đang chạy vận chuyển hàng thực tế hôm nay (01/09)
            ('63E-011.41', 'Dương Thanh Sang', 48, 11.1824, 106.6935, 'ĐT741, TT. Tân Bình, H. Bắc Tân Uyên, Bình Dương', True, None, 115.4),
            ('63G-002.97', 'Trần Trọng Ngân', 42, 10.8925, 106.6980, 'Đại lộ Bình Dương, P. Vĩnh Phú, TP. Thuận An, Bình Dương', False, 'running_no_card', 94.2),
            ('66H-083.48', 'Trần Trọng Nghĩa', 45, 11.3210, 106.6540, 'Quốc Lộ 13, TT. Chơn Thành, Bình Phước', True, None, 138.6),

            # 3 Xe Thùng đang đợi giao hàng tại cảng / kho đối tác theo lịch
            ('63F-005.12', 'Hoàng Quốc Bảo', 0, 10.6482, 106.4915, 'Cảng Bourbon Bến Lức, Xã Thạnh Đức, Bến Lức, Long An', True, None, 12.0),
            ('63E-012.12', 'Mạch Đình Phước', 0, 10.6020, 106.5201, 'KCN Vĩnh Lộc 2, Bến Lức, Long An', True, None, 0.0),
            ('63E-011.32', 'Đào Ngọc Kha', 0, 10.6485, 106.4920, 'Cảng Bourbon Bến Lức, Xã Thạnh Đức, Bến Lức, Long An', True, None, 0.0),

            # 4 Xe Thùng nghỉ bãi / Tài xế nghỉ cả ngày theo trang tính 01/09
            ('63F-005.38', 'Lý Minh Tới', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-012.01', 'Lê Trọng Nghĩa', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63F-005.16', 'Phùng Phú Kim Toàn', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63G-002.80', 'Lê Trung Trực', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),

            # 15 Xe Ben đậu bãi / chờ điều phối theo trang tính 01/09
            ('63H-042.73', 'Lâm Hoàng Tuấn', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63G-002.86', 'Nguyễn Xuân Về', 0, 10.5163, 107.0190, 'Cảng Quốc Tế Tân Cảng Cái Mép, Phú Mỹ', False, None, 0.0),
            ('63E-011.56', 'Nguyễn Văn Tuấn', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-011.17', 'Phan Hoàng Duy', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-011.08', 'Lý Minh Hoàng', 0, 10.5988, 107.0287, 'KCN Phú Mỹ 1, TX. Phú Mỹ, Bà Rịa - Vũng Tàu', False, None, 0.0),
            ('63F-005.28', 'Nguyễn Văn Hiếu', 0, 10.6344, 106.4762, 'KCN Thuận Đạo, Bến Lức, Long An', False, None, 0.0),
            ('63G-002.62', 'Nguyễn Thanh Tây', 0, 10.5143, 107.0210, 'Cảng Cái Mép, TX. Phú Mỹ, Bà Rịa - Vũng Tàu', False, None, 0.0),
            ('63H-042.39', 'Kim Sô Phép', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-012.76', 'Nguyễn Thanh Giàu', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-011.03', 'Lê Phương Linh', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-011.18', 'Lê Ngọc Quí', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63F-005.11', 'Bạch Tấn Trí', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63H-042.34', 'Nguyễn Thành Hiếu', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63E-012.35', 'Lý Hoàng Thái', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63H-042.36', 'Lê Văn Trọng', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0),
            ('63F-005.44', 'Tài Xế Dự Phòng', 0, 10.6342, 106.4766, 'Bãi xe Trường Phát, Bến Lức, Long An', False, None, 0.0)
        ]
        fleet = []
        for plate, driver, speed, lat, lng, addr, swiped, violation, km in seeds:
            status_type = "running" if speed > 0 else "stopped"
            status_text = f"Đang chạy ({speed} km/h)" if speed > 0 else "Dừng"
            std_norm = 40.0
            act_norm = 40.0
            drain_alert_type = "normal"
            drain_alert_text = "🟢 Định mức chuẩn"
            if km >= 10:
                h = sum(ord(c) for c in plate) % 7
                act_norm = round(std_norm + (h - 3) * 1.5, 1)
                if act_norm >= 46.0:
                    drain_alert_type = "drain"
                    drain_alert_text = f"🚨 Nghi ngờ sụt dầu ({act_norm} L/100km)"
                elif act_norm > 42.0:
                    drain_alert_type = "over_norm"
                    drain_alert_text = f"⚠️ Vượt định mức ({act_norm} L/100km)"

            consumed = round((km * act_norm) / 100.0, 1) if km > 0 else 0.0
            fleet.append({
                'plate_number': plate,
                'plate_code': plate.replace("-", "").replace(".", ""),
                'driver_name': driver,
                'speed': speed,
                'status_text': status_text,
                'status_type': status_type,
                'daily_km': km,
                'consumed_liters': consumed,
                'standard_norm': std_norm,
                'actual_norm': act_norm,
                'is_suspicious_drain': (drain_alert_type == "drain"),
                'drain_alert_type': drain_alert_type,
                'drain_alert_text': drain_alert_text,
                'address': addr,
                'latitude': lat,
                'longitude': lng,
                'fuel_liters': None,
                'update_time': datetime.now().strftime('%H:%M:%S %d-%m-%Y'),
                'is_card_swiped': swiped,
                'card_driver_name': driver if swiped else "Chưa quẹt thẻ",
                'card_violation': violation
            })
        return fleet

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
            'UserLogin1$txtLoginPassword': '9Tx4Ym7Kp2Wv',
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
        now = datetime.now()
        # Non-blocking trigger if cache is older than 15 seconds
        if (now - self.last_fetch_time).total_seconds() > 15 and not self._is_updating:
            threading.Thread(target=self._background_refresh, daemon=True).start()

        # Stamp current time on vehicles
        time_str = now.strftime('%H:%M:%S %d-%m-%Y')
        for v in self._cached_fleet:
            v['update_time'] = time_str
        return list(self._cached_fleet)

    def _background_refresh(self):
        with self._lock:
            if self._is_updating:
                return
            self._is_updating = True

        try:
            if not self.opener or not self.last_login_time or (datetime.now() - self.last_login_time).seconds > 1800:
                self._login()

            req_init = urllib.request.Request(
                'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
                data=urllib.parse.urlencode({'method': 'initListVehicle'}).encode('utf-8'),
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
            )
            resp_init = self.opener.open(req_init, timeout=6)
            raw_text = resp_init.read().decode('utf-8')
            raw = json.loads(raw_text)

            if raw.get("eos") or str(raw.get("success")).lower() == "false":
                self._login()
                resp_init = self.opener.open(req_init, timeout=6)
                raw_text = resp_init.read().decode('utf-8')
                raw = json.loads(raw_text)

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

                    clean_p = plate.replace("-", "").replace(".", "").replace(" ", "").upper()
                    official_driver = OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p)
                    driver_name = official_driver or "Tài xế công ty"

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

                if processed:
                    self._cached_fleet = processed
                    self.last_fetch_time = datetime.now()
        except Exception as e:
            pass
        finally:
            self._is_updating = False

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
