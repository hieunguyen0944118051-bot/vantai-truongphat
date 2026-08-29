import urllib.request, re

url = 'https://gps3.binhanh.vn/main-E2PV26WP.js'
with urllib.request.urlopen(url) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

kong_matches = re.findall(r'https://kong\.binhanh\.vn/[^\'\"`\s\)\}\;\,]+', js)
print('🎯 Kong API Gateway endpoints in V3:')
for m in sorted(set(kong_matches)):
    print('  -', m)
