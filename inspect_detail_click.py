import subprocess, time, json, urllib.request, urllib.parse, re, http.cookiejar, asyncio, websockets, os

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

chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = "/tmp/chrome_ba_gps_click"
os.system(f"rm -rf {user_data_dir}")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9227",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu"
])
time.sleep(2)

try:
    resp = urllib.request.urlopen("http://127.0.0.1:9227/json")
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

            # Inspect links with 'Chi tiết' or click first vehicle
            inspect_js = """
            (() => {
                const links = [];
                document.querySelectorAll('a, button, span').forEach(el => {
                    if (el.innerText && el.innerText.includes('Chi tiết')) {
                        links.push({
                            tag: el.tagName,
                            id: el.id,
                            className: el.className,
                            href: el.getAttribute('href'),
                            onclick: el.getAttribute('onclick'),
                            html: el.outerHTML
                        });
                    }
                });

                // Click on the first vehicle link or item
                const firstCar = document.querySelector('td:contains("63E01118"), span:contains("63E01118")') || Array.from(document.querySelectorAll('*')).find(e => e.children.length === 0 && e.innerText.trim() === '63E01118');
                let clicked = false;
                if (firstCar) {
                    firstCar.click();
                    clicked = true;
                }

                return {
                    detailLinks: links.slice(0, 5),
                    clickedCar: clicked
                };
            })()
            """
            eval_id = await send("Runtime.evaluate", {"expression": inspect_js, "returnByValue": True})
            while True:
                res_raw = await ws.recv()
                msg = json.loads(res_raw)
                if msg.get("id") == eval_id:
                    print("Detail link attributes:", json.dumps(msg.get("result", {}).get("result", {}).get("value", {}), indent=2, ensure_ascii=False))
                    break

            # Wait 3 seconds after click to see what popup/infowindow opens
            await asyncio.sleep(3)
            popup_js = """
            (() => {
                // Check all open popups / tooltips / infowindows
                const popups = [];
                document.querySelectorAll('.infoBox, .gm-style-iw, [class*="popup"], [class*="info"], [id*="info"]').forEach(el => {
                    const txt = el.innerText || '';
                    if (txt.length > 10 && txt.length < 1500) {
                        popups.push(txt.replace(/\\s+/g, ' ').trim());
                    }
                });
                return popups;
            })()
            """
            eval_pop_id = await send("Runtime.evaluate", {"expression": popup_js, "returnByValue": True})
            while True:
                res_raw = await ws.recv()
                msg = json.loads(res_raw)
                if msg.get("id") == eval_pop_id:
                    pops = msg.get("result", {}).get("result", {}).get("value", [])
                    print("Popup contents after click:")
                    for p in pops:
                        print("  📌", p)
                    break

    asyncio.run(run())
finally:
    proc.terminate()
