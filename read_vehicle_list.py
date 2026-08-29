import urllib.request, urllib.parse, http.cookiejar, json, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req_get = urllib.request.Request('https://gps.binhanh.vn/', headers={'User-Agent': 'Mozilla/5.0'})
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
req_post = urllib.request.Request('https://gps.binhanh.vn/', data=urllib.parse.urlencode(post_data).encode('utf-8'))
opener.open(req_post)

req = urllib.request.Request(
    'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
    data=urllib.parse.urlencode({'method': 'getVehicleList4Hidden'}).encode('utf-8')
)
resp = opener.open(req)
content = resp.read().decode('utf-8')
print("getVehicleList4Hidden result:")
print(content[:600])

with open('/Users/alex/.gemini/antigravity/scratch/transport-management/vehicles_hidden.json', 'w', encoding='utf-8') as f:
    f.write(content)
