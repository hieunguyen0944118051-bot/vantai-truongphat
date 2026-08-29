import urllib.request

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

pos = js.find('$("#divKmCo")')
if pos != -1:
    start = max(0, pos - 1500)
    end = min(len(js), pos + 1500)
    print(js[start:end])
