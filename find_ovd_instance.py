import urllib.request, re

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

instances = re.findall(r'([a-zA-Z0-9_\.]+\s*=\s*new\s+OnlineViewData\s*\([^\)]*\))', js)
print('Instances of OnlineViewData:')
for inst in instances:
    print(' ', inst)
