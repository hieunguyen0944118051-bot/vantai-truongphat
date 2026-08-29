import re

with open('/Users/alex/.gemini/antigravity/scratch/transport-management/get_vehicles_gps.py') as f:
    pass

import urllib.request, urllib.parse, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
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

# Save to file to inspect
with open('/Users/alex/.gemini/antigravity/scratch/transport-management/onlinem_dump.html', 'w', encoding='utf-8') as f:
    f.write(html_online)

# Look for GpsServices methods
methods = re.findall(r'GpsServices\.(\w+)', html_online)
print('🎯 GpsServices methods called:', set(methods))

# Look for $.ajax or $.post calls
ajax_calls = re.findall(r'url\s*:\s*[\'"]([^\'"]+)[\'"]', html_online)
print('🌐 Ajax URLs in HTML:', set(ajax_calls[:15]))
