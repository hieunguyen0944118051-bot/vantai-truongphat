import urllib.request, urllib.parse, re, http.cookiejar, json

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
resp_post = opener.open(req_post)
html_online = resp_post.read().decode('utf-8', errors='ignore')
print(f'✅ Đã vào trang OnlineM.aspx ({len(html_online)} bytes)')

# Check scripts & PageMethods in OnlineM.aspx
ajax_endpoints = re.findall(r'[\'"]([^\'"]+\.asmx/[^\'"]+|[^\'"]+\.aspx/[^\'"]+|/api/[^\'"]+)[\'"]', html_online)
print('🔗 AJAX endpoints found:', set(ajax_endpoints[:15]))

# Search for vehicle data in page
json_data_matches = re.findall(r'var\s+(\w+)\s*=\s*(\[\{.*?\}\]|\{.*?\});', html_online, re.DOTALL)
for var_name, var_val in json_data_matches[:5]:
    print(f'📦 Found JS variable: {var_name} (Length: {len(var_val)})')

# Let us check standard BA GPS Ajax methods
test_methods = [
    ('https://gps.binhanh.vn/OnlineM.aspx/GetVehicleOnline', {}),
    ('https://gps.binhanh.vn/OnlineM.aspx/GetListVehicle', {}),
    ('https://gps.binhanh.vn/OnlineM.aspx/GetVehicles', {}),
    ('https://gps.binhanh.vn/Services/OnlineService.asmx/GetVehicleOnline', {}),
    ('https://gps.binhanh.vn/Services/VehicleService.asmx/GetListVehicle', {})
]

for method_url, payload in test_methods:
    try:
        req_m = urllib.request.Request(
            method_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Content-Type': 'application/json; charset=utf-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://gps.binhanh.vn/OnlineM.aspx'
            }
        )
        with opener.open(req_m, timeout=5) as r:
            res = r.read().decode('utf-8', errors='ignore')
            print(f'🎯 Thành công gọi {method_url}: {res[:250]}')
    except Exception as e:
        print(f'Thử {method_url} -> {e}')
