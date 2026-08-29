import urllib.request, re

url = 'https://gps.binhanh.vn/Scripts/mapStraction/gps/online/online.vehicle.ext.newbrowser.js?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        js = resp.read().decode('utf-8', errors='ignore')
        print(f"File length: {len(js)}")
        
        # Search for method names in OnlineHandler
        methods = re.findall(r'OnlineHandler\.ashx[^\}]*method[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]', js)
        print("Methods in OnlineHandler from online.vehicle.ext.newbrowser.js:")
        for m in set(methods):
            print("  -", m)

        # Look for method: '...' anywhere in js
        all_methods = re.findall(r'method[\'"]?\s*:\s*[\'"]([a-zA-Z0-9_]+)[\'"]', js)
        print("All method parameters in js:", set(all_methods))
except Exception as e:
    print("Error:", e)
