import urllib.request, urllib.parse, http.cookiejar, json, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login to gps.binhanh.vn
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

# 2. Call GetSSO
req_sso = urllib.request.Request(
    'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
    data=urllib.parse.urlencode({'method': 'GetSSO'}).encode('utf-8'),
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
)
try:
    resp_sso = opener.open(req_sso)
    sso_data = json.loads(resp_sso.read().decode('utf-8'))
    print('🔑 SSO Result:', sso_data)
    sso_token = sso_data.get('sso')
    
    # 3. Access V3 with SSO token
    v3_url = f'https://gps3.binhanh.vn/online?sso={sso_token}&sc=1'
    req_v3 = urllib.request.Request(v3_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
    resp_v3 = opener.open(req_v3)
    html_v3 = resp_v3.read().decode('utf-8', errors='ignore')
    print(f'✅ Truy cập thành công BA GPS V3! URL: {resp_v3.geturl()} ({len(html_v3)} bytes)')
except Exception as e:
    print('SSO Error:', e)
