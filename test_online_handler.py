import urllib.request, urllib.parse, http.cookiejar, json, re

with open('/Users/alex/.gemini/antigravity/scratch/transport-management/onlinem_dump.html') as f:
    html = f.read()

# Check mentions of OnlineHandler in JS
matches = re.findall(r'OnlineHandler\.ashx[^\n]+', html)
for m in matches[:10]:
    print('Handler snippet:', m.strip()[:180])

# Search for PK_UserID and Customer ID
user_id = re.search(r'PK_UserID=([a-f0-9\-]+)', html)
if user_id:
    print('🔑 PK_UserID:', user_id.group(1))

# Check report pages or vehicle list handlers
handlers = re.findall(r'[\'"](/[^/]+\.ashx[^\'"]*)[\'"]', html)
print('📂 All ashx handlers in page:', set(handlers))
