import urllib.request

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

pos = 0
while True:
    pos = js.find('this.listVehicle', pos)
    if pos == -1: break
    print('--- MATCH ---')
    print(js[pos-100:pos+250])
    pos += len('this.listVehicle')
