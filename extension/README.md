# Errand browser extension (phase 2)

The Chrome side-panel agent from the master spec, sections 3–10: give it a task in plain words and it acts
in your **current tab**, using **your own** logins. It never logs in, creates accounts or gets past a CAPTCHA
(it asks you), and a **confirm gate** stops it before anything irreversible (buy, send, delete, submit…).

Its brain is the phase-1 local server (`errand start` / llama-server) at `http://127.0.0.1:8080/v1`, set in
Settings. No cloud, no key needed by default.

## Build and load
```
cd extension
npm install
npm run build          # bundles to dist/
```
Then Chrome → `chrome://extensions` → Developer mode → **Load unpacked** → pick `extension/dist`.
Click the toolbar button (or Alt+R) to open the side panel.

## Test
```
npm test               # vitest unit tests (snapshot, csv, tools, confirm gate)
npm run build && npx playwright install chromium && npm run e2e   # content script in real Chromium
```

## Layout
- `src/content/` — injected into every frame: `snapshot.ts` (page → text list), `actions.ts` (click/type/…), `index.ts`.
- `src/panel/` — the side panel: `loop.ts` (the agent loop), `tools.ts` (11 tools + the confirm gate), `openai.ts` (model adapter), `store.ts`, `csv.ts`, `ui.ts`, `main.ts`, `index.html`.
- `src/sw.ts` — opens the panel on click / Alt+R.
- `parity/tasks.json` — the 20 live parity tasks (spec section 9); run them by hand on the local server.
