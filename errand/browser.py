"""The browser windows (main spec section 16 and the no-wait line spec): one headless Chromium holds up
to 25 private windows (browser contexts), shared by the 53 agents.
- Every page gets a fresh, empty window that is closed (wiped) when the page is done: no cookies,
  storage or logins carry over from one page to the next.
- Memory guard: no new window opens while free RAM is under 2 GB (measured limit, bench/windows.md).
- A page that hasn't loaded in 30 s is given up, and its window wiped and freed.
- If Chromium crashes, the next page starts a fresh one.
Fetch ladder (main spec section 14), for pages a plain download can't read:
- render: a JavaScript page, loaded in a window until the network goes quiet
- stealth: a page that refused plain downloads, loaded in Scrapling's stealth browser with CAPTCHA
  solving OFF (solve_cloudflare=False). A CAPTCHA or bot check still ends as blocked.
"""
import asyncio, ctypes, threading

SIZE = 25
MIN_FREE_GB = 2.0
TIMEOUT = 30


class MEMSTAT(ctypes.Structure):
    _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + \
               [(n, ctypes.c_ulonglong) for n in ('total', 'avail', 'tpf', 'apf', 'tv', 'av', 'aev')]


def free_gb():
    m = MEMSTAT()
    m.dwLength = ctypes.sizeof(MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2**30


class Pool:
    def __init__(self, size=SIZE, min_free_gb=MIN_FREE_GB, timeout=TIMEOUT):
        self.size, self.min_free, self.timeout = size, min_free_gb, timeout
        self.lock = threading.Lock()
        self.in_use = 0
        self.loop = self.browser = self.pw = None

    def take(self):
        """Borrow a window if one is free. Never waits: no window means the page waits, not the agent."""
        with self.lock:
            # shortcut: with no window open, one always opens even when RAM is low, so a job can't stall
            if self.in_use >= self.size or (self.in_use and free_gb() < self.min_free):
                return False
            self.in_use += 1
            return True

    def free(self):
        with self.lock:
            return self.size - self.in_use

    def give_back(self):
        with self.lock:
            self.in_use = max(0, self.in_use - 1)

    def render(self, url, user_agent, shot=True):
        """Load a page in a fresh window: {'status': 'ok', 'html', 'code', 'shot': jpeg bytes} or a reason."""
        self._start()
        try:
            return asyncio.run_coroutine_threadsafe(self._render(url, user_agent, shot), self.loop).result(self.timeout + 30)
        except Exception as e:
            return {'status': f'error: {type(e).__name__}'}

    def stealth(self, url):
        """Scrapling's stealth browser, CAPTCHA solving off. It runs its own browser, in this thread."""
        from scrapling.fetchers import StealthyFetcher
        from .fetch import text
        try:
            page = StealthyFetcher.fetch(url, headless=True, solve_cloudflare=False, disable_resources=True,
                                         hide_canvas=True, block_webrtc=True, network_idle=True,
                                         timeout=self.timeout * 1000)
            return {'status': 'ok', 'code': page.status, 'html': text(page)}
        except Exception as e:
            return {'status': f'error: {type(e).__name__}'}

    def close(self):
        if self.loop:
            try:
                asyncio.run_coroutine_threadsafe(self._close(), self.loop).result(30)
            except Exception:
                pass
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop = None

    # ---- the browser's own thread ----
    def _start(self):
        with self.lock:
            if self.loop:
                return
            self.loop = asyncio.new_event_loop()
            threading.Thread(target=self.loop.run_forever, daemon=True, name='browser').start()

    async def _chromium(self):
        if self.browser is None or not self.browser.is_connected():  # first page, or after a crash
            from playwright.async_api import async_playwright
            if self.pw is None:
                self.pw = await async_playwright().start()
            self.browser = await self.pw.chromium.launch(headless=True)
        return self.browser

    async def _render(self, url, user_agent, shot):
        from playwright.async_api import TimeoutError as Slow
        ctx = await (await self._chromium()).new_context(user_agent=user_agent, viewport={'width': 1280, 'height': 800},
                                                         device_scale_factor=0.5)  # 640x400 pictures for the room
        try:
            page = await ctx.new_page()
            resp = await page.goto(url, wait_until='load', timeout=self.timeout * 1000)
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Slow:
                pass  # a page that keeps talking (ads, live updates) is read as it is now
            return {'status': 'ok', 'code': resp.status if resp else 0, 'html': await page.content(),
                    'shot': await page.screenshot(type='jpeg', quality=40) if shot else None}
        except Slow:
            return {'status': f'blocked: page did not load in {self.timeout} s'}
        except Exception as e:
            return {'status': f'error: {type(e).__name__}'}
        finally:
            await ctx.close()  # the wipe: this window's cookies, storage and pages are gone

    async def _close(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()
        self.browser = self.pw = None
