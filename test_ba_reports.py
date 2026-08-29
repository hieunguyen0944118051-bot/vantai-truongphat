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

# 2. Check various report pages & handler URLs
report_urls = [
    'https://gps.binhanh.vn/OnlineM.aspx',
    'https://gps.binhanh.vn/BaoCao/BaoCaoTongHop/BaoCaoTongHop.aspx',
    'https://gps.binhanh.vn/BaoCao/BaoCaoTongHopTheoXe/BaoCaoTongHopTheoXe.aspx',
    'https://gps.binhanh.vn/BaoCao/BaoCaoNhienLieu/BaoCaoNhienLieu.aspx',
    'https://gps.binhanh.vn/BaoCao/BaoCaoKM/BaoCaoKM.aspx'
]

for url in report_urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
        with opener.open(req) as resp:
            page_html = resp.read().decode('utf-8', errors='ignore')
            print(f'✅ Status OK: {url} ({len(page_html)} bytes)')
            # Search for plate numbers (63H, 63E, 63G, 63F...)
            plates = re.findall(r'63[A-Z0-9\.\-]+', page_html)
            if plates:
                print('   🚘 Found plates on page:', set(plates[:10]))
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code} for {url}')
    except Exception as e:
        print(f'Error for {url}: {e}')
