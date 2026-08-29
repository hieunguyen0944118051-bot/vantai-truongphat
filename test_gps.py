import urllib.request, urllib.parse, re, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Get initial page
req_get = urllib.request.Request('https://gps.binhanh.vn/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
resp_get = opener.open(req_get)
html_get = resp_get.read().decode('utf-8', errors='ignore')

# Extract hidden values
vs_m = re.search(r'id="__VIEWSTATE"\s+value="([^"]+)"', html_get)
vsg_m = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]+)"', html_get)
ev_m = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]+)"', html_get)

vs = vs_m.group(1) if vs_m else ""
vsg = vsg_m.group(1) if vsg_m else ""
ev = ev_m.group(1) if ev_m else ""

# 2. Post login
post_data = {
    '__LASTFOCUS': '',
    '__EVENTTARGET': '',
    '__EVENTARGUMENT': '',
    '__VIEWSTATE': vs,
    '__VIEWSTATEGENERATOR': vsg,
    '__EVENTVALIDATION': ev,
    'UserLogin1$txtLoginUserName': 'truongphat68',
    'UserLogin1$txtLoginPassword': 'bN8Xm2Wp6KzV',
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

resp_post = opener.open(req_post)
final_url = resp_post.geturl()
html_post = resp_post.read().decode('utf-8', errors='ignore')

print('🔗 Final URL after login:', final_url)
print('🍪 Cookies received:')
for cookie in cj:
    print('  -', cookie.name, '=', cookie.value[:30] + '...')

error_msg = re.findall(r'alert\(["\']([^"\']+)["\']\)', html_post)
if error_msg:
    print('⚠️ Thông báo trang web:', error_msg)

if 'txtLoginUserName' not in html_post:
    print('🎉 ĐĂNG NHẬP THÀNH CÔNG VÀO HỆ THỐNG BA GPS!')
else:
    print('Kiểm tra nội dung trang trả về (500 ký tự đầu):')
    print(html_post[:500])
