import urllib.request

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

pos = js.find('lblAccKm')
if pos != -1:
    print('Found lblAccKm in bundle!')
    print(js[pos-300:pos+300])
else:
    print('Not found')
