import subprocess, time, json, urllib.request, urllib.parse, re, http.cookiejar, asyncio, websockets, os

# 1. Login
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
opener.open(req_post)
cookies_to_set = [{"name": c.name, "value": c.value, "domain": ".binhanh.vn", "path": "/"} for c in cj]

# 2. Launch Chrome
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = "/tmp/chrome_ba_gps_details"
os.system(f"rm -rf {user_data_dir}")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9226",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu"
])
time.sleep(2)

try:
    resp = urllib.request.urlopen("http://127.0.0.1:9226/json")
    tabs = json.loads(resp.read().decode('utf-8'))
    ws_url = tabs[0]["webSocketDebuggerUrl"]

    async def run():
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

            await send("Page.navigate", {"url": "https://gps.binhanh.vn/OnlineM.aspx"})
            await asyncio.sleep(10)

            # Click each car in the vehicle list to populate detail / tooltip
            click_and_extract_js = """
            (() => {
                const results = [];
                // Find all vehicle item elements in the left panel
                const items = document.querySelectorAll('.itemVehicle, [id^="itemVehicle_"], [class*="car-item"], [class*="vehicle-item"]');
                
                // Also inspect all elements inside vehicle list container
                const listContainer = document.querySelector('#contentListVehicle, #listVehicle, .list-vehicle, #divVehicleList');
                
                // Let us inspect the raw list items
                const carElements = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.children.length === 0 && /^63[EFGH][0-9]{5}$/.test(el.innerText.trim())) {
                        carElements.push(el);
                    }
                });

                // For each car element, get its parent / row text
                carElements.forEach(el => {
                    let parent = el.parentElement;
                    for (let i = 0; i < 4; i++) {
                        if (parent && parent.innerText && parent.innerText.length > 20) break;
                        if (parent && parent.parentElement) parent = parent.parentElement;
                    }
                    if (parent) {
                        results.push({
                            plate: el.innerText.trim(),
                            infoText: parent.innerText.replace(/\\s+/g, ' ').trim()
                        });
                    }
                });

                return {
                    totalCarsFound: carElements.length,
                    results: results
                };
            })()
            """
            eval_id = await send("Runtime.evaluate", {"expression": click_and_extract_js, "returnByValue": True})
            while True:
                res_raw = await ws.recv()
                msg = json.loads(res_raw)
                if msg.get("id") == eval_id:
                    data = msg.get("result", {}).get("result", {}).get("value", {})
                    print(f"🎯 Found {data.get('totalCarsFound')} vehicles with details:")
                    for item in data.get("results", []):
                        print("🚗", item.get("plate"), "=>", item.get("infoText"))
                    with open("/Users/alex/.gemini/antigravity/scratch/transport-management/full_telemetry_extracted.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    break
    asyncio.run(run())
finally:
    proc.terminate()
