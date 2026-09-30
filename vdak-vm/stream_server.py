"""
vdak-vm/stream_server.py
Zero-latency native CDP screencast stream for SEVA AI Kiosk.
Uses local interactive government portal simulation (no network timeouts).
"""

import asyncio
import base64
from aiohttp import web
from playwright.async_api import async_playwright

current_frame: bytes = b""
cdp_session = None

PORTAL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SEVA Kiosk Portal</title>
<style>
  body { margin:0; padding:32px; font-family: 'Segoe UI', Arial, sans-serif; background:#0f172a; color:#f8fafc; }
  .header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #334155; padding-bottom:16px; margin-bottom:24px; }
  .logo { font-size:24px; font-weight:700; color:#38bdf8; letter-spacing:1px; }
  .badge { background:#0369a1; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600; }
  .card { background:#1e293b; border-radius:12px; padding:24px; border:1px solid #334155; margin-bottom:20px; }
  .form-group { margin-bottom:18px; }
  label { display:block; margin-bottom:8px; font-size:14px; color:#94a3b8; font-weight:500; }
  input { width:100%; box-sizing:border-box; padding:14px 16px; border-radius:8px; border:1px solid #475569; background:#0f172a; color:#fff; font-size:16px; outline:none; transition:0.2s; }
  input:focus { border-color:#38bdf8; box-shadow:0 0 0 2px rgba(56,189,248,0.25); }
  .btn { display:inline-block; background:#0284c7; color:#fff; font-weight:600; padding:14px 28px; border-radius:8px; border:none; cursor:pointer; font-size:15px; }
  .status { margin-top:14px; font-size:14px; color:#4ade80; }
</style>
</head>
<body>
  <div class="header">
    <div class="logo">🏛️ SEVA AI — MAHARASHTRA E-SERVICES</div>
    <div class="badge">SANDBOX VM ACTIVE</div>
  </div>

  <div class="card">
    <h2 style="margin-top:0; color:#f1f5f9;">संजय गांधी निराधार अनुदान योजना (Application)</h2>
    <p style="color:#94a3b8; font-size:14px;">Automated form navigation powered by Playwright Sandbox Agent.</p>

    <div class="form-group">
      <label>Beneficiary Full Name / अर्जदाराचे नाव:</label>
      <input type="text" id="name" placeholder="Waiting for voice input..." />
    </div>

    <div class="form-group">
      <label>District / जिल्हा:</label>
      <input type="text" id="district" placeholder="District name..." />
    </div>

    <div class="form-group">
      <label>Application Category / वर्गवारी:</label>
      <input type="text" id="category" placeholder="Category..." />
    </div>

    <button class="btn" id="submitBtn">Verify & Submit Application</button>
    <div class="status" id="statusMsg"></div>
  </div>
</body>
</html>
"""

async def browser_loop():
    global current_frame, cdp_session
    print("[STREAM] Starting Chromium CDP pipeline...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1024,640"
            ]
        )
        context = await browser.new_context(viewport={"width": 1024, "height": 640})
        page = await context.new_page()

        # Connect native screencast listener
        cdp_session = await context.new_cdp_session(page)

        async def on_screencast(event):
            global current_frame
            current_frame = base64.b64decode(event.get("data", ""))
            try:
                await cdp_session.send("Page.screencastFrameAck", {"sessionId": event.get("sessionId")})
            except Exception:
                pass

        cdp_session.on("Page.screencastFrame", on_screencast)

        # Start 25 FPS native screencast
        await cdp_session.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 55,
            "maxWidth": 1024,
            "maxHeight": 640,
            "everyNthFrame": 1
        })

        # Load local interactive portal
        await page.set_content(PORTAL_HTML, wait_until="commit")

        # Autonomous typing demo
        await asyncio.sleep(2)
        await page.click("#name")
        for char in "Lalit Patil":
            await page.keyboard.type(char, delay=70)

        await asyncio.sleep(1)
        await page.click("#district")
        for char in "Jalgaon":
            await page.keyboard.type(char, delay=70)

        await asyncio.sleep(1)
        await page.click("#category")
        for char in "Niradhar Yojana - Rural":
            await page.keyboard.type(char, delay=70)

        await asyncio.sleep(1)
        await page.click("#submitBtn")
        await page.evaluate("document.getElementById('statusMsg').innerText = '✓ Form Verified & Dispatched to Tahsil Office'")

        # Infinite smooth scroll demonstration
        while True:
            await page.mouse.wheel(0, 150)
            await asyncio.sleep(1.2)
            await page.mouse.wheel(0, -150)
            await asyncio.sleep(1.2)

async def mjpeg_handler(request):
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Access-Control-Allow-Origin': '*'
        }
    )
    await response.prepare(request)
    while True:
        if current_frame:
            chunk = (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n'
                b'Content-Length: ' + str(len(current_frame)).encode() + b'\r\n\r\n' +
                current_frame + b'\r\n'
            )
            try:
                await response.write(chunk)
            except (ConnectionResetError, asyncio.CancelledError):
                break
        await asyncio.sleep(0.04)
    return response

async def index_handler(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>SEVA AI - Sandbox Stream</title>
        <style>
            body { background:#090d16; color:#f8fafc; font-family:sans-serif; text-align:center; margin:0; padding:16px; }
            h3 { color:#38bdf8; margin:0 0 12px 0; }
            .box { display:inline-block; border:2px solid #38bdf8; border-radius:10px; overflow:hidden; box-shadow:0 0 30px rgba(56,189,248,0.25); background:#0f172a; }
            img { display:block; width:960px; max-width:95vw; height:auto; }
        </style>
    </head>
    <body>
        <h3>⚡ SEVA AI — Live VM Sandbox Screencast</h3>
        <div class="box">
            <img src="/stream" onerror="setTimeout(() => { this.src = '/stream?' + Date.now(); }, 1000);" />
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def init_app():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/stream', mjpeg_handler)
    asyncio.create_task(browser_loop())
    return app

if __name__ == '__main__':
    web.run_app(init_app(), host='127.0.0.1', port=8080)
