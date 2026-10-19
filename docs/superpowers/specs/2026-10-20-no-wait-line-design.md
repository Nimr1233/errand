# The no-wait line (design)

Date: 2026-10-20. Changes "Borrow, wait, hand off" in section 16 of `2026-10-17-errand-browser-agent-design.md`, and sections 2.1, 2.2 and 2.4 of `2026-10-19-mission-control-room-design.md`.

**Goal:** momentum only. No agent ever stands in line. When all 25 browser windows are busy, the *page* waits on a shelf and the agent goes on with other work.

## 1. Why not phones

The user asked whether agents without a browser window could each get a private Android phone driven by [google/artemis](https://github.com/google/artemis). We checked it on 2026-10-20:
- **What it is.** ARTEMIS is not an AI model. It is a tool (Apache-2.0) that lets an AI use an Android phone like a person: an emulator on the laptop, or a real phone over USB.
- **Memory.** One emulator needs about 2–3 GB of RAM. With the 25 windows open, the laptop has room for 1, maybe 2. Not 28.
- **AI calls.** Every phone step is one vision call to Gemini (about 3–5 s a step). The free tier is one key with a small, unpublished daily limit. One phone working nonstop would use most of it.
- **The local 2B model can't do it.** ARTEMIS needs a model that sees screenshots. Small local models are only on its roadmap.
- **Downloads.** The emulator, a system image, Python 3.12, ARTEMIS and its libraries, ADB, scrcpy and FFmpeg: about 5 GB.
- **Slower anyway.** The "paperwork" tasks (extract, check, recipe, fix, vote) read page text in under a second. On a phone they would take several 3–5 s steps each.

So phones would add waiting, not remove it. A single phone for app-only jobs may come later, in its own spec.

## 2. The rule

When an agent is free, it does the first of these it can:
1. **A page from the shelf**, if it already holds a window or a window is free.
2. **The next task from the shared queue:**
   - It needs no browser: do it now.
   - It needs a browser and a window is free: take the window and do it.
   - It needs a browser and all windows are busy: put the page on the shelf, then repeat step 2.
3. **The queue is empty:** the agent is finished. It goes back to work if new tasks appear later (a late "check" task), or if a window frees up while pages are on the shelf.

**Hand-off.** When an agent finishes a browser page and the shelf has pages, it keeps its window. The window is wiped as in section 16, and the same agent opens the next page from the shelf in it. That counts as one hand-off. If the shelf is empty, the window is returned to the pool.

**Order on the shelf.** Interactive jobs go ahead of bulk jobs (as in section 16). Otherwise the oldest page goes first.

**Stopping an agent.** A stopped agent returns its window to the pool. The page it was on goes back to the front of the queue, as today. The next free agent takes the window with the next page from the shelf (step 1). Until an agent is free, that window stays free: the one moment a window can be free while pages wait.

## 3. What still waits

- **The end of a job.** When the only pages left all need a browser, just 25 can run at once. Agents with no window and nothing left to do are finished.
- **Problems.** An agent that needs your approval keeps its window and waits for your answer, because the page must stay exactly as it is. (Chosen by the user on 2026-10-20 over parking the problem.)

## 4. What the numbers mean

| Where | Shows |
|---|---|
| Agents waiting in line | always 0; the "queued" state is gone |
| BROWSERS HANDED DOWN TV | hand-offs so far, out of hand-offs so far plus pages on the shelf now (e.g. `312/349`) |
| Desk monitor 3 | "PAGES WAITING FOR A WINDOW": pages on the shelf, and the next 3 |
| A finished agent's screen | "last window passed on", "window closed: no pages waiting" or "no window used" |

The engine's status reports `shelf` (pages waiting) and `next_on_shelf` (the next 3, as `site/page`), instead of `waiting` and `next_in_line`. Agent views lose `line`.

## 5. What changes

- **`errand/demo.py`:** the shelf, the rule above, the new status keys. A hand-off update reads "#12 kept its window for the next page: books.toscrape.com/page-88".
- **`errand/static/room.html`:** no queued screen; the TV and desk monitor 3 as in section 4; the finished-screen wording; the info bar wording; **the hand-off beams are removed**, because the window no longer moves between agents.
- **`errand/mcp_server.py`:** `job_status` says "25/25 windows in use · 37 pages waiting for a window"; `list_agents` has no "queued" state.
- **Specs:** master spec section 16 and room spec sections 2.1, 2.2 and 2.4 point here.
- **`HANDOFF.md`:** a short note.

## 6. Tests

- **Demo engine**, checked after every step of a full job with no agent stopped:
  - no agent is ever waiting
  - a window is never free while pages are on the shelf
- **Stopping:** after a stop, the freed window goes to the next page on the shelf as soon as an agent is free.
  - no agent is finished while the queue still has tasks
  - pages done equals the job's pages when it completes
  - every hand-off happened with pages on the shelf
- **Server and connector:** the new status keys and wording.
- **Room (Playwright):** the existing tests still pass, and no agent screen ever shows "QUEUED".
