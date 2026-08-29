import urllib.request, urllib.parse, http.cookiejar, json, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
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

# 2. Call initListVehicle
req_init = urllib.request.Request(
    'https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx',
    data=urllib.parse.urlencode({'method': 'initListVehicle'}).encode('utf-8'),
    headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
)
resp_init = opener.open(req_init)
res_text = resp_init.read().decode('utf-8')
print(f"✅ initListVehicle returned: Length {len(res_text)} bytes")
print("Snippet:", res_text[:300])

with open('/Users/alex/.gemini/antigravity/scratch/transport-management/init_list_vehicle_result.json', 'w', encoding='utf-8') as f:
    f.write(res_text)

# Also test synVehicle
req_syn = urllib.request.Request('https://gps.binhanh.vn/HttpHandlers/OnlineHandler.ashx?method=synVehicle', headers={'User-Agent': 'Mozilla/5.0'})
resp_syn = opener.open(req_syn)
syn_text = resp_syn.read().decode('utf-8')
print(f"✅ synVehicle returned: Length {len(syn_text)} bytes")
print("Snippet:", syn_text[:300])
with open('/Users/alex/.gemini/antigravity/scratch/transport-management/syn_vehicle_result.json', 'w', encoding='utf-8') as f:
    f.write(syn_text)
