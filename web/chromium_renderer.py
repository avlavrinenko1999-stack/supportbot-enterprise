import asyncio
import contextlib
import os
import secrets
import time

from aiohttp import web
from playwright.async_api import async_playwright

TARGET_URL = "http://127.0.0.1:8080/?embedded=1c&remote=1"
VIEWPORT = {"width": 1440, "height": 900}
SESSION_TTL = 900
ACCESS_TOKEN = os.environ.get("SUPPORTBOT_RENDERER_TOKEN", "")


@web.middleware
async def token_middleware(request, handler):
    if not ACCESS_TOKEN or request.query.get("token") != ACCESS_TOKEN:
        raise web.HTTPForbidden(text="renderer access denied")
    return await handler(request)


class Renderer:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.sessions = {}
        self.lock = asyncio.Lock()

    async def start(self, app):
        self.playwright = await async_playwright().start()
        await self.launch_browser()
        app["cleanup_task"] = asyncio.create_task(self.cleanup_loop())

    async def launch_browser(self):
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-extensions",
                "--no-sandbox",
                "--js-flags=--max-old-space-size=160",
            ],
        )

    async def ensure_browser(self):
        if self.browser is not None and self.browser.is_connected():
            return
        async with self.lock:
            if self.browser is not None and self.browser.is_connected():
                return
            for entry in list(self.sessions.values()):
                with contextlib.suppress(Exception):
                    await entry["context"].close()
            self.sessions.clear()
            with contextlib.suppress(Exception):
                if self.browser:
                    await self.browser.close()
            await self.launch_browser()

    async def stop(self, app):
        app["cleanup_task"].cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await app["cleanup_task"]
        for entry in list(self.sessions.values()):
            await entry["context"].close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            cutoff = time.monotonic() - SESSION_TTL
            for sid, entry in list(self.sessions.items()):
                if entry["last_seen"] < cutoff:
                    await entry["context"].close()
                    self.sessions.pop(sid, None)

    async def get_session(self, sid):
        await self.ensure_browser()
        if not sid or sid not in self.sessions:
            async with self.lock:
                if not sid or sid not in self.sessions:
                    sid = secrets.token_urlsafe(24)
                    context = await self.browser.new_context(viewport=VIEWPORT)
                    page = await context.new_page()
                    await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
                    self.sessions[sid] = {
                        "context": context,
                        "page": page,
                        "last_seen": time.monotonic(),
                        "lock": asyncio.Lock(),
                    }
        self.sessions[sid]["last_seen"] = time.monotonic()
        return sid, self.sessions[sid]


renderer = Renderer()


async def health(request):
    return web.json_response({"ok": renderer.browser is not None, "engine": "chromium", "sessions": len(renderer.sessions)})


async def surface(request):
    sid, _ = await renderer.get_session(request.query.get("sid"))
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>SupportBot Enterprise</title>
<style>html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#eef1f4}}#f{{width:100%;height:100%;object-fit:fill;user-select:none}}</style></head>
<body><img id="f" draggable="false" alt="SupportBot Enterprise">
<script>
var sid={sid!r}, token=new URLSearchParams(location.search).get('token'), img=document.getElementById('f'), busy=false;
function frame(){{if(busy)return;busy=true;img.onload=img.onerror=function(){{busy=false}};img.src='/renderer/frame?token='+encodeURIComponent(token)+'&sid='+encodeURIComponent(sid)+'&t='+Date.now()}}
setInterval(frame,300);frame();
function send(o){{o.sid=sid;fetch('/renderer/input?token='+encodeURIComponent(token),{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(o)}})}}
img.addEventListener('mousedown',function(e){{var r=img.getBoundingClientRect();send({{type:'click',x:(e.clientX-r.left)*1440/r.width,y:(e.clientY-r.top)*900/r.height,button:e.button}})}});
window.addEventListener('keydown',function(e){{e.preventDefault();send({{type:'key',key:e.key,code:e.code,ctrl:e.ctrlKey,alt:e.altKey,shift:e.shiftKey}})}});
window.addEventListener('paste',function(e){{send({{type:'text',text:(e.clipboardData||window.clipboardData).getData('text')}})}});
</script></body></html>"""
    return web.Response(text=html, content_type="text/html")


async def frame(request):
    sid, entry = await renderer.get_session(request.query.get("sid"))
    async with entry["lock"]:
        data = await entry["page"].screenshot(type="jpeg", quality=78, animations="disabled")
    return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "no-store", "X-Renderer-Session": sid})


async def user_input(request):
    payload = await request.json()
    _, entry = await renderer.get_session(payload.get("sid"))
    page = entry["page"]
    async with entry["lock"]:
        if payload.get("type") == "click":
            button = {0: "left", 1: "middle", 2: "right"}.get(int(payload.get("button", 0)), "left")
            await page.mouse.click(float(payload["x"]), float(payload["y"]), button=button)
        elif payload.get("type") == "text":
            await page.keyboard.insert_text(str(payload.get("text", "")))
        elif payload.get("type") == "key":
            key = str(payload.get("key", ""))
            if len(key) == 1:
                await page.keyboard.insert_text(key)
            else:
                names = {"Enter": "Enter", "Backspace": "Backspace", "Tab": "Tab", "Escape": "Escape", "Delete": "Delete", "ArrowUp": "ArrowUp", "ArrowDown": "ArrowDown", "ArrowLeft": "ArrowLeft", "ArrowRight": "ArrowRight"}
                if key in names:
                    await page.keyboard.press(names[key])
    return web.json_response({"ok": True})


def create_app():
    app = web.Application(client_max_size=1024 * 1024, middlewares=[token_middleware])
    app.router.add_get("/renderer/health", health)
    app.router.add_get("/renderer/surface", surface)
    app.router.add_get("/renderer/frame", frame)
    app.router.add_post("/renderer/input", user_input)
    app.on_startup.append(renderer.start)
    app.on_cleanup.append(renderer.stop)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=18081, access_log=None)
