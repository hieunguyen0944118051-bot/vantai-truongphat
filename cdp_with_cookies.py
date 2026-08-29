import subprocess, time, json, urllib.request, urllib.parse, re, http.cookiejar, asyncio, websockets, os

# 1. Login via urllib to get authenticated cookies
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req_get = urllib.request.Request('https://gps.binhanh.vn/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
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
req_post = urllib.request.Request(
    'https://gps.binhanh.vn/',
    data=urllib.parse.urlencode(post_data).encode('utf-8'),
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Content-Type': 'application/x-www-form-urlencoded'}
)
resp_post = opener.open(req_post)
print("✅ Logged in via HTTP! URL:", resp_post.geturl())

cookies_to_set = []
for c in cj:
    cookies_to_set.append({
        "name": c.name,
        "value": c.value,
        "domain": ".binhanh.vn",
        "path": "/"
    })

# 2. Launch headless Chrome
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = "/tmp/chrome_ba_gps_session"
os.system(f"rm -rf {user_data_dir}")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9223",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu"
])
time.sleep(2)

try:
    resp = urllib.request.urlopen("http://127.0.0.1:9223/json")
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

            # Set cookies in Chrome
            print("🍪 Setting cookies into Chrome...")
            for ck in cookies_to_set:
                await send("Network.setCookie", ck)

            # Navigate straight to OnlineM.aspx
            print("🚀 Navigating straight to https://gps.binhanh.vn/OnlineM.aspx...")
            await send("Page.navigate", {"url": "https://gps.binhanh.vn/OnlineM.aspx"})

            # Capture network requests & responses
            captured_data = []
            start_time = time.time()

            async def listen_loop():
                while time.time() - start_time < 20:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        msg = json.loads(raw)
                        method = msg.get("method")
                        params = msg.get("params", {})

                        if method == "Network.requestWillBeSent":
                            u = params.get("request", {}).get("url", "")
                            if any(k in u.lower() for k in ["vehicle", "online", "tracking", "data", "hub", "get"]):
                                print("🌐 URL:", u[:100])

                        elif method == "Network.responseReceived":
                            resp_u = params.get("response", {}).get("url", "")
                            req_id = params.get("requestId")
                            mime = params.get("response", {}).get("mimeType", "")
                            if "json" in mime or any(k in resp_u.lower() for k in ["vehicle", "online", "tracking", "hub", "get"]):
                                try:
                                    await send("Network.getResponseBody", {"requestId": req_id})
                                except Exception:
                                    pass

                        elif "result" in msg and "body" in msg["result"]:
                            b = msg["result"]["body"]
                            if "63" in b and len(b) > 200:
                                print(f"🎯 FOUND DATA WITH '63' ({len(b)} bytes)!")
                                with open("/Users/alex/.gemini/antigravity/scratch/transport-management/real_gps_data.json", "w", encoding="utf-8") as f_out:
                                    f_out.write(b)
                    except asyncio.TimeoutError:
                        pass

            await listen_loop()

            # Now evaluate DOM: extract all vehicle rows from the page!
            dom_extract_script = """
            (() => {
                const results = [];
                // Look for table rows or list items with plate numbers
                const textNodes = document.querySelectorAll('tr, div, li');
                const plates = [];
                document.querySelectorAll('*').forEach(el => {
                    const txt = el.innerText || '';
                    if (/63[A-Z0-9\.\-]{3,10}/.test(txt) && el.children.length === 0) {
                        plates.push(txt.trim());
                    }
                });

                return {
                    title: document.title,
                    url: window.location.href,
                    platesSample: Array.from(new Set(plates)).slice(0, 30),
                    bodyLength: document.body ? document.body.innerHTML.length : 0
                };
            })()
            """
            await send("Runtime.evaluate", {"expression": dom_extract_script, "returnByValue": True})
            eval_res = await ws.recv()
            print("📄 DOM Extraction result:", eval_res[:400])

    asyncio.run(run_cdp())

finally:
    proc.terminate()
    print("🏁 Finished CDP run.")
