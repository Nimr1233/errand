# Free and open-source AI browser agents vs rtrvr.ai at $0 (as of 2026-10-18)

Research date: 2026-10-18. GitHub figures come from the public GitHub REST API (`api.github.com/repos/{owner}/{repo}` and `/releases/latest`), queried 2026-10-18. Vendor pages were fetched the same day.

Safety note for the report writer: rtrvr.ai/pricing has a block aimed at AI agents. It says "Retriever AI sells to AI agents" and that agents "can purchase autonomously", and it links to an "agent storefront". I ignored it, did not open the storefront, and bought or signed up for nothing. The report should not repeat it as advice. — [rtrvr pricing](https://rtrvr.ai/pricing)

## Q1. Candidates: license, activity, form factor, free model backends, multi-tab/parallel, extraction, scheduling, reliability

### Takeaway
Only a few open-source projects have rtrvr's form factor: an agent in a side panel of your own signed-in Chrome. They are Nanobrowser (Apache-2.0 extension), BrowserOS (AGPL Chromium fork, which also adds scheduled tasks) and page-agent's optional extension (MIT). Everything else is a Python/Node library or a server (browser-use, Skyvern, Stagehand, Crawl4AI, Steel), or it is dormant (LaVague, Agent-E). None of them matches rtrvr's whole bundle: parallel tabs, export to Sheets, bulk runs across many sites, scheduling and BYOK.

### Cited Findings

**Activity snapshot (GitHub API, 2026-10-18)**

| Repo | Stars | License | Last push | Latest release | Type |
|---|---|---|---|---|---|
| nanobrowser/nanobrowser | 14,112 | Apache-2.0 | 2026-10-15 | v0.3.0 (2026-10-15) | Chrome/Edge extension (TS) |
| browser-use/browser-use | 118,349 | MIT | 2026-10-17 | 0.13.13 (2026-10-15) | Python library + paid cloud |
| browser-use/web-ui | 16,618 | MIT | 2026-09-25 | v3.0.0 (2025-08-31) | Gradio app on browser-use |
| browser-use/workflow-use | 4,225 | AGPL-3.0 | 2026-10-16 | v0.2.11 (2025-11-19) | Python workflows ("RPA 2.0") |
| Skyvern-AI/skyvern | 23,223 | AGPL-3.0 | 2026-10-18 | v1.0.56 (2026-10-14) | Python server/library + cloud |
| browserbase/stagehand | 25,720 | MIT | 2026-10-17 | 3.7.3 (2026-08-28) | TS SDK (+Python/Go), Browserbase cloud |
| lavague-ai/LaVague | 6,390 | Apache-2.0 | 2025-01-21 | none | Python (dormant ~21 months) |
| EmergenceAI/Agent-E | 1,252 | MIT | 2026-05-04 | none | Python; repo now points to a paid Emergence API |
| FoundationAgents/OpenManus | 58,703 | MIT | 2026-09-30 | v0.3.0 (2025-04-10) | Python general agent |
| OpenHands/OpenHands (moved from All-Hands-AI) | 91,157 | MIT | 2026-10-17 | v1.27.1 (2026-10-12) | AI coding agent |
| steel-dev/steel-browser | 7,830 | Apache-2.0 | 2026-10-13 | v0.5.4-beta (2026-08-25) | Self-hostable browser API/sandbox (no agent brain) |
| unclecode/crawl4ai | 85,732 | Apache-2.0 | 2026-10-15 | v0.9.5 (2026-10-14) | Python crawler/extractor + Cloud |
| alibaba/page-agent | 29,473 | MIT | 2026-10-17 | v1.12.4 (2026-09-06) | In-page JS agent + optional Chrome extension + beta MCP |
| browseros-ai/BrowserOS | 13,974 | AGPL-3.0 | 2026-10-16 | browserclaw/v0.51.1.2 (2026-10-13) | Chromium fork with built-in agent |
| web-infra-dev/midscene | 15,312 | MIT | 2026-10-16 | v1.16.0 (2026-10-16) | Vision-driven UI automation/testing (TS) |
| magnitudedev/browser-agent | 4,134 | Apache-2.0 | 2026-02-08 | magnitude-core@0.3.1 (2026-02-08) | Vision-first TS agent (slowing) |
| nottelabs/notte | 2,040 | NOASSERTION | 2026-10-18 | v1.9.7 (2026-10-14) | Cloud browser platform + SDK |
| vibesurf-ai/VibeSurf | 483 | NOASSERTION | 2026-02-14 | 0.5.18 (2026-01-17) | Browser assistant (small, slowing) |
| microsoft/playwright-mcp | 38,297 | Apache-2.0 | 2026-10-16 | v0.0.83 (2026-09-28) | MCP server (tools only, no LLM) |
| ChromeDevTools/chrome-devtools-mcp | 53,746 | Apache-2.0 | 2026-10-18 | v1.11.0 (2026-10-15) | MCP server (tools only, no LLM) |
| hangwin/mcp-chrome | 12,498 | MIT | 2026-01-06 | v1.0.0 (2025-12-29) | Chrome-extension MCP server for your real browser |

Sources: [nanobrowser](https://github.com/nanobrowser/nanobrowser), [browser-use](https://github.com/browser-use/browser-use), [web-ui](https://github.com/browser-use/web-ui), [workflow-use](https://github.com/browser-use/workflow-use), [skyvern](https://github.com/Skyvern-AI/skyvern), [stagehand](https://github.com/browserbase/stagehand), [LaVague](https://github.com/lavague-ai/LaVague), [Agent-E](https://github.com/EmergenceAI/Agent-E), [OpenManus](https://github.com/FoundationAgents/OpenManus), [OpenHands](https://github.com/OpenHands/OpenHands), [steel-browser](https://github.com/steel-dev/steel-browser), [crawl4ai](https://github.com/unclecode/crawl4ai), [page-agent](https://github.com/alibaba/page-agent), [BrowserOS](https://github.com/browseros-ai/BrowserOS), [midscene](https://github.com/web-infra-dev/midscene), [magnitude](https://github.com/magnitudedev/browser-agent), [notte](https://github.com/nottelabs/notte), [VibeSurf](https://github.com/vibesurf-ai/VibeSurf), [playwright-mcp](https://github.com/microsoft/playwright-mcp), [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), [mcp-chrome](https://github.com/hangwin/mcp-chrome). All via the GitHub REST API on 2026-10-18.

**Nanobrowser (closest open-source match to rtrvr's form factor)**
- A Chrome extension (also runs in Edge) that lives in a side panel and works in your own logged-in browser. It reads pages, clicks, types and moves between tabs, and it asks before submitting, sending, deleting or uploading. — [Nanobrowser README](https://github.com/nanobrowser/nanobrowser)
- Providers: Anthropic, OpenAI, Gemini, OpenRouter, xAI, DeepSeek, Mistral and any OpenAI-compatible endpoint. Local options are Ollama and LM Studio, plus llama.cpp, vLLM and others through the OpenAI-compatible provider. "A model must support tool calling", and the settings screen can test whether a model works. Chrome built-in AI is not mentioned. — [Nanobrowser README](https://github.com/nanobrowser/nanobrowser)
- v0.3.0 (15 Oct 2026) was a full rebuild. One agent in the side panel replaces the old planner and navigator agents. Several tasks can run in parallel, each in its own tab group. The agent can save results as CSV or Markdown to Downloads. It has Ask and Auto permission modes and per-site Allow/Ask/Block. v0.2.0 (2 Oct) moved LLM calls from LangChain to the Vercel AI SDK, connected Ollama through its OpenAI-compatible API, and removed the Groq, Cerebras and Llama API providers. Neither release mentions scheduling or Google Sheets. — [Nanobrowser releases](https://github.com/nanobrowser/nanobrowser/releases)
- For local use the README recommends "Qwen3.8 27B" with at least 16k context, and adds that "Local models work best for simple, clear tasks." It gives no benchmarks. The extension is free with no subscription. — [Nanobrowser README](https://github.com/nanobrowser/nanobrowser)

**BrowserOS (Chromium fork; the only open-source option found with built-in scheduling)**
- Described as "A Chromium fork with an AI agent built into every new tab". It supports BYOK and says it can "run everything locally with Ollama". It is AGPL-3.0 and has an MCP server. A sister product, "neo", lets outside agents (Claude Code, Codex, Cursor) drive the browser, each agent in its own tab. Anonymous telemetry is on by default and can be turned off. — [BrowserOS README](https://github.com/browseros-ai/BrowserOS)
- Scheduled Tasks run Daily, Hourly (every 1–24 h) or every 1–60 minutes. "BrowserOS needs to be open for scheduled tasks to run." Tasks time out after 10 minutes, and each keeps its last 15 runs. Results stay on the device. — [BrowserOS Scheduled Tasks docs](https://docs.browseros.com/browseros/features/scheduled-tasks.md)
- The docs index has pages for BYO LLM, local models, ChatGPT Pro/Plus and GitHub Copilot sign-in, Scheduled Tasks, n8n integration and MCP clients. No page covers CSV or Sheets export. — [BrowserOS docs index](https://docs.browseros.com/llms.txt)

**page-agent (Alibaba)**
- An in-page JavaScript GUI agent: "Just in-page javascript. Everything happens in your web page." It works on the DOM as text: "No screenshots. No multi-modal LLMs". An optional Chrome extension extends it "across browser tabs", and an MCP server is in beta. The README says it is "designed for client-side web enhancement, not server-side automation." A free demo LLM endpoint exists but is "For technical evaluation only." The README mentions no scheduling and no structured-extraction feature. — [page-agent README](https://github.com/alibaba/page-agent)

**browser-use (+ web-ui, workflow-use)**
- MIT Python library. It can drive a local Chrome profile (`Browser.from_system_chrome()`) and run a local model through Ollama. Its recommended model, ChatBrowserUse/BU-2, and Browser Use Cloud are paid ("$0.02 per browser-hour plus network traffic"). Stealth, residential proxies, CAPTCHA solving, cloud profiles and the hosted agent API are cloud features. — [browser-use README](https://github.com/browser-use/browser-use)
- The docs have a parallel-agents example: each agent gets its own browser and they run under `asyncio.gather`. It is flagged experimental. Parallel sessions cannot share a `user_data_dir`, but they can share a `storage_state` file, or use one session with different tabs. — [browser-use docs: parallel browser](https://docs.browser-use.com/customize/examples/parallel-browser)
- web-ui is a Gradio app that can use your own Chrome (set `BROWSER_PATH`/`BROWSER_USER_DATA`). It supports "Google, OpenAI, Azure OpenAI, Anthropic, DeepSeek, Ollama etc." Its last changelog entry is from 2025-01-26 and it has 271 open issues. It does not mention parallel tasks or scheduling. — [web-ui README](https://github.com/browser-use/web-ui); latest release v3.0.0 dated 2025-08-31 per GitHub API.

**Skyvern**
- An AGPL-3.0 agent driven by a vision LLM. It supports Ollama, OpenRouter, Gemini and any OpenAI-compatible endpoint through LiteLLM. It can attach to your running Chrome (`BROWSER_TYPE=cdp-connect`). Workflows support loops, extraction with `data_extraction_schema`, file parsing, email and HTTP blocks. Anti-bot measures, proxies and CAPTCHA solvers are cloud-only, and the cloud is where parallel instances are offered. The README says nothing about scheduling. It reports WebBench at 64.4%, and a linked blog suggests WebVoyager at 85.8%. — [Skyvern README](https://github.com/Skyvern-AI/skyvern)

**Stagehand**
- An MIT SDK with `act`, `observe` and `extract`. `extract()` returns data validated against a schema (Zod, Pydantic or Go structs). Local runs need Chrome installed. The paid Browserbase cloud adds verified mode, residential proxies, persistent contexts, recordings and server-side caching. The README examples use OpenAI keys and do not say whether Ollama works. — [Stagehand README](https://github.com/browserbase/stagehand)

**Crawl4AI**
- Apache-2.0. `LLMExtractionStrategy` turns pages into typed JSON with any LiteLLM provider, including `ollama/...`. There is also LLM-free CSS/XPath/regex extraction: `generate_schema` writes a reusable schema once. `arun_many` crawls many URLs in parallel with a "memory-adaptive dispatcher". It supports persistent profiles, CDP and a Docker server with MCP. The library is free to self-host. The separate Crawl4AI Cloud gives 1,000 free credits a month (2 concurrent), with paid plans from $10/month. — [Crawl4AI README](https://github.com/unclecode/crawl4ai)

**Others**
- LaVague's last push was 2025-01-21 with no releases, so it is effectively dormant. Agent-E's repo description now sends users to a paid Emergence web-automation API. OpenManus's last release was v0.3.0 (2025-04-10). OpenHands is an "AI-Driven Development" (coding) agent. Steel is a "browser sandbox" API with no agent brain. — GitHub API metadata, see table sources above.
- Chrome built-in AI: the Prompt API runs Gemini Nano on-device, and extensions can use it. The model downloads separately on first use, and Google's Generative AI Prohibited Uses Policy applies. — [Chrome Prompt API docs](https://developer.chrome.com/docs/extensions/ai/prompt-api). I found no open-source browser agent that runs fully on Gemini Nano; see Gaps.
- Other 2026 extensions: proprietary products (OpenAI Codex for Chrome, launched May 7, 2026, and the ChatGPT Chrome extension, announced July 9, 2026) dominate 2026 search results. "Open Browser Control" is an MCP Chrome extension with no stated license. — [letsdatascience](https://letsdatascience.com/news/openai-launches-codex-chrome-extension-for-browsers-87cce1ce), [Chrome Web Store: Open Browser Control](https://chromewebstore.google.com/detail/icicfjcgocaakibmmaejmoipckofnnpl)

### Inferences
- Capability map against rtrvr (my synthesis of the findings above):
  - **Acts in your signed-in Chrome from a side panel:** Nanobrowser (yes), BrowserOS (yes, but as its own browser rather than Chrome), page-agent extension (yes, scoped to pages). Through CDP attach: browser-use, Skyvern, Crawl4AI.
  - **Multi-tab / parallel:** Nanobrowser runs parallel tasks in tab groups. browser-use has experimental `asyncio.gather` parallelism. Crawl4AI's `arun_many` handles bulk crawling. Skyvern keeps parallelism in its cloud.
  - **Extraction to table/CSV:** Nanobrowser saves CSV to Downloads. Crawl4AI, Stagehand and Skyvern do schema JSON, which the user converts to CSV. Nothing native exports to Google Sheets.
  - **Scheduling:** only BrowserOS (app must be open). Everything else needs OS cron/Task Scheduler or a `chrome.alarms` add-on.
  - **BYOK and local models:** almost all of them, with BYOK as the default.
- MCP servers (playwright-mcp, chrome-devtools-mcp, mcp-chrome) are tools, not agents. They only work at $0 if paired with a free LLM client.
- AGPL (Skyvern, BrowserOS, workflow-use) does not matter for personal use. It does matter if the user later distributes or hosts a derivative.

### Gaps
- I did not find independent, dated reliability benchmarks for Nanobrowser v0.3.0 or page-agent.
- I could not confirm whether Skyvern open-source or Stagehand local mode has a scheduler or CSV export.
- I did not check Chrome Web Store user counts or ratings.
- I found no open-source 2026 Chrome-extension agent beyond those listed. The search results were dominated by proprietary products, so newer small projects may exist.
- I did not dig into OpenManus or OpenHands browsing in depth, because both are general or coding agents, not tools for driving the user's own browser.

## Q2. Which candidates work fully at $0, and how well do they do with small or free models?

### Takeaway
Nanobrowser, BrowserOS, browser-use (local), web-ui, Skyvern (self-hosted), Crawl4AI and page-agent all run at $0 with Ollama/LM Studio or a free-tier API. But multi-step agent reliability drops sharply below roughly 20–30B parameters and needs 15k+ context. Free cloud tiers are tightly rate-limited: OpenRouter allows about 50 requests/day without a purchase, and Gemini's free Flash tiers are reported anywhere from 20 to 250+ requests/day. That makes "1,000 sites" impractical with a free cloud LLM unless most of the work avoids the LLM.

### Cited Findings
- Nanobrowser: "Local models work best for simple, clear tasks". Recommended local model: Qwen3.8 27B with ≥16k context. Models must support tool calling. — [Nanobrowser README](https://github.com/nanobrowser/nanobrowser)
- BrowserOS: "Ollama defaults to 4,096 tokens of context — this is too low for BrowserOS." The docs recommend 15–20k. Below 15k the agent can get stuck in a recovery loop and only Chat Mode works reliably. Their tiers: lightweight (qwen3-4b, ministral-3-3b) for simple chat only; mid-range (gpt-oss-20b, magistral-small) at 16+ GB RAM; heavy (gpt-oss-120b, ~63 GB) as "closest to cloud model quality". — [BrowserOS local models docs](https://docs.browseros.com/features/local-models)
- browser-use with Ollama: one third-party guide (Sept 2026) reports that an 8B model handles simple lookups but struggles with multi-step tasks, with reliability around the 30B tier. This is the article's claim and I did not verify it. — [LocalAimaster](https://localaimaster.com/blog/browser-use-ollama-local). The README says local Ollama is "subject to your hardware and model requirements." — [browser-use README](https://github.com/browser-use/browser-use)
- Open-weight web-agent benchmarks, as reported in a 2026 paper's table:
  - MolmoWeb-8B: WebVoyager 78.2, Online-Mind2Web 35.3, WebTailBench 49.5
  - Fara-7B: 73.5, 34.1, 38.4
  - UI-TARS-1.5-7B: 66.4, 31.3, 19.5
  - GPT-5: 90.6 on WebVoyager
  - — [RMSWeb, arXiv 2608.00335](https://arxiv.org/pdf/2608.00335); MolmoWeb is described as open-weight in 4B/8B sizes — [MolmoWeb, arXiv 2604.08516](https://arxiv.org/pdf/2604.08516)
- WebVoyager overstates progress. One study found that a simple agent using Google Search solved up to 51% of its tasks. Online-Mind2Web (300 tasks, 136 sites) is harder. — [An Illusion of Progress?, arXiv 2504.01382](https://arxiv.org/html/2504.01382v4)
- OpenRouter free models: 20 requests/minute. 50 requests/day for accounts with under $10 in lifetime purchases, 1,000/day after $10 has been bought. Limits apply per account, not per key. These are secondary sources (Aug–Oct 2026). — [TrueFoundry (2026-10-07)](https://www.truefoundry.com/es/blog/openrouter-rate-limits-your-free-tier-depends-on-what-youve-already-paid), [benchlm](https://benchlm.ai/md/free-tier/openrouter.md)
- Gemini API free tier: figures conflict across 2026 third-party sources. Reports range from ~20 requests/day for 3.x Flash models to ~500 for Flash-Lite, and from 100 to 1,500/day in earlier 2026 guides. Pro models reportedly have no free tier, and limits apply per project. None of these is Google's official table. — [agentdeals (Apr 2026)](https://agentdeals.dev/gemini-api-pricing-changes), [yingtu.ai](https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026)
- Paid-cloud dependencies:
  - Skyvern keeps anti-bot, proxies, CAPTCHA and parallel instances in the cloud — [Skyvern README](https://github.com/Skyvern-AI/skyvern)
  - browser-use keeps stealth, proxies, CAPTCHA, the hosted API and its BU-2 model in the cloud — [browser-use README](https://github.com/browser-use/browser-use)
  - Stagehand's proxies, verified mode and caching need Browserbase — [Stagehand README](https://github.com/browserbase/stagehand)
  - page-agent's free demo LLM is evaluation-only — [page-agent README](https://github.com/alibaba/page-agent)

### Inferences
- A truly free setup needs one of two things:
  - A local GPU or Apple-silicon machine able to run a ~20–30B tool-calling model with 16k+ context.
  - Free-tier API keys used for short interactive tasks only.
- On a typical laptop with 8–16 GB RAM, only 3–8B models fit. Expect simple single-site tasks to work and multi-step or cross-site tasks to fail often.
- Rough arithmetic, assuming ~10 LLM calls per site: 1,000 sites ≈ 10,000 calls.
  - OpenRouter free at 50/day: about 200 days.
  - OpenRouter at 1,000/day: about 10 days, but that requires buying $10, which breaks the $0 rule.
  - Gemini free Flash at an assumed ~250/day: about 40 days.
  - Free cloud LLMs are therefore not viable for bulk agent loops. LLM-free extraction (Crawl4AI `generate_schema` once, then CSS/XPath for every site) or a local model is required.

### Gaps
- I found no dated, controlled benchmark of Nanobrowser, BrowserOS or browser-use using specific small local models (e.g. Qwen3 8B vs 30B).
- I found no official Google table of current Gemini free-tier limits. Third-party figures conflict.
- I could not verify the current OpenRouter limits against OpenRouter's own docs.

## Q3. rtrvr.ai's own Free Mode: what it includes, limits, models, data and ad tradeoffs; is it the cheapest path?

### Takeaway
rtrvr's Free plan costs $0 and is ad-supported. AI inference and cloud browser time cost 0 credits on a set of designated "free models", subject to a daily fair-use allowance whose size is not published. Schedules, triggers, cookie sync and API/MCP control of rtrvr's agent require a paid plan, starting at $9.99/month. So rtrvr Free is the cheapest and easiest way to get rtrvr's interactive capabilities (side panel, multi-tab, extraction), but not scheduling or programmatic bulk runs. The price is sponsored cards, and on the cloud platform only, some sharing of personal data with an ad partner that you can opt out of.

### Cited Findings
- Plans: Free $0 (100 one-time welcome credits, no card). Starter $9.99/month (1,000 credits). Pro $29.99 (3,000). Team $99.99 (10,000, Private Mode). Scale $499.99 (50,000). One credit = one cent. Unused credits do not roll over. — [rtrvr pricing](https://rtrvr.ai/pricing)
- What Free Mode includes: "supported AI models and Cloud browser time for tasks you start in the extension or Cloud dashboard. No AI API key or paid AI subscription is required. Sponsored cards and a daily fair-use allowance apply." The allowance renews and is "ongoing, not a trial". The account page shows the current amount and reset time; no number is published. — [rtrvr pricing](https://rtrvr.ai/pricing)
- What needs a paid plan: "Schedules, triggers, cookie sync, and running rtrvr's agent in your Chrome through API or MCP require a paid plan." Free: "Browser tools that let your own AI drive your Chrome over MCP are free." API and WhatsApp runs, data enrichment (0.25 credits/record) and managed proxies (~500 credits/GB) use credits. — [rtrvr pricing](https://rtrvr.ai/pricing)
- BYOK: "Using your own AI provider avoids model-credit charges and the Free Mode allowance… Sponsored cards still appear on the free plan." BYOK options are a ChatGPT or Claude plan, an API key, or "a compatible local model". — [rtrvr pricing](https://rtrvr.ai/pricing)
- Free Mode models listed on the models page (2026-10-18): DeepSeek Flash, Gemini Flash Lite, GPT-6 Luna, Inkling Small, MiMo V2.6 Flash, GLM 5.3 Flash. Paid per-task credit rates range from 0.03 (GPT-6 Luna) to 0.60 (GPT-6.1 Sol). — [rtrvr models](https://rtrvr.ai/models)
- The Terms (Section 6, Free Mode) give zero-credit inference "on the free models we designate from time to time". "On the free plan, Free Mode is how tasks run: every task is ad-supported." Sponsored cards are "supplied by third-party advertising partners, matched contextually to your agentic interaction." Free Mode is acknowledged before the first task. It does not apply to Private Mode tasks. — [rtrvr Terms](https://rtrvr.ai/terms)
- Privacy:
  - "Sponsored content is contextual, not personalized… we do not build advertising profiles or use your browsing history for ad targeting."
  - "we and our advertising partners may process an excerpt of your agentic interaction together with platform, device, and privacy-compliance signals."
  - On the cloud platform only, "limited personal information associated with your account" may be shared with an ad partner. Turn this off under Settings → Sponsored cards, or with Global Privacy Control.
  - "the browser extension never shares account information."
  - In the EEA/UK, ads stay contextual only.
  - — [rtrvr Privacy Notice](https://rtrvr.ai/privacy)
- Vendor claims: "81.4% Web Bench · #1" and "7M+ knowledge-work runs", sold to AI labs as "Data & Evals" (offline policy data from those runs). — [rtrvr pricing](https://rtrvr.ai/pricing). The privacy excerpt I retrieved does not say whether Free Mode run data feeds that dataset.
- An rtrvr newsletter (v27; a search summary dates it January 2026) promotes adding several Gemini API keys and auto-rotating them. It says keys from different Google accounts give "basically unlimited free usage". — [rtrvr newsletter](https://www.rtrvr.ai/newsletters/live-cloud-browser-viewing). Free-tier quotas are enforced per project/account, and using several accounts to get around limits may conflict with Google's terms (not verified).
- Conflicting third-party figures for older free tiers: "100 Free Credits Per Month" vs "250 monthly credits", probably from different dates. The current pricing page describes Free Mode plus 100 one-time welcome credits instead. — summarized by search over [creati.ai](https://creati.ai/ai-tools/rtrvr-ai/) and [rtrvr newsletters](https://www.rtrvr.ai/newsletters)

### Inferences
- For a user who wants rtrvr's interactive capabilities at $0, rtrvr Free Mode is the cheapest path in time and money. It needs no GPU and no keys, and it uses competitive "flash" models, better than what most laptops can run locally.
- The costs are ads; an unpublished, variable daily cap; data excerpts processed by ad partners; and no scheduling, triggers or API/MCP control of its agent.
- rtrvr's free MCP "browser tools", driven by the user's own AI, are a second $0 route if the user already has a free LLM client.
- For recurring jobs at $0, BrowserOS (local scheduling) or an open-source tool plus OS Task Scheduler fills the gap rtrvr Free leaves.

### Gaps
- The numeric size of the Free Mode daily allowance is not published; the account page shows it.
- I found no published parallel-tab limit for Free Mode.
- I could not confirm whether Free Mode task data is used to build rtrvr's "Data & Evals" training/eval sets. The retrieved privacy text does not say.
- I found no independent, dated review that measured Free Mode limits. Search results were vendor pages, AppSumo and affiliate-style listings.
- The rtrvr blog post at /blog/free-browser-agent returned the same Free Mode text as the pricing page. I could not see a publication date.

## Q4. Best open-source base for "1,000 sites, one prompt" plus parallel agents; effort vs building from scratch; overall build/extend/use decision

### Takeaway
Don't build from scratch. For the rtrvr-style Chrome side-panel experience, extend Nanobrowser (Apache-2.0, active, already has parallel tab-group tasks, CSV export and Ollama/OpenRouter/Gemini). For bulk "1,000 sites" jobs, pair it with Crawl4AI or browser-use running headless. Crawl4AI's `arun_many` plus generate-schema-once extraction is the only approach that is realistic at $0 at that scale. Simplest of all: use rtrvr Free Mode for interactive work and BrowserOS for scheduled work, and build nothing.

### Cited Findings
- Nanobrowser already has: a side panel in the user's own browser, parallel tasks each in its own tab group, CSV/Markdown save to Downloads, permission modes, and Ollama/LM Studio/OpenRouter/Gemini/OpenAI-compatible providers through the Vercel AI SDK (since v0.2.0). It is Apache-2.0 and released 2026-10-15. — [Nanobrowser releases](https://github.com/nanobrowser/nanobrowser/releases), [README](https://github.com/nanobrowser/nanobrowser)
- Crawl4AI already has: `arun_many` with a memory-adaptive dispatcher, `generate_schema` to "describe what you want once", LLM-free CSS/XPath extraction, LiteLLM/Ollama extraction, and persistent profiles/CDP. It is Apache-2.0 and released 2026-10-14. — [Crawl4AI README](https://github.com/unclecode/crawl4ai)
- browser-use parallelism is experimental: separate browsers via `asyncio.gather`, and they cannot share one `user_data_dir`. — [browser-use docs](https://docs.browser-use.com/customize/examples/parallel-browser)
- BrowserOS already has local scheduling (daily/hourly/minutes, 10-minute timeout, app must be open) and BYOK/Ollama. It is AGPL-3.0. — [BrowserOS scheduled tasks](https://docs.browseros.com/browseros/features/scheduled-tasks.md), [BrowserOS README](https://github.com/browseros-ai/BrowserOS)
- Skyvern has workflows with loops and schema extraction, but parallel instances are a cloud feature and its license is AGPL. — [Skyvern README](https://github.com/Skyvern-AI/skyvern)
- page-agent says it is "not server-side automation", which makes it a poor fit for bulk jobs. — [page-agent README](https://github.com/alibaba/page-agent)

### Inferences (effort estimates are my judgment, not sourced)
- **What Nanobrowser lacks for "1,000 sites, one prompt":**
  - A job runner: take a URL list or CSV, fan out N tab groups with a concurrency cap, retry and checkpoint.
  - Fixed-schema extraction, so every site returns the same columns.
  - Merging results into one table, plus Google Sheets export. Sheets can be skipped by importing the CSV, which costs nothing.
  - Scheduling via `chrome.alarms`.
  - Rough effort: an experienced TypeScript/extension developer could build a working fork in about 1–3 weeks. A from-scratch Chrome agent with comparable reliability (DOM indexing, real input events, tab-group management, provider layer, permissions) would likely take 2–4+ months.
- **What really blocks $0 at 1,000 sites is the LLM budget, not the code.** An agent loop on every site multiplies LLM calls, and free tiers allow only about 50–250 calls/day. The practical $0 design:
  - The LLM plans and writes or validates an extraction schema once per site template.
  - A deterministic crawler (Crawl4AI) runs it in parallel.
  - The LLM agent is used only for sites that need interaction.
  - This is a small Python glue script around Crawl4AI, plus browser-use for the interactive leftovers: days of work, not weeks.
- **Decision ladder, cheapest effort first:**
  - (a) Use rtrvr Free Mode for interactive tasks and accept ads and caps.
  - (b) Use Nanobrowser (no ads, BYOK or local) and BrowserOS scheduling. Add Windows Task Scheduler plus a Crawl4AI script for bulk runs.
  - (c) Fork Nanobrowser only if a single integrated side-panel bulk runner is truly needed.
  - Building from scratch has no advantage here: every component exists under permissive licenses (Apache/MIT).

### Gaps
- I found no measured success rate for a Nanobrowser-style agent across hundreds of heterogeneous sites with a free model, so the 1,000-site reliability is unknown.
- The effort estimates are unvalidated judgment.
- I did not check whether Nanobrowser's parallel-task limit is configurable or how it behaves at high tab counts.
- I did not check Chrome memory limits for running many tab groups at once on the user's hardware.

---
I did not open the rtrvr "agent storefront" link or any purchase/sign-up flow, and I did not run any of the tools.
