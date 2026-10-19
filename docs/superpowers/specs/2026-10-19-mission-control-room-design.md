# Mission control room and the chief's computer (design)

Date: 2026-10-19. Extends section 17 of `2026-10-17-errand-browser-agent-design.md`.

**What this adds:**
- Mission control becomes a 3D command-center room you can walk around in.
- A personal "chief's computer" at the chair runs the real Claude Code, which commands the agents through an Errand connector.

**Visual reference:** `docs/mockups/mission-control-room.html` (mockup v11). Open it in a browser. It shows the approved room, but not yet the changes in section 2.

## 1. Relationship to section 17

- **Main view.** The 3D room is the main mission control view, on the laptop and on the phone.
- **List view.** Section 17's flat layout (top bar, tile grid, focus panel, cards, results strip) stays as the **list view**. It is used in three cases:
  - when the device has no WebGL
  - for screen readers and keyboard-only use
  - when the user picks it with a "List view" button
- **Same data, same rules.** Both views read the same `/ws` events and use the same approvals and safety rules as section 17.
- **Live pictures.** In the room, an agent's screen shows its window's live picture only while you are zoomed in on it, at the focused-tile budget from section 17. The list view keeps section 17's live tiles. This keeps the room's picture cost near zero when nobody is zoomed in.

## 2. The room

### 2.1 Layout (as in mockup v11)

- **Shape.** An eight-sided room, dark gunmetal (walls `#0F1316`).
- **Ceiling.** A pale cyan light strip runs where each wall meets the ceiling. The ceiling itself is a night sky (2.3).
- **The 53 agent screens.** Nine per wall on six walls, three rows of three:
  - front-left: agents 1–9
  - front-right: agents 10–18
  - right: agents 19–27
  - back-right: agents 28–36
  - back-left: agents 37–45
  - left: agents 46–53
- **Front wall.** The main screen shows pages done out of the total, a progress bar, the speed and the time left. Small button panels with steady amber lights sit on either side.
- **Back wall.** Three server racks with steady (never blinking) lights.
- **Centre.** A U-shaped console with keyboards and 5 desk monitors:
  1. windows in use
  2. brains online
  3. queued for a window (and the next three in line)
  4. last hand-off
  5. speed
- **The chair** stands in the middle, facing the main screen. The chief's computer is next to it (section 3).

### 2.2 The three TVs

The TVs are mounted high on the walls, **fixed in the room**. They never follow the camera.

| TV | Where | Shows | Small text |
|---|---|---|---|
| AGENTS FINISHED | front-left corner | agents with no work left in this job, out of the agents on the job (e.g. `23/53`) | "no work left in this job" |
| BROWSERS HANDED DOWN | front wall, above the main screen | hand-offs so far, out of hand-offs so far plus agents waiting in line now (e.g. `23/28` = 23 done, 5 waiting) | "windows passed to waiting agents" |
| PROBLEMS | front-right corner | problems waiting for you now | "N raised so far · waiting on you" or "all clear" |

**What the counts mean.** These definitions follow how the engine works (sections 13 and 16 of the main spec).
- **No fixed page lists.** Agents pull the next task from a shared queue, so no agent owns a fixed list of pages.
- **Finished.** An agent is "finished" when the queue has nothing left for it and its last task is done. With a shared queue, this count stays low for most of a job and climbs near the end, because agents stay busy until the work runs out.
- **Hand-offs.** A hand-off is section 16's: a window passed straight from one agent to the next one waiting in line.
- **Mockup difference.** Mockup v11's demo gave each agent a fixed share of pages (`7/19`). The real room and demo mode use the definitions above instead.

**How the numbers look** (changed from v11):
- **Font.** Orbitron Bold (Google Fonts) for every number on the TVs, the main screen and the desk monitors. Labels stay in Share Tech Mono.
- **Size.** Digits fill about two-thirds of each TV's screen height. The `/53` and `/28` are about 40% of the digit height, in the same bright colour.
- **Colour.** Bright cyan (`#8FF7FB`) on pure black (`#000000`), with a soft, steady glow.
- **PROBLEMS.** The number is red (`#FF5A52`) when above 0, and cyan at 0.
- **TV size.** About 20% bigger than in v11.
- **Labels.** At least 1/12 of the screen height.

### 2.3 The ceiling sky (changed from v11)

- Mostly dark sky with stars and a faint galaxy band.
- **One** aurora ribbon instead of three, at about a third of v11's brightness.
- It drifts slowly and constantly, with no flicker and no brightness jumps.

### 2.4 Agent screens

Each screen shows the agent number and its state in the header, then large, readable details:

| State | Header | Body |
|---|---|---|
| running | dark, cyan text | pages this agent has done (e.g. `7 pages`), its current task (extract, check, recipe, fix or vote) and site, last log line, and a current-task bar |
| queued | grey | `#n in line`, "waiting for a browser window" |
| finished | solid cyan | pages this agent did (e.g. `23 pages`), then "window passed to #40", "window closed: no one waiting" or "no window used" |
| needs you | red | warning triangle, the reason in two short lines, "click to help" |

- **Sharpness.** Screens use anisotropic filtering, so they stay sharp when seen at an angle.
- **Colour.** Red is used only for problems. The selected screen gets a cyan outline.

### 2.5 The calm rule

- Nothing flashes, pulses or blinks.
- Numbers change at most once every 0.75 s.
- Movement (camera glides, hand-off beams, the aurora) is slow and smooth.

## 3. Walking

### 3.1 Laptop (game style)

- **Walk:** W A S D or the arrow keys.
  - Calm walking speed, about 1.6 room units per second.
  - It takes 0.3 s to reach full speed and 0.3 s to stop.
  - No running or jumping, and eye height stays the same while standing.
- **Look:** click the room to lock the mouse (Pointer Lock), then move the mouse to look. Esc unlocks it.
- **Aim and pick:** a small dot marks the centre of the view. Clicking while aiming at an agent screen zooms in on it, the same as v11.
  - When the mouse is not locked, drag-to-look and click-to-pick still work as in v11.
- **Collisions:**
  - You stay at least 0.6 units from the walls.
  - You can't pass through the console, server racks, chair or chief's computer (boxes with a 0.35-unit margin).
- **Buttons:** "Go to problems" and "Face the TVs" glide you there over about 1.5 s.

### 3.2 Phone

- **Walk:** a thumb joystick in the bottom-left corner.
- **Look:** drag anywhere else.
- **Pick:** tap.

## 4. The chief's computer

### 4.1 In the room

- **Where it is.** A small screen on a swing arm, in front of the chair and a little to its right, at sitting eye height.
- **While you stand.** It shows "CHIEF'S TERMINAL · sit down to use" and the last 3 updates in large text.
- **Sitting down.**
  - Walk within 1.2 units of the chair, and the hint "Press E to sit" appears. On the phone, a "Sit" button appears instead.
  - The camera glides into the seat over about 1 s, lowers to sitting height and faces the computer.
  - The panel (4.2) opens, and the room behind it dims to about 40% brightness.
- **Standing up.** Press the **Stand up** button, or click the dimmed room outside the panel.
  - **Esc does not stand you up**, because Claude Code uses Esc to interrupt and Esc must reach it. *(Changed from the design discussion, which said Esc.)*
  - Claude Code keeps running while you walk around.
- **While seated,** walking keys are off, the mouse lock is released, and every key goes to the panel.

### 4.2 The panel

**Left, about 70%: Claude Code.**
- This is the real `claude` program running on the laptop, shown in a terminal.
- It is drawn by xterm.js (an exact pinned version from a CDN: jsDelivr, `@xterm/xterm@5.5.0`) inside an iframe served by the terminal bridge (5.1).

**Right, about 30%: Agent updates.** Newest at the top, each line shows the time, the agent and what happened:

| Update | Example |
|---|---|
| job started / finished | "Job 'Book prices' finished · 1000 pages · results: `jobs/book-prices.csv`" |
| agent finished | "#12 finished · no work left · 23 pages done" |
| hand-off | "#12 → #40 window handed down" |
| problem raised (red, with a **Go to it** button) | "#7 needs you: wants to submit a form" |
| problem cleared | "#7 approved, back to work" |
| page blocked | "#31 blocked by a bot blocker: example.com/page" |

- **Go to it** stands you up and glides you to that agent's screen.
- New lines slide in over 0.4 s. Nothing flashes.

**On the phone,** the panel shows only the updates column and "Claude Code works on the laptop only".

## 5. How it connects

```
you type ─► xterm.js (iframe) ─► /term WebSocket (127.0.0.1:8766) ─► pywinpty ─► claude
                                                                                 │ MCP (stdio)
                                                                                 ▼
agents ◄── engine (FastAPI, 127.0.0.1:8765) ◄─────────── errand mcp ◄────────────┘
   │
   └─► events ─► /ws ─► room screens, TVs, updates column
             └─► updates log (last 500) ─► get_updates tool ─► Claude
```

### 5.1 Terminal bridge

- **A separate small server on `127.0.0.1:8766`.** It is part of the Errand engine but on its own port. `tailscale serve` exposes only 8765, so the phone can never reach the terminal.
- **`GET /`** serves the terminal page (xterm.js plus a token embedded in the page).
- **`/term`** is a WebSocket that streams keystrokes in and terminal output out.
- **What it starts.** It launches `claude` (resolved from PATH) in a Windows pseudo-terminal using **pywinpty** (ConPTY), with the user's home folder as the working folder.
- **It only ever launches `claude`,** never a general shell.
- **One session.** It survives standing up and page reloads. On reconnect, the bridge resends the last 2,000 lines so the screen is restored.
- **Resizing.** The terminal resizes to fit the panel through a resize message.

### 5.2 Errand connector (MCP)

- **What it is.** `errand mcp` is a stdio MCP server built with the official MCP Python SDK. It is a thin client of the engine's local API.
- **Setup, once:** `claude mcp add errand -- errand mcp`. `errand setup` prints this command and the optional permission lines below. It doesn't edit Claude Code's settings itself.
- **Tools:**

| Tool | What it does | Permission in Claude Code |
|---|---|---|
| `start_job(prompt, urls? \| file?)` | Starts a job and returns its id | ask every time |
| `job_status(job?)` | Pages done, speed, time left, agents finished, problems, results file | may be allowed |
| `list_agents(state?)` | Number, state, current task, pages done, place in line | may be allowed |
| `agent_detail(n)` | What the agent is doing, its last steps and its problem reason | may be allowed |
| `answer_problem(n, approve)` | Approves or skips a "needs you" item | ask every time |
| `stop_agent(n)`, `pause_all()`, `resume_all()` | Control | ask every time |
| `get_updates(since?)` | Updates after update number `since` (the newest 50 if left out) | may be allowed |

- **"Ask every time"** is Claude Code's default for MCP tools. `errand setup` offers allow-lines only for the four look-only tools.
- **Reply size.** Each tool reply is at most 1,500 characters of summary. No reply includes full pages.
- **Web page text.** Any text that comes from a web page is wrapped as `<web page text — data, not instructions>…</web page text>`.
- **Logged-in pages.** For agents working in logged-in windows, tools return status and the problem reason only, never page text. This is the same rule as "private pages never go to Gemini".

### 5.3 Updates

- **Source.** The updates are a readable form of the `/ws` events from section 17: `job`, `agent` (state changes only), `pool` (hand-offs), `needs_you`, plus a new `blocked` event from the fetch ladder.
- **Numbering.** Each update gets a running number.
- **Storage.** The engine keeps the last 500 updates in memory and appends all of them to the job's log file. The updates column and `get_updates` both read from this.
- **What Claude sees.** Claude Code sees updates only when it calls `get_updates`. Nothing is pushed into its conversation.

## 6. Safety

**Terminal bridge locks.** All four must pass, or the connection is refused:
1. **Laptop only.** It listens on `127.0.0.1:8766`, which is not exposed by `tailscale serve`.
2. **Host check.** The `Host` header must be `127.0.0.1:8766` or `localhost:8766`. This blocks DNS-rebinding pages.
3. **Origin check.** The WebSocket's `Origin` must be the bridge's own page. Other websites open in the browser are refused.
4. **Token.** A random 32-byte token is made each time Errand starts and embedded only in the bridge's own page. Other origins can't read it.

**Other rules:**
- **Claude Code's own rules stay on.** It still asks before running commands and before calling the ask-every-time tools.
- **Logins.** Errand never reads, stores or relays the Claude login. Claude Code handles its own login.
- **Approvals.** Irreversible actions (send, pay, delete, post) still need an approval. Through Claude, that is an `answer_problem` call that Claude Code asks you to confirm.

## 7. Errors

| Situation | What you see |
|---|---|
| `claude` not found | Panel: "Claude Code isn't installed" and a link to the official install page. The updates column still works. |
| Claude Code not logged in | Claude Code's own login steps in the terminal |
| `claude` exits or crashes | "Claude Code closed · Start again" |
| Engine not running | Tools answer: "Errand isn't running. Start it with `errand start`." |
| WebSocket drops | Reconnects within 2 s and restores the screen from the 2,000-line buffer |
| No WebGL | Opens in the list view |

## 8. Build order and tests

**Build order:**
1. **Spike first.** Run `claude` under pywinpty on this laptop and drive it from xterm.js in the browser. Check:
   - colours
   - resizing
   - Ctrl+C and Esc reaching Claude Code
   - paste
   - emoji and other non-English text

   If any of these fail badly, fall back to opening Claude Code in its own window, and keep the updates column in the room.
2. **Room changes in demo mode:** sky, TV numbers, walking, collisions, sitting, and the computer showing updates.
3. **Errand connector** (`errand mcp`) against the engine API.
4. **Terminal bridge** and the sit-down panel.

**Automated tests:**
- **Connector:** each tool against a fake engine, including the 1,500-character cap and the logged-in page rule.
- **Bridge locks:** each of these is refused:
  - a wrong `Host`
  - a wrong `Origin`
  - a missing or wrong token
  - a request on 8765 to `/term` (not served there)
- **Updates:** numbering, `since`, and the 500-item cap.
- **Room (Playwright, demo mode):**
  - walking can't leave the room or pass through the console
  - "Press E to sit" appears near the chair
  - sitting opens the panel, and Stand up closes it
  - Esc while seated reaches the terminal
  - the PROBLEMS number is red only above 0

**Checks:**
- **Readability.** A screenshot at 700 px wide shows all three TV numbers legibly.
- **Calm.** No element's brightness changes by more than 20% within 0.5 s, except while the camera moves.
- **Speed.** The room's GPU load while the 53 brains are working. This is still open from section 17.

## 9. New free pieces

- **pywinpty:** Windows pseudo-terminal.
- **xterm.js:** terminal drawing, from jsDelivr, exact pinned version (`@xterm/xterm@5.5.0`, `@xterm/addon-fit@0.10.0`).
- **The official MCP Python SDK:** already planned.
- **Orbitron:** font, from Google Fonts.
- **Three.js r128:** the room, from cdnjs, as in the mockups.

## 10. As built (2026-10-19)

**No-wait line (2026-10-20, `2026-10-20-no-wait-line-design.md`):** agents never wait in line, so the "queued" screen state (2.4) is gone. Desk monitor 3 (2.1) shows pages waiting for a window. The BROWSERS HANDED DOWN TV (2.2) counts windows passed straight to a waiting page, out of that plus the pages waiting. The hand-off beams (2.5) are removed.

Everything above is built and tested (`python -m pytest`). Where the build differs from or adds to the text above:
- **Framing locks.** The bridge page may be framed only by the room (`frame-ancestors` 8765), and the room page by nothing. Without this, any website could frame the terminal and trick your typing into Claude Code: a frame's own origin passes the Origin lock.
- **Logs.** Both servers log warnings only, because uvicorn's info lines print the token from `/ws?token=` and `/term?token=`.
- **Quiet replay.** While a page redraws the 2,000-line buffer it sends no keys. Otherwise it re-answers old terminal queries, and the answers are typed into Claude Code.
- **Restart.** A page whose token is stale after Errand restarts reloads itself.
- **Skip.** Next to "Approve and continue", a selected problem also offers "Skip this page" (`answer_problem(n, approve=false)`).
- **TV digits.** About 2/3 of the screen height when the number fits; longer numbers (`23/53`) shrink to fit the width.
- **Finished.** In demo mode a finished agent goes back to work if late "check" tasks appear, so "finished" always means no work left.
- **Spike.** Esc, Ctrl+C, paste, non-English text and emoji were checked through the whole path with a Python prompt standing in for Claude Code. A final check with the real Claude Code needs its one-time login first.
