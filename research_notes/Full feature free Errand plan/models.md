# Gemini free tier + local Qwen3.5-2B hybrid for Errand ($0, as of Oct 2026)

Research date: 2026-10-19. Page "last updated" dates are given inline. All Google pages were read through a summarizing fetch tool, so exact model IDs and numbers should be checked once in AI Studio before they go into code.

## Q1. Gemini API free tier as of Oct 2026: models, limits, features, terms, regions

### Takeaway
The free tier covers the current Flash and Flash-Lite line (3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, 3 Flash Preview) and the 2.5 family. 3.1 Pro Preview and the new "Gemini 4 Argon" are paid only. Limits are per project and shown only in AI Studio; the docs no longer print a per-model free table. Two rules bear directly on the widget: free-tier prompts may be used for training and read by human reviewers, and an app offered to users in the EEA, UK or Switzerland must use Paid Services.

### Cited Findings
**Free models (pricing page, last updated 2026-10-16)**
- Free tier = Yes for text/agent models: `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-embedding-2`, plus Gemma 4 and several Live/TTS/transcribe models. For every free-tier model, "Used to improve our products" = Yes. — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Free tier = No for: `gemini-4-argon` ("Gemini 4 Argon is not available on the Free tier"), `gemini-3.1-pro-preview`, all image models (3.1 Flash Image, 3 Pro Image, 2.5 Flash Image), Veo 3.1, Lyria, and Omni Flash. — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Grounding with Google Search on the free tier: 2.5 Flash and 2.5 Flash-Lite share 500 RPD. 2.5 Pro has no free grounding. For Gemini 3+, the 5,000 free searches/month allowance appears under the paid column, and many Gemini 3 models show grounding as unavailable on the free tier. — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Upcoming paid price increases (Dec 1, 2026 and Jan 1, 2027) "don't affect free-tier pricing". "Google AI Studio usage is free of charge in all available regions." — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- The models page (last updated 2026-10-13) marks 3.8 Flash ("New Stable"), 3.6 Flash, 3.5 Flash-Lite and 3.1 Flash-Lite as stable. It recommends "3.5 Flash-Lite or 3.8 Flash" for new projects and says access to the 2.5 models is limited to users who have used them before. 2.5 models "are not deprecated and will continue to be served until further notice." — [Gemini models](https://ai.google.dev/gemini-api/docs/models)

**Capabilities and context (gemini-3.8-flash model page, last updated 2026-09-02)**
- Input limit 1,048,576 tokens; output limit 65,536 tokens. — [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- Supported: function calling, structured outputs, thinking (low/medium/high, no `minimal`), URL context, search grounding, code execution, computer use (Preview), Batch API, caching. — [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- OpenAI-compatible endpoint at `https://generativelanguage.googleapis.com/v1beta/openai/` supports chat completions, `tools`/`tool_choice` function calling, `response_format` structured output (Pydantic/Zod), streaming, embeddings and `reasoning_effort`. It is still labelled beta. Gemini-only features need `extra_body`; parameters it does not recognize are silently ignored. Last updated 2026-10-14. — [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)

**Rate limits (rate-limits page, last updated 2026-10-15)**
- Limits are measured as RPM, input TPM and RPD; going over any one triggers an error. "Rate limits are applied per project, not per API key." RPD resets at midnight Pacific time. Preview and experimental models have tighter limits. — [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- Active limits are shown in AI Studio at `aistudio.google.com/rate-limit` and update automatically when the tier changes. The docs page has no per-model free-tier RPM/RPD table. — [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- Over-limit responses are `429 RESOURCE_EXHAUSTED`. The spend-based 10-minute caps are "N/A" for Free. — [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)

**Terms (Gemini API Additional Terms, effective 2026-03-23, last updated 2026-04-28)**
- For Unpaid Services, Google uses submitted content to "provide, improve, and develop Google products and services and machine learning technologies". Human reviewers may "read, annotate, and process your API input and output". Data is disconnected from the account, key and project before review. "Do not submit sensitive, confidential, or personal information to the Unpaid Services." — [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- You may "make API Clients available to users" in available regions. API Clients include websites and apps. For the EEA, Switzerland and the UK: "You may use only Paid Services when making API Clients available to users." — [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- The user must be 18+. API Clients must not be directed at, or likely to be accessed by, people under 18. — [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- The general Google APIs ToS (last modified 2021-11-09) says you "will not attempt to circumvent" documented limits and "will not misrepresent or mask either your identity or your API Client's identity". Credentials must be kept confidential, and "Developer credentials may not be embedded in open source projects." An API Client needs a privacy policy describing what user data it collects and how it is used and shared. — [Google APIs Terms of Service](https://developers.google.com/terms)

**Regions (available-regions page, last updated 2026-04-28)**
- Access is limited to listed countries. China, Russia, Iran, Hong Kong and Belarus are not listed. The page does not mention a separate free-tier region restriction; the EEA/UK/CH paid-only rule comes from the Additional Terms above. — [Available regions](https://ai.google.dev/gemini-api/docs/available-regions)

### Inferences
- Best free planner for Errand: `gemini-3.8-flash` (stable, 1M context, function calling, structured output, computer-use preview). Use `gemini-3.5-flash-lite` as the higher-volume or cheaper-quota second Gemini tier. Avoid `-preview` models for the main loop because their limits are tighter.
- Errand itself and the widget share one project quota, since limits are per project. Spreading load over extra projects or keys to raise quota would conflict with the "not circumvent" clause, and the user ruled it out anyway.
- With free tier, every page snapshot sent to Gemini can be used for training and seen by a reviewer. Logged-in, banking, email or other personal pages should therefore never reach Gemini; route them to the local 2B only.
- The 1M context does not mean whole raw pages should be sent. Free TPM is the real ceiling, so send compact accessibility trees or trimmed DOM.

### Gaps
- Exact free-tier RPM / TPM / RPD per model are not published in the docs as of 2026-10-15. They appear only in the signed-in AI Studio page, so the user has to read them there.
- Context window and capability list for `gemini-3.5-flash-lite` and `gemini-3.6-flash` were not fetched. Assume they are similar to 3.8 Flash, but verify.
- Whether computer use (Preview) on 3.8 Flash is allowed on the free tier was not confirmed.
- The Additional Terms fetch did not surface any clause on multiple accounts. The applicable text is the general ToS circumvention clause.

## Q2. Routing split between Gemini and local Qwen3.5-2B, with fallback when quota runs out

### Takeaway
Published hybrid designs all follow the same pattern: local first, then a validation gate, then escalation to cloud, with fallback triggered by quota or health. For Errand the split falls along task type. Gemini plans and drives multi-step browsing. The local 2B does bulk extraction, handles private pages, and checks results. When Gemini returns 429, work degrades to "local-only plus queue" and is never spread to other keys.

### Cited Findings
- The "SLM-default, LLM-fallback" pattern sends every query to a local small model first and escalates only when a verification step says the local model cannot answer confidently. — [Strathweb, Dec 2025](https://strathweb.com/2025/12/slm-default-llm-fallback-pattern-with-agent-framework-and-azure-ai-foundry)
- Confidence gates used in practice: token log-probabilities, agreement across several samples, and a format check before escalating. — [lablab.ai "cheap route"](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/sillygeese/cheap-route)
- Health-aware routing keeps simple tasks local and falls back to cloud when the local provider is busy, out of quota, or cooling down after failures. — [goagents llmkit](https://pkg.go.dev/github.com/eruca/goagents/llmkit)
- A LiteLLM gateway can switch transparently on local timeout, outage, or a prompt larger than the local context. It warns that cloud usage grows unnoticed unless it is tracked. — [bestllmfor.com LiteLLM guide](https://bestllmfor.com/guide/litellm-proxy-gateway-local/)
- Small models have lower capability ceilings. Hybrid pays off mostly when demand is spiky. — [Speaker Deck talk](https://speakerdeck.com/abedmatini/stop-paying-for-easy-prompts-architecting-hybrid-local-to-cloud-ai-systems); [PromptQuorum](https://www.promptquorum.com/prompt-bites/hybrid-local-cloud-llm-strategy)
- Gemini exposes an OpenAI-compatible endpoint, so one OpenAI client can call both llama-server (also OpenAI-compatible) and Gemini by switching base URL and model. — [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)
- Quota exhaustion shows up as `429 RESOURCE_EXHAUSTED`, and RPD resets at midnight Pacific. — [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- Note: most hybrid-routing sources are blogs, hackathon projects or libraries, not official guidance. — (search-result assessment)

### Inferences
- Proposed split. This is a design inference from the user's measurements (2B at about 93% on simple-page extraction, 53 slots, about 2.7 pages/s, weaker at multi-step tasks) and the sources above:
  - **Gemini 3.8 Flash:** turn the user's goal into a plan; choose the next action on multi-step or unfamiliar sites; handle hard pages (2B failed validation twice, or low confidence); write skills and record steps; generate "For You" suggestions (a few calls per day).
  - **Gemini 3.5 Flash-Lite:** second-tier escalation for extraction the 2B fails; cheap summarization of results.
  - **Local Qwen3.5-2B:** all bulk extraction (the 53-slot engine); every page with cookies, a login or personal data (privacy rule, Q1); schema and format validation of Gemini outputs; deduping and classification; replay-time sanity checks ("is this the expected page?").
- Escalation gate for the 2B: JSON-schema validity, required fields non-empty, and agreement between 2 slots (cheap because slots are parallel). Escalate only rows that fail.
- Quota fallback, in order: (1) on 429 from 3.8 Flash, retry on 3.5 Flash-Lite, which has its own per-model limits; (2) on 429 there too, the planner runs on the local 2B in "simple mode" (single-page tasks only, with a warning to the user) and multi-step tasks are queued until after the midnight-Pacific reset; (3) track Gemini calls per day locally so the "For You" feed and the widget never use up the planner's budget.
- Never rotate keys or projects on a 429. Errand should back off instead.

### Gaps
- No official Google guidance on hybrid local/cloud routing was found. All routing sources are third-party.
- No published accuracy numbers for Qwen3.5-2B as a multi-step browsing planner. The user's own benchmark is the only data.

## Q3. Website widget ("Rover"-like) at $0: hosting, key safety, terms

### Takeaway
A tiny JS widget calling a Cloudflare Worker proxy, with the Gemini key stored as a Worker secret, fits the Workers Free plan (100k requests/day; 10 ms CPU per request). It also follows the Google rule to keep credentials confidential. A free-tier widget on the user's own site is allowed in available regions, with conditions: no EEA/UK/Swiss visitors (paid-only there), not aimed at minors, a privacy policy on the site, and a visitor notice that chats go to Google and may be reviewed and used for training.

### Cited Findings
- Workers Free: 100,000 requests/day (reset at midnight UTC), 10 ms CPU per HTTP request, 50 subrequests per invocation, 128 MB memory, 64 environment variables/secrets of 5 KB each. Over the daily limit returns Error 1027 (fail open or fail closed per route); over CPU returns Error 1102. Last updated 2026-10-12. — [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- Outbound `fetch()` has no fixed time limit, and HTTP-triggered Workers have no wall-time limit. `ctx.waitUntil()` extends work by up to 30 s after the response. — [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- Credentials must be kept confidential, and you must "make reasonable efforts to prevent and discourage other API Clients from using your credentials". — [Google APIs Terms of Service](https://developers.google.com/terms)
- An API Client must have a privacy policy covering what user information it collects, uses and shares. — [Google APIs Terms of Service](https://developers.google.com/terms)
- API Clients may be made available to users in available regions. In the EEA/UK/CH only Paid Services may be used for that. API Clients must not be directed at, or likely to be accessed by, under-18s. — [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- Free-tier inputs and outputs may be read by human reviewers and used to improve Google products. — [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)

### Inferences
- Waiting on Gemini inside the Worker is I/O, not CPU, so a streaming proxy should stay under 10 ms of CPU. Keep JSON parsing and processing light. This follows from the CPU-vs-wall-time distinction on the limits page and should be verified with `wrangler tail` CPU stats.
- The Worker must apply abuse controls, because widget visitors drain the same per-project Gemini quota as Errand: an Origin/Referer allowlist for the user's domain, a per-IP request cap (Workers KV or the free rate-limiting binding; exact free limits not checked), max input length, and a fixed system prompt.
- EEA/UK/CH compliance: geo-block or hide the widget for those visitors using the `request.cf.country` field Cloudflare provides (not re-verified here), or accept that the widget has to wait for paid tier there.
- Privacy: tell visitors not to type personal data, because free-tier content may be reviewed. Inputs to a live site may contain personal data, so this rule is a real constraint.
- The local 2B cannot serve website visitors at $0 without exposing the laptop to the internet, and it would be offline whenever the laptop is. The widget should therefore use Gemini only. Answers can be grounded in the site's own pages, pre-extracted by the local 2B and stored as static JSON in the Worker or on Pages. That still counts as using both models.

### Gaps
- Free-tier limits of Cloudflare's Rate Limiting binding and KV write caps were not checked in this pass.
- Google's terms say nothing specific about a free-tier widget on a "personal" site versus a commercial one. The applicable conditions are the region, age, privacy-policy and data-use rules above.

## Q4. Record once, replay without AI: capture, determinism, brittleness, self-healing

### Takeaway
Record actions as semantic locators (role, text, test-id) the way Playwright codegen does, store them as a step list, and replay deterministically with zero model calls. When a step fails, ask the model for that one step only and write the fix back into the cache. This is the Stagehand/Qodex pattern.

### Cited Findings
- Playwright codegen records clicks and fills and generates code. It prefers role, text and test-ID locators and refines a locator until it matches exactly one element. It can record visibility, text and value assertions. — [Playwright codegen](https://playwright.dev/docs/codegen)
- `--save-storage=auth.json` and `--load-storage=auth.json` save and restore cookies, localStorage and IndexedDB so a session can be recorded logged in. `auth.json` is sensitive and should be gitignored. Chrome 136+ blocks automation of the default profile; use `--user-data-dir` with a separate profile. — [Playwright codegen](https://playwright.dev/docs/codegen)
- The docs recommend reviewing and improving generated code, because a recording reflects a single session. — [Playwright codegen](https://playwright.dev/docs/codegen)
- Stagehand caches `act()` results keyed by instruction, URL and selector. On failure it waits, retries, and updates the cache if a different selector works. — [Stagehand caching docs](https://www.mintlify.com/browserbase/stagehand/concepts/caching)
- Qodex caches each step as intent plus action plus selector, and replays without the LLM. On a stale selector it sends intent, snapshot, old action and error to the LLM for one bounded replacement. — [Qodex replay cache](https://qodex.ai/docs/ui-testing-replay-cache)
- browser-use's workflow-use records and replays deterministically, but its README calls self-healing/LLM fallback weak and "very early". — [workflow-use](https://github.com/cdxiaodong/workflow-use); [HN thread](https://brianlovin.com/hn/44007065)
- agbrowse resolves in order: cached selector, snapshot ref, CSS fallback. AI selector guessing is opt-in and off by default. — [agbrowse devlog](https://cdn.jsdelivr.net/npm/agbrowse@0.1.16/devlog/_fin/mvp/02_substrate/09_phase8_self_healing.md)

### Inferences
- For Errand, store each step as `{intent, url_pattern, action, locators:[role+name, text, test-id, css], expected_check}`. Replay tries each locator in order with no AI. Only if all fail, call the local 2B first ("which of these N candidate elements matches the intent?"), then Gemini, and write the winning locator back. In the common case a replay costs $0 and uses no quota.
- A skill (saved reusable instruction) and a recording can share one format: a skill is a recording with parameter slots (for example `{search_term}`) plus a natural-language intent the planner can use when the replay breaks.
- "For You" suggestions can come mostly from local data (recent recordings, skill run history, schedule), with at most one Gemini call per day to phrase or rank them. Keep the user's browsing history out of free-tier Gemini prompts (Q1 privacy rule).

### Gaps
- No independent reliability data on replay brittleness rates or self-healing success rates. All sources are vendor or project self-descriptions.

## Summary and main unknowns
- Free and usable now: `gemini-3.8-flash` (1M context; function calling, structured output, computer-use preview) and `gemini-3.5-flash-lite`. Limits are per project, shown only in AI Studio, RPD resets at midnight PT, over-limit returns 429.
- Terms: free-tier data may be used for training and reviewed by humans, so private pages go to the local 2B only. Apps for users are allowed in available regions, but EEA/UK/CH require paid tier. 18+, a privacy policy, and confidential keys are required. Do not circumvent limits.
- Widget: JS snippet, then a Cloudflare Worker (free: 100k req/day, 10 ms CPU) holding the key as a secret, then Gemini. Needs origin and IP rate limits, an EEA/UK/CH geo-block and a privacy notice. The 2B contributes offline by pre-extracting site content.
- Replay: Playwright-style semantic locators with no AI. On failure, heal one step via the local 2B and then Gemini, and cache the fix.
- Unknown: exact free RPM/RPD numbers; whether Flash-Lite and computer use are free; free limits of Cloudflare rate limiting and KV; no official Google hybrid-routing guidance. The model IDs (3.8 / 3.6 / 3.5 generation) came through a summarizing fetch and should be confirmed in AI Studio.
