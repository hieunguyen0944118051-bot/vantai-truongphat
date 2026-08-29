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
opener.open(req_post)
cookies_to_set = [{"name": c.name, "value": c.value, "domain": ".binhanh.vn", "path": "/"} for c in cj]

# 2. Launch Chrome
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = "/tmp/chrome_ba_gps_telemetry"
os.system(f"rm -rf {user_data_dir}")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9225",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu"
])
time.sleep(2)

try:
    resp = urllib.request.urlopen("http://127.0.0.1:9225/json")
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

            # Extract detailed vehicle items
            extract_js = """
            (() => {
                const vehicles = [];
                // Check all elements with vehicle data
                document.querySelectorAll('[id*="vehicle"], [class*="vehicle"], [id*="Vehicle"], [class*="Vehicle"], .carItem, .itemVehicle').forEach(el => {
                    const txt = el.innerText || '';
                    if (/63[A-Z0-9]/i.test(txt) && txt.length < 500) {
                        vehicles.push(txt.trim());
                    }
                });

                // Also check if BA GPS has internal data in Angular / jQuery / Straction
                let internalData = null;
                try {
                    if (window.vehicleOnline) internalData = window.vehicleOnline;
                    else if (window.listVehicles) internalData = window.listVehicles;
                    else if (window.vehiclesData) internalData = window.vehiclesData;
                } catch(e) {}

                return {
                    vehiclesCount: vehicles.length,
                    sample: vehicles.slice(0, 10),
                    fullTextSnippet: document.body.innerText.slice(0, 2000)
                };
            })()
            """
            eval_id = await send("Runtime.evaluate", {"expression": extract_js, "returnByValue": True})
            while True:
                res_raw = await ws.recv()
                msg = json.loads(res_raw)
                if msg.get("id") == eval_id:
                    val = msg.get("result", {}).get("result", {}).get("value", {})
                    print("📊 Body Text Snippet:")
                    print(val.get("fullTextSnippet", "")[:1200])
                    break
    asyncio.run(run())
finally:
    proc.terminate()
