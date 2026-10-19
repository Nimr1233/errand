# Browser pool benchmark (spec section 16)

Measured on 2026-10-19 on the user's laptop: 16 GB RAM, i5-10500H, RTX 3060 Laptop. Playwright with Chromium 148, headless. The 53 brains (llama-server, `-np 53`, 4,096 tokens each) were loaded the whole time. Other apps were open, so only 5.56 GB of RAM was free at the start.

**Command:** `python -X utf8 bench/windows.py`. Raw numbers are in `bench/windows.json`.

## Results

| Measure | Result |
|---|---|
| Free RAM before loading the brains | 5.56 GB |
| Free RAM with 53 brains loaded | 3.98 GB (the brains take about 1.6 GB of regular RAM) |
| **Private windows held above the 2 GB safety line** | **25** (the 26th dipped to 1.99 GB) |
| Memory per window | about 70–76 MB on average (Wikipedia article pages) |
| Page load time | 1.1–1.7 s per page, no slower at 25 windows than at 2 (the first load, 4.4 s, includes browser start-up) |
| **Clean hand-off** (wipe a window, open a fresh one, load a page) | **0.146 s** median, 0.166 s at most (10 runs) |
| Live pictures (screencast on all 26 windows while each scrolled, 17 s) | 27.9 frames per second in total (about 1 per tile), 34.8% CPU |

## What it means

- **20 windows** is a safe default and **25** the maximum on this laptop with today's free memory. Each extra 1 GB of free RAM, for example from closing other apps, makes room for about 13 more light windows.
- Wikipedia pages are light. Heavy pages full of scripts, like web apps and social media, use more memory per window, so fewer fit. The memory guard stops opening windows automatically when free RAM drops below 2 GB.
- Hand-off is fast enough that wiping a window between jobs costs nothing noticeable.
- Mission control's live pictures run at about 1 frame per second per tile with all windows active, at about a third of the CPU. Fine for watching. For smoother video on one agent, raise that tile's rate when it's selected.

## Not measured

- heavy script-filled pages
- the brains and the browsers both busy at the same time (in this test the brains were loaded but idle)
- a visible (non-headless) browser
- the phone link over Tailscale
