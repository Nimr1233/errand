"""Benchmark the browser pool (spec section 16): how many private browser windows fit
next to the 53 loaded brains, how long a clean hand-off takes, and what the mission-control
live pictures (Chrome screencast) cost.

Opens windows one at a time (one different Wikipedia article each, one load at a time) until
free RAM drops below the spec's 2 GB guard or MAX_WINDOWS is reached.

Run:  python -X utf8 bench/windows.py
"""
import asyncio, ctypes, json, pathlib, sys, time
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import brains  # reuse start_server so the 53 brains are loaded exactly as in the brain benchmark

ROOT = pathlib.Path(__file__).parent
MAX_WINDOWS = 40
GUARD_GB = 2.0  # spec section 16: stop opening windows below 2 GB free RAM
ARTICLES = ['Mount_Everest', 'Python_(programming_language)', 'Pakistan', 'Moon', 'Internet', 'Football',
            'Albert_Einstein', 'Photosynthesis', 'Roman_Empire', 'Coffee', 'Volcano', 'Chess', 'Jupiter',
            'Mathematics', 'Leonardo_da_Vinci', 'Amazon_rainforest', 'Bicycle', 'Electricity', 'Honey_bee',
            'Great_Wall_of_China', 'Solar_System', 'Cricket', 'Penguin', 'Olympic_Games', 'Tea', 'Earthquake',
            'Rainbow', 'Library', 'Bridge', 'Television', 'Elephant', 'Desert', 'Piano', 'Lighthouse',
            'Glacier', 'Printing_press', 'Telescope', 'Coral_reef', 'Train', 'Paper']


class MEMSTAT(ctypes.Structure):
    _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + \
               [(n, ctypes.c_ulonglong) for n in ('total', 'avail', 'tpf', 'apf', 'tv', 'av', 'aev')]


def free_gb():
    m = MEMSTAT(); m.dwLength = ctypes.sizeof(MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2**30


def cpu_times():
    idle, kern, user = (ctypes.c_ulonglong() for _ in range(3))
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
    return idle.value, kern.value + user.value  # kernel time includes idle time


def cpu_pct(a, b):
    return round(100 * (1 - (b[0] - a[0]) / max(1, b[1] - a[1])), 1)


async def main():
    with open(ROOT / 'server-windows.log', 'w') as log:
        before_server = free_gb()
        proc, cmd = brains.start_server(53, 4096, log)
        try:
            await asyncio.sleep(5)
            after_server = free_gb()
            print(f'free RAM {before_server:.2f} GB -> {after_server:.2f} GB with 53 brains loaded', flush=True)
            result = await run_browser()
        finally:
            proc.terminate(); proc.wait(30)
    result.update({'free_gb_before_brains': round(before_server, 2), 'free_gb_with_brains': round(after_server, 2),
                   'brain_server_cmd': ' '.join(cmd)})
    (ROOT / 'windows.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'windows'}, indent=2))


async def run_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        start_free = free_gb()
        windows, rows, hit_guard = [], [], False
        for n in range(1, MAX_WINDOWS + 1):
            ctx = await browser.new_context(viewport={'width': 1280, 'height': 800})
            page = await ctx.new_page()
            t = time.perf_counter()
            await page.goto(f'https://en.wikipedia.org/wiki/{ARTICLES[n - 1]}', wait_until='load', timeout=60000)
            load = time.perf_counter() - t
            windows.append((ctx, page))
            await asyncio.sleep(1.0)  # let memory settle; also keeps requests to one site slow and polite
            f = free_gb()
            rows.append({'windows': n, 'load_seconds': round(load, 2), 'free_gb': round(f, 2),
                         'mb_per_window_avg': round((start_free - f) * 1024 / n)})
            print(f"{n:2d} windows  load {load:5.2f}s  free {f:5.2f} GB  ~{rows[-1]['mb_per_window_avg']} MB/window",
                  flush=True)
            if f < GUARD_GB:
                hit_guard = True
                break

        # Mission-control live pictures: screencast every open window while each one scrolls.
        frames = {'n': 0}
        sessions = []
        for _, page in windows:
            s = await page.context.new_cdp_session(page)
            def on_frame(params, s=s):
                frames['n'] += 1
                asyncio.ensure_future(s.send('Page.screencastFrameAck', {'sessionId': params['sessionId']}))
            s.on('Page.screencastFrame', on_frame)
            await s.send('Page.startScreencast', {'format': 'jpeg', 'quality': 40,
                                                  'maxWidth': 640, 'maxHeight': 400, 'everyNthFrame': 2})
            sessions.append(s)
        c0, t0 = cpu_times(), time.perf_counter()
        for _ in range(15):  # 15 s of every window scrolling, like agents working
            await asyncio.gather(*(page.mouse.wheel(0, 400) for _, page in windows))
            await asyncio.sleep(1)
        cast_cpu, cast_secs = cpu_pct(c0, cpu_times()), time.perf_counter() - t0
        for s in sessions:
            await s.send('Page.stopScreencast')

        # Clean hand-off: wipe a window (close its context) and give the next agent a fresh one.
        handoffs = []
        ctx, _ = windows.pop()
        light = 'data:text/html,<h1>next job</h1>'
        for _ in range(10):
            t = time.perf_counter()
            await ctx.close()
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto(light, wait_until='load')
            handoffs.append(time.perf_counter() - t)
        await browser.close()

    return {'max_windows_above_guard': len(rows) - 1 if hit_guard else len(rows),
            'stopped_by': 'memory guard (2 GB free)' if hit_guard else f'MAX_WINDOWS={MAX_WINDOWS}',
            'screencast': {'windows': len(windows) + 1, 'seconds': round(cast_secs, 1), 'cpu_percent': cast_cpu,
                           'frames_per_second_total': round(frames['n'] / cast_secs, 1)},
            'handoff_seconds': {'median': round(sorted(handoffs)[5], 3), 'max': round(max(handoffs), 3)},
            'windows': rows}


if __name__ == '__main__':
    asyncio.run(main())
