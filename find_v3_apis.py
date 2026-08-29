import urllib.request, re, json

url = 'https://gps3.binhanh.vn/main-E2PV26WP.js'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        js = resp.read().decode('utf-8', errors='ignore')
        print(f'V3 Main JS length: {len(js)}')
        
        # Find API domains
        domains = re.findall(r'https?://[a-zA-Z0-9\.\-]+(?:bagps|binhanh|bagroup)[a-zA-Z0-9\.\-:\/]*', js)
        print('🌐 API domains found:', set(domains[:20]))

        # Find endpoints related to online/vehicle/tracking/report
        endpoints = re.findall(r'[\'"](/api/v\d+/[^\'"]+|/api/[^\'"]+vehicle[^\'"]*|/api/[^\'"]+tracking[^\'"]*|/api/[^\'"]+online[^\'"]*|/api/[^\'"]+report[^\'"]*)[\'"]', js, re.I)
        print('🎯 Specific Telematics Endpoints:', set(endpoints[:25]))
except Exception as e:
    print('Error:', e)
