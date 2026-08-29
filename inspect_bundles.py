import urllib.request, re

url = 'https://gps.binhanh.vn/OnlineM/bundles/scripts?v=20260829v1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        js = resp.read().decode('utf-8', errors='ignore')
        print(f"Bundle Script Length: {len(js)}")
        
        # Search for OnlineHandler method calls
        matches = re.findall(r'url\s*:\s*[\'"][^\'"]*OnlineHandler\.ashx[^\'"]*[\'"][^;]+', js)
        print(f"Found {len(matches)} occurrences of OnlineHandler.ashx:")
        for m in matches[:15]:
            method_m = re.search(r'method[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]', m)
            if method_m:
                print("  Method:", method_m.group(1))
            else:
                print("  Snippet:", m[:100].replace('\n', ' '))
                
        # Also check all .ashx calls
        ashx_calls = re.findall(r'[\'"](/HttpHandlers/[a-zA-Z0-9_\.]+\.ashx[^\'"]*)[\'"]', js)
        print("All HTTP Handlers called:")
        for h in set(ashx_calls):
            print("  *", h)
except Exception as e:
    print("Error:", e)
