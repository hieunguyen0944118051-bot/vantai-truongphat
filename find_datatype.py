import urllib.request

with open('/Users/alex/.gemini/antigravity/scratch/transport-management/find_listvehicle.py') as f:
    pass

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

pos = js.find('onlineViewDataType')
print(js[pos-200:pos+1500])
