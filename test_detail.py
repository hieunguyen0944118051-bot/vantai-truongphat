import urllib.request, urllib.parse, http.cookiejar, json, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
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

# Test detail for vehicle 63E01118_C
url = 'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx?' + urllib.parse.urlencode({
    'method': 'detail',
    'VehiclePlate': '63E01118_C',
    'lng': 106.5796,
    'lat': 10.6869
})

req_detail = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = opener.open(req_detail)
res = resp.read().decode('utf-8')
print("✅ Vehicle detail response:")
print(res)

with open('/Users/alex/.gemini/antigravity/scratch/transport-management/vehicle_detail_sample.json', 'w', encoding='utf-8') as f:
    f.write(res)
