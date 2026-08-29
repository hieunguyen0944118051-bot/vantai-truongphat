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

# 2. Get SSO
req_sso = urllib.request.Request(
    'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
    data=urllib.parse.urlencode({'method': 'GetSSO'}).encode('utf-8'),
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
)
resp_sso = opener.open(req_sso)
sso = json.loads(resp_sso.read().decode('utf-8'))['sso']

# 3. Access V3
v3_url = f'https://gps3.binhanh.vn/online?sso={sso}&sc=1'
req_v3 = urllib.request.Request(v3_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
resp_v3 = opener.open(req_v3)
html_v3 = resp_v3.read().decode('utf-8', errors='ignore')

# Save V3 html
with open('/Users/alex/.gemini/antigravity/scratch/transport-management/v3_dump.html', 'w', encoding='utf-8') as f:
    f.write(html_v3)

print('V3 Cookies:')
for c in cj:
    print('  -', c.name, '=', c.value[:20] + '...')

# Find API URLs in V3 scripts
apis = re.findall(r'[\'"]([^\'"]*api[^\'"]*)[\'"]', html_v3)
print('🔗 V3 APIs in HTML:', set(apis))

# Find script files in V3
scripts = re.findall(r'<script[^>]+src=[\'"]([^\'"]+)[\'"]', html_v3)
print('📜 V3 Scripts:', scripts)
