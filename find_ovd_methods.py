import urllib.request, re

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

methods = re.findall(r'OnlineViewData\.prototype\.([a-zA-Z0-9_]+)\s*=', js)
print('OnlineViewData methods:')
for m in methods:
    print(' -', m)
