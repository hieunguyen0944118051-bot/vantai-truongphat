import urllib.request, re

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    js = resp.read().decode('utf-8', errors='ignore')

instances = re.findall(r'(var\s+([a-zA-Z0-9_]+)\s*=\s*new\s+OnlineVehicle|[a-zA-Z0-9_]+\s*=\s*new\s+OnlineVehicle)', js)
print('Instances of OnlineVehicle found:')
for inst in instances:
    print(' ', inst)

# Also find where vehicles are stored inside OnlineVehicle
props = re.findall(r'this\.([a-zA-Z0-9_]+)\s*=\s*new\s+Dictionary|this\.([a-zA-Z0-9_]+)\s*=\s*\[\]|this\.([a-zA-Z0-9_]+)\s*=\s*\{\}', js)
print('Collections in script:')
for p in props[:20]:
    print(' ', [x for x in p if x])
