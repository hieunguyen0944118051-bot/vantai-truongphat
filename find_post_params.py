import urllib.request, urllib.parse, http.cookiejar, json, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
req_get = urllib.request.Request('https://gps.binhanh.vn/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
html_get = opener.open(req_get).read().decode('utf-8', errors='ignore')

vs = re.search(r'id="__VIEWSTATE"\s+value="([^"]+)"', html_get).group(1)
vsg = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]+)"', html_get).group(1)
ev = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]+)"', html_get).group(1)

post_data = {
    '__LASTFOCUS': '', '__EVENTTARGET': '', '__EVENTARGUMENT': '',
    '__VIEWSTATE': vs, '__VIEWSTATEGENERATOR': vsg, '__EVENTVALIDATION': ev,
    'UserLogin1$txtLoginUserName': 'truongphat68',
    'UserLogin1$txtLoginPassword': 'bN8Xm2Wp6KzV',
    'UserLogin1$hdfPassword': '',
    'UserLogin1$chkRememberMe': 'on',
    'UserLogin1$btnLogin': 'Đăng nhập'
}
req_post = urllib.request.Request(
    'https://gps.binhanh.vn/',
    data=urllib.parse.urlencode(post_data).encode('utf-8'),
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded'}
)
opener.open(req_post)

# 2. Test VehicleHandler.ashx with POST methods
post_methods = [
    {'method': 'getVehicleByCompany'},
    {'method': 'getVehicles'},
    {'method': 'getVehicleInfo'},
    {'method': 'getVehicleStatus'},
    {'method': 'getVehicleList'},
    {'method': 'getVehicleExpired'},
    {'method': 'getVehicleGroupSpecial'}
]

for p in post_methods:
    try:
        req = urllib.request.Request(
            'https://gps.binhanh.vn/HttpHandlers/VehicleHandler.ashx',
            data=urllib.parse.urlencode(p).encode('utf-8'),
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with opener.open(req) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            print(f"🎯 VehicleHandler POST {p['method']} -> Length: {len(data)} bytes")
            if '63E' in data:
                print(f"   🚘 MATCH FOUND IN {p['method']}!")
    except Exception as e:
        print(f"Error {p['method']}: {e}")

# 3. Test OnlineHandler.ashx methods
online_methods = [
    {'method': 'getVehicleList4Hidden'},
    {'method': 'loadConfigMap'},
    {'method': 'getErrorList'},
    {'method': 'GetVehiclesOnline'},
    {'method': 'getVehicles'},
    {'method': 'getAllVehicleOnline'}
]

for p in online_methods:
    try:
        req = urllib.request.Request(
            'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
            data=urllib.parse.urlencode(p).encode('utf-8'),
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with opener.open(req) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            print(f"🎯 OnlineHandler POST {p['method']} -> Length: {len(data)} bytes")
            if '63E' in data or 'p_code' in data:
                print(f"   🚘 MATCH FOUND IN {p['method']}!")
    except Exception as e:
        print(f"Error {p['method']}: {e}")
