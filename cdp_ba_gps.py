import subprocess, time, json, urllib.request, asyncio, websockets, os

chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = "/tmp/chrome_ba_gps"
os.system(f"rm -rf {user_data_dir}")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu"
])
time.sleep(2)

try:
    resp = urllib.request.urlopen("http://127.0.0.1:9222/json")
    tabs = json.loads(resp.read().decode('utf-8'))
    ws_url = tabs[0]["webSocketDebuggerUrl"]
    print("🔌 CDP WebSocket URL:", ws_url)

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

            # Navigate to login
            print("🚀 Navigating to https://gps.binhanh.vn/...")
            await send("Page.navigate", {"url": "https://gps.binhanh.vn/"})

            # Wait for load and fill login
            await asyncio.sleep(4)
            print("🔑 Submitting login form...")
            login_code = """
            (() => {
                const u = document.getElementById('UserLogin1_txtLoginUserName');
                const p = document.getElementById('UserLogin1_txtLoginPassword');
                const btn = document.getElementById('UserLogin1_btnLogin');
                if (u && p && btn) {
                    u.value = 'truongphat68';
                    p.value = 'bN8Xm2Wp6KzV';
                    btn.click();
                    return 'CLICKED_LOGIN';
                }
                return 'NOT_FOUND';
            })()
            """
            await send("Runtime.evaluate", {"expression": login_code})

            print("⏳ Listening for BA GPS network traffic...")
            start_t = time.time()
            req_map = {}

            while time.time() - start_t < 15:
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(raw_msg)
                    method = msg.get("method")
                    params = msg.get("params", {})

                    if method == "Network.requestWillBeSent":
                        req_url = params.get("request", {}).get("url", "")
                        req_id = params.get("requestId")
                        if any(k in req_url.lower() for k in ["vehicle", "online", "gps", "hub", "service", "api", "report"]):
                            print("🌐 Network Request:", req_url[:120])
                            req_map[req_id] = req_url

                    elif method == "Network.responseReceived":
                        req_id = params.get("requestId")
                        resp_url = params.get("response", {}).get("url", "")
                        status = params.get("response", {}).get("status")
                        if req_id in req_map or any(k in resp_url.lower() for k in ["vehicle", "online", "hub", "api", "service", "report"]):
                            print(f"📥 Response [{status}]:", resp_url[:120])
                            try:
                                get_id = await send("Network.getResponseBody", {"requestId": req_id})
                                req_map[get_id] = resp_url
                            except Exception:
                                pass

                    elif "result" in msg and "body" in msg["result"]:
                        body = msg["result"]["body"]
                        print(f"📦 Response Body ({len(body)} bytes):", body[:200])
                        if "63" in body:
                            print("🎯 FOUND FLEET DATA IN RESPONSE!")
                            with open("/Users/alex/.gemini/antigravity/scratch/transport-management/captured_fleet_data.json", "w", encoding="utf-8") as f:
                                f.write(body)

                except asyncio.TimeoutError:
                    pass

            # Inspect final page URL
            eval_script = "window.location.href"
            await send("Runtime.evaluate", {"expression": eval_script})
            eval_resp = await ws.recv()
            print("📄 Page URL after login:", eval_resp)

    asyncio.run(run_cdp())

finally:
    proc.terminate()
    print("🏁 Done capturing.")
