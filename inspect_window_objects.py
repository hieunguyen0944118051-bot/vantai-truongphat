import subprocess, time, json, urllib.request, urllib.parse, re, http.cookiejar, asyncio, websockets, os

# 1. Login via urllib to get authenticated cookies
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req_get = urllib.request.Request('https://gps.binhanh.vn/', headers={'User-Agent': 'Mozilla/5.0'})
html_get = opener.open(req_get).read().decode('utf-8', errors='ignore')

vs = re.search(r'id="__VIEWSTATE"\s+value="([^"]+)"', html_get).group(1)
vsg = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]+)"', html_get).group(1)
ev = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]+)"', html_get).group(1)

post_data = {
    '__LASTFOCUS': '', '__EVENTTARGET': '', '__EVENTARGUMENT': '',
    '__VIEWSTATE': vs, '__VIEWSTATEGENERATOR': vsg, '__EVENTVALIDATION': ev,
    'UserLogin1$txtLoginUserName': 'truongphat68',
    'UserLogin1$txtLoginPassword': 'bN8Xm2Wp6KzV',
    'UserLogin1$hdfPassword': '',
    'UserLogin1$chkRememberMe': 'on',
    'UserLogin1$btnLogin': 'Đăng nhập'
}
req_post = urllib.request.Request('https://gps.binhanh.vn/', data=urllib.parse.urlencode(post_data).encode('utf-8'))
resp_post = opener.open(req_post)

cookies_to_set = [{"name": c.name, "value": c.value, "domain": ".binhanh.vn", "path": "/"} for c in cj]

# 2. Launch Chrome
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = "/tmp/chrome_ba_gps_win"
os.system(f"rm -rf {user_data_dir}")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9224",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu"
])
time.sleep(2)

try:
    resp = urllib.request.urlopen("http://127.0.0.1:9224/json")
    tabs = json.loads(resp.read().decode('utf-8'))
    ws_url = tabs[0]["webSocketDebuggerUrl"]

    async def run_cdp():
        async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
            msg_id = 1

            async def send(method, params=None):
                nonlocal msg_id
                m = {"id": msg_id, "method": method, "params": params or {}}
                msg_id += 1
                await ws.send(json.dumps(m))
                return m["id"]

            await send("Network.enable")
            await send("Page.enable")
            await send("Runtime.enable")

            for ck in cookies_to_set:
                await send("Network.setCookie", ck)

            print("🚀 Navigating to OnlineM.aspx...")
            await send("Page.navigate", {"url": "https://gps.binhanh.vn/OnlineM.aspx"})
            
            # Wait 8 seconds for page and websockets/protobuf to process
            await asyncio.sleep(8)

            # Evaluate script to dump vehicle data structures
            eval_js = """
            (() => {
                const dump = {};
                // Check common BA GPS variables
                for (let k of Object.keys(window)) {
                    if (/vehicle|car|fleet|tracking|device|online/i.test(k)) {
                        try {
                            const val = window[k];
                            if (val && typeof val === 'object') {
                                dump[k] = {
                                    type: Array.isArray(val) ? 'array' : typeof val,
                                    length: Array.isArray(val) ? val.length : Object.keys(val).length,
                                    sample: Array.isArray(val) ? val.slice(0, 3) : Object.keys(val).slice(0, 5)
                                };
                            }
                        } catch(e) {}
                    }
                }
                return dump;
            })()
            """
            eval_id = await send("Runtime.evaluate", {"expression": eval_js, "returnByValue": True})
            
            while True:
                res_raw = await ws.recv()
                msg = json.loads(res_raw)
                if msg.get("id") == eval_id:
                    print("🎯 Found Vehicle Objects in window:")
                    print(json.dumps(msg.get("result", {}).get("result", {}).get("value", {}), indent=2, ensure_ascii=False))
                    break

            # Also extract the vehicle list from the UI table/DOM
            table_js = """
            (() => {
                const rows = [];
                // Look for table rows in the vehicle grid
                document.querySelectorAll('#tblVehicleOnline tr, .grid-row, .ui-jqgrid-bdiv tr, table tr').forEach(tr => {
                    const txt = tr.innerText.replace(/\\t+/g, ' ').trim();
                    if (/63[A-Z0-9]/i.test(txt)) {
                        rows.push(txt.split('\\n').map(s => s.trim()).filter(Boolean));
                    }
                });
                return rows.slice(0, 30);
            })()
            """
            eval_table_id = await send("Runtime.evaluate", {"expression": table_js, "returnByValue": True})
            while True:
                res_raw = await ws.recv()
                msg = json.loads(res_raw)
                if msg.get("id") == eval_table_id:
                    rows = msg.get("result", {}).get("result", {}).get("value", [])
                    print(f"📋 Extracted {len(rows)} Vehicle Rows from UI:")
                    for r in rows[:10]:
                        print("  🚗", " | ".join(r[:8]))
                    with open("/Users/alex/.gemini/antigravity/scratch/transport-management/extracted_ui_rows.json", "w", encoding="utf-8") as f:
                        json.dump(rows, f, indent=2, ensure_ascii=False)
                    break

    asyncio.run(run_cdp())
finally:
    proc.terminate()
