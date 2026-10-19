# Windows 11 laptop as a free, always-on home server for Errand (as of Oct 2026)

All pages accessed 2026-10-19. "Last updated" dates are the dates shown on the pages themselves. Hardware context: i5-10500H, 16 GB RAM, RTX 3060 6 GB, Windows 11 Home.

## 1. Reaching the laptop securely from a phone (Cloudflare Tunnel, Tailscale, ngrok)

### Takeaway
Tailscale's free Personal plan is the best fit: free forever, non-commercial personal use is explicitly allowed, it is a private network (nothing public to attack), and no metered bandwidth caps were found. Cloudflare Quick Tunnels need no account but do not support SSE and cap in-flight requests at 200. ngrok free is too small for a live view (1 GB/month out).

### Cited Findings
**Cloudflare Tunnel / Quick Tunnels**
- Quick Tunnels "create a temporary URL for a local service without a Cloudflare account". The same page description says access can be restricted "with email one-time PINs". Page last updated Sep 30, 2026. — [Cloudflare Docs: Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- Quick Tunnel limits: "Each Quick Tunnel supports up to 200 in-flight requests. Additional requests return a 429 response." and "Quick Tunnels do not support Server-Sent Events (SSE)." — [Cloudflare Docs: Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- Cloudflare Tunnel (named tunnels) is "Available on all plans", uses an "outbound-only, post-quantum encrypted connection", and supports "HTTP, HTTPS, TCP, SSH, RDP, and more". Page last updated Sep 11, 2026. — [Cloudflare Docs: Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/)
- Terms risk for live video: Cloudflare's CDN service-specific terms say non-Enterprise customers must use paid services (e.g. Stream, Images, Developer Platform) "to serve video and other large files via the CDN". Cloudflare may limit access if the CDN is used "to serve video or a disproportionate percentage of pictures, audio files, or other large files". — [Cloudflare Service-Specific Terms](https://www.cloudflare.com/service-specific-terms-application-services/)

**Tailscale**
- Personal plan: "$0 Free forever", "Unlimited user devices", "Up to 6 users", "Up to 3 ACL groups", "Up to 50 tagged resources to start", "1,000 mins per month for ephemeral resources". — [Tailscale pricing](https://tailscale.com/pricing)
- Terms of use: "Personal users have access to the free tier plan for non-commercial use, which will be free forever". The plan is "for individuals who want to use Tailscale at home… only suitable for non-commercial use", with examples like "building a homelab or home VPN". — [Tailscale pricing](https://tailscale.com/pricing)

**ngrok (Free plan)**
- Usage limits: data transfer out "1 GB / month"; HTTP requests "20,000 / month"; TCP connections "5,000 / month"; OAuth/OIDC traffic identities "3 / month". — [ngrok docs: Free Plan Limits](https://ngrok.com/docs/pricing-limits/free-plan-limits)
- Resource limits: up to 3 online endpoints, 3 concurrent agents, 1 development domain (e.g. `your-assigned-name.ngrok-free.app`), 5 traffic-policy rules, TLS endpoints "Not available". — [ngrok docs: Free Plan Limits](https://ngrok.com/docs/pricing-limits/free-plan-limits)
- An interstitial warning page appears "in front of all HTML browser traffic on the free tier". Clicking Visit sets a cookie that hides it for 7 days. API and programmatic traffic is not affected. — [ngrok docs: Free Plan Limits](https://ngrok.com/docs/pricing-limits/free-plan-limits)

### Inferences
- Tailscale gives the phone a direct private network path to the laptop, so the Errand web UI, WebSockets, and SSE should work like they do on a LAN, and the Cloudflare CDN video clause does not apply. Recommended default: install Tailscale on the laptop and phone, bind the Errand UI to the tailnet interface only, and add an app-level login as a second layer.
- A live view uses a lot of data. For example, 50 KB JPEG frames at 5 fps is about 250 KB/s, or roughly 0.9 GB per hour. That would use up ngrok's 1 GB/month free allowance in about an hour, so ngrok free is only good for occasional webhook testing.
- On a Quick Tunnel, Errand should use WebSockets or polling for live updates, not SSE. Streaming a browser screencast through Cloudflare's CDN is a gray area under the video/large-files clause, so Tailscale is the safer route for the live view.
- Use only one account per provider, and only for personal, non-commercial use. This matches Tailscale's stated intent.

### Gaps
- No page I read said whether Tailscale or ngrok sign-up requires a credit card. My expectation is that neither does, but I did not verify it.
- I did not check whether Quick Tunnels support WebSockets. The page only names the SSE limitation.
- I did not verify this session that a named Cloudflare Tunnel with a public hostname requires a domain (zone) on Cloudflare. If it does, that domain costs money, which breaks the $0 rule. I also did not check how many free Cloudflare Access/Zero Trust seats there are.
- I did not check whether Tailscale has a bandwidth or relay (DERP) cap, or what Funnel's free-plan limits are.
- Quick Tunnel URLs are believed to be random and to change on every restart (prior knowledge, not re-verified).

## 2. Live view and human takeover of a running Chromium

### Takeaway
The simplest option for one user on Windows is the Chrome DevTools Protocol (CDP) screencast. Errand calls `Page.startScreencast`, sends the JPEG frames over a WebSocket to a phone web page, and turns taps and keys from the phone back into CDP input events. This works with Playwright-launched Chromium and needs no VNC stack.

### Cited Findings
- `Page.startScreencast` and `Page.stopScreencast` are marked experimental ("exp"). Parameters: `format` ("Image compression format"), `quality`, `maxWidth`, `maxHeight`, `everyNthFrame` ("Send every n-th frame"), and `maxFramesInFlight` ("Maximum number of frames sent until screencastFrameAck is required. Defaults to 3."). — [Chrome DevTools Protocol: Page domain](https://chromedevtools.github.io/devtools-protocol/tot/Page/)

### Inferences
- How it would work: Playwright (Python) opens a CDP session on the page. Errand calls `Page.startScreencast` (format jpeg, quality around 50–70, maxWidth around 1024) and receives `Page.screencastFrame` events. Each frame must be acknowledged with `Page.screencastFrameAck`, which also limits the frame rate. Frames go to the phone over a WebSocket. To take over, the phone sends taps and keys, and Errand replays them with CDP `Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`, and `Input.insertText`, or with Playwright's `page.mouse` and `page.keyboard`. This method comes from prior knowledge of the CDP Input domain and Playwright's `new_cdp_session`; I did not re-fetch those docs this session.
- Because the screencast is experimental, Chrome updates could change it. Pin the Playwright/Chromium version and fall back to periodic `page.screenshot()` polling if it breaks.
- noVNC/x11vnc is a Linux/X11 stack. On Windows you would need a separate VNC server plus a websockify proxy. That is more moving parts, and it exposes the whole desktop rather than one browser, so it is not the simplest choice for one user.
- The screencast works for headless browsers too. That matters when jobs run while the user is logged off (see section 3).

### Gaps
- I did not fetch the full CDP docs for the `screencastFrame` event fields or the `Input` domain, so parameter details beyond those quoted are unverified.
- I did not check whether Playwright 2026 has a built-in "live view" or trace-streaming feature.
- I did not check whether Scrapling's stealth browser exposes a CDP session the same way Playwright does.

## 3. Running scheduled jobs on Windows at $0 and keeping the laptop awake

### Takeaway
Use Windows Task Scheduler to start (or wake for) the Errand engine, and a Python in-process scheduler for job timing while the engine is running. Task Scheduler can wake a sleeping PC (`WakeToRun`). The hard limit is that the laptop must be powered, plugged in, and not shut down or hibernated past what wake timers can handle.

### Cited Findings
- `WakeToRun`: "If True… the Task Scheduler will wake the computer when it is time to run the task." Also: "the screen may remain off even though the computer is no longer in the sleep or hibernate mode". It is stored in the task XML as the `WakeToRun` element. Supported from Windows Vista onward. Page last updated 12/11/2020. — [Microsoft Learn: TaskSettings.WakeToRun](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-waketorun)

### Inferences
- Practical setup:
  - Task Scheduler starts the Errand engine at logon (or on a schedule) with "Wake the computer to run this task" checked.
  - Inside the engine, a Python scheduler (e.g. APScheduler with a SQLite job store) runs the daily/hourly jobs, so schedules live in one place.
  - The power plan is set to "never sleep when plugged in". Lid-close action is "Do nothing" if the laptop runs closed.
- "Run whether user is logged on or not" runs the task in a non-interactive session. A visible (headed) Chromium window would not be visible there. Headless plus the CDP screencast still works, and is the better fit for runs while the user is away.
- Laptop limits: it must be plugged in, and thermals and battery wear matter when it runs 24/7. Windows Update restarts can kill long runs. Wake timers are less reliable on Modern Standby (S0) laptops than on classic S3 sleep. Errand should catch up on missed runs at startup (APScheduler has `misfire_grace_time` / coalesce options).

### Gaps
- I did not verify this session that the "Allow wake timers" power setting must be enabled on battery and AC, or how Windows 11 Modern Standby handles `WakeToRun`.
- I did not fetch APScheduler docs, so its current version and misfire options in 2026 are unconfirmed.
- I did not check Windows Update "active hours" or restart-deferral settings.

## 4. Receiving webhooks and triggers while the laptop may be offline (Cloudflare Workers free inbox)

### Takeaway
A Cloudflare Worker on the free plan can act as an always-on webhook inbox. It accepts the POST, stores the event in D1 (or a Durable Object's SQLite), and the laptop pulls new events when it comes online. Free limits are far beyond one person's needs. Avoid Queues as the main store, because free-plan messages expire after 24 hours.

### Cited Findings
- Workers Free: "100,000 per day" requests, "No charge for duration", "10 milliseconds of CPU time per invocation". Page last updated Oct 2, 2026. — [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- D1 on Workers Free: rows read "5 million / day", rows written "100,000 / day", storage "5 GB (total)". — [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- Durable Objects free plan: requests "100,000 / day" (this includes HTTP requests, RPC sessions, WebSocket messages, and alarm invocations), duration "13,000 GB-s / day". — [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- Workers KV is included in the Free plan: keys read "100,000 / day", keys written "1,000 / day", keys deleted "1,000 / day", list requests "1,000 / day", stored data "1 GB". Page last updated Apr 21, 2026. — [Cloudflare KV Pricing](https://developers.cloudflare.com/kv/platform/pricing/)
- Queues on Workers Free: "10,000 operations/day included", with message retention of "24 hours (non-configurable)". One operation is counted per 64 KB written, read, or deleted, and "it takes 3 operations to deliver a message". Page last updated Apr 21, 2026. — [Cloudflare Queues Pricing](https://developers.cloudflare.com/queues/platform/pricing/)
- Cloudflare's Workers page reportedly says "no credit card required". — [flaviocopes.com hosting free tiers, checked Sep 16, 2026](https://flaviocopes.com/hosting-free-tiers/) (secondary source quoting Cloudflare)

### Inferences
- Rough capacity:
  - Queues: about 3,333 messages/day (10,000 ÷ 3).
  - KV: about 1,000 new events/day (write cap).
  - D1: about 100,000 rows/day.
  - Polling cost: a laptop checking every minute uses about 1,440 Worker requests/day, well under 100,000.
- D1 (or Durable Object SQLite) is the best inbox store. Events stay until the laptop deletes them, so an offline weekend does not lose triggers. Queues' fixed 24-hour retention would lose them.
- Suggested design: `POST /hook/<job>` checks a per-job secret or HMAC and inserts a row. The laptop calls `GET /events?since=<id>` with a bearer token, then acks with a delete. Alternatively, the laptop holds a WebSocket to a Durable Object for instant push while online. This needs no tunnel for triggers at all.
- The 10 ms CPU limit is fine for validate-and-insert. Do not do LLM or browser work in the Worker; that runs on the laptop.

### Gaps
- I did not verify this session the Cron Trigger allowance on Workers Free or the free-plan Worker count and script-size limits.
- I did not check whether Queues' HTTP pull-consumer API is available on the free plan.
- I did not confirm on Cloudflare's own page that sign-up needs no card (only a secondary source).

## 5. Free always-on compute for a 24/7 personal service without a card (2026)

### Takeaway
I found no legitimate, card-free, always-on general-purpose server (a VM or container) in 2026. Card-free options either sleep when idle (Render), give token credit (Railway's $1/month), or are serverless and event-driven (Cloudflare Workers). Errand should treat the laptop as the compute host and Cloudflare Workers as the only always-on piece.

### Cited Findings
- All findings in this section come from one secondary comparison, which says every number was checked on September 16, 2026 against provider pricing pages (page modified 2026-10-16). — [flaviocopes.com: Every hosting provider's free tier](https://flaviocopes.com/hosting-free-tiers/). Its findings:
  - **Render:** free web services get 512 MB RAM and "less than one CPU" from 750 instance hours/month per workspace. They "sleep after 15 idle minutes and take a minute to wake", and the filesystem is ephemeral. Render's docs say "Do not use them for production applications." No payment method is needed; Render suspends services when bandwidth runs out instead of billing.
  - **Railway:** a $5 trial credit for 30 days, then $1 credit a month, which "keeps about 100 MB of RAM alive for a month".
  - **Fly.io:** no free allowance any more. The trial is 2 hours of machine runtime or 7 days, and "all organizations require a credit card on file".
  - **Cards required:** a card or payment method is needed up front for AWS, Google Cloud, Azure, Fly.io after the trial, "and every VPS provider".

### Inferences
- Oracle Cloud Always Free and Google Cloud's e2-micro offer real always-on VMs but need a card to verify identity, so they fail the "ideally no card" goal. They are also too small to run Chromium plus a local LLM.
- No free host has a GPU, so the local LLM must stay on the laptop's RTX 3060 in any case.
- Do not keep a sleeping free service (like Render) awake with pinger hacks. That works against the provider's intent, and the user asked to respect every provider's terms.

### Gaps
- I did not read Oracle's or Google's own pages this session, so their card requirements come from prior knowledge plus the secondary source's "every VPS provider" claim.
- I did not check Hugging Face Spaces, Koyeb, or Deno Deploy for current idle/sleep rules and card requirements.
- I did not check whether GitHub Actions scheduled workflows are acceptable for personal automation under GitHub's terms.
