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

# 2. Test VehicleHandler.ashx methods
methods = [
    'getVehicleGroupSpecial',
    'getAllVehicles',
    'getListVehicles',
    'getVehicles',
    'getVehicleOnline',
    'getListVehicleOnline',
    'getVehicleStatus',
    'getVehicleInfo',
    'getVehiclesByGroup'
]

for m in methods:
    url = f'https://gps.binhanh.vn/HttpHandlers/VehicleHandler.ashx?method={m}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
        with opener.open(req) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            print(f'🎯 Method [{m}] -> Status 200, Length: {len(data)} bytes')
            if len(data) > 0:
                print('   Snippet:', data[:200])
                if '63' in data:
                    print('   🚘 FOUND VEHICLES!')
                    with open(f'/Users/alex/.gemini/antigravity/scratch/transport-management/vh_{m}.json', 'w', encoding='utf-8') as f:
                        f.write(data)
    except urllib.error.HTTPError as e:
        print(f'Method [{m}] -> HTTP {e.code}')
    except Exception as e:
        print(f'Method [{m}] -> {e}')
