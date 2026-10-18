# Can 53 concurrent agents run on $0 free hosted LLM tiers? (state as of 2026-10-18)

Research date: 2026-10-18. This builds on `research_notes/Zero cost AI browser agent/apis.md` (same date), which already lists RPM/RPD/TPM per provider. Numbers carried over from that file are cited to their original sources. "Official" means the provider's own docs or live API; "community" means a third-party tracker and is unconfirmed.

Workload assumed throughout: 53 agents. Each step sends 3k-6k input tokens (5,000 used) plus ~100 output tokens, so **5,100 tokens per request**. Each agent steps every 5-15 s, which is **4-12 requests/min per agent**.

## Q1. Concurrency limits (max simultaneous open requests), separate from RPM, per free provider

### Takeaway
Almost no free provider publishes a separate concurrency cap. The limits that actually bind are per-minute request or token limits and daily caps. The explicit concurrency-style caps found are Z AI GLM-Flash (1 concurrent request per model), Mistral free (about 1 request per second per key), LLM7 (1 RPS) and ModelScope ("dynamically rate-limited" concurrency). Gemini documents a concurrency number only for the async Batch API (100 concurrent batch requests). Cloudflare, Groq, NVIDIA, OpenRouter, Kilo and OVH document RPM caps but no concurrency cap.

### Cited Findings
- **Gemini API.** The only concurrency figure on the rate-limits page is "Concurrent batch requests: 100", under Batch API limits (page last updated 2026-10-15 UTC). I found no concurrency limit for normal `generateContent` calls. Limits are "applied per project, not per API key", and RPD resets at midnight Pacific — [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- **Gemini free-tier RPM/RPD is contested in October 2026:**
  - Community tracking "as of October 2026 (benchlm.ai) puts the 3.x Flash free-tier limits at roughly 10 requests per minute and 1,500 requests per day" — [klymentiev.com, Oct 2026](https://klymentiev.com/blog/gemini-api-free-tier)
  - A GitHub issue from March 2026 shows `generate_content_free_tier_requests` "still capped at 20 requests per day" — [aifreeapi, dated 2026-10-10](https://www.aifreeapi.com/en/posts/google-gemini-api-free-tier), citing [google-gemini/api-examples#98](https://github.com/google-gemini/api-examples/issues/98)
  - The Gemini CLI docs list "Gemini API key | Free tier (Unpaid) | 250 requests" per user per day — [Gemini CLI quotas](https://geminicli.com/docs/resources/quota-and-pricing/)
  - An earlier tracker listed 15 RPM / 1,500 RPD for Flash and 30 RPM / 1,500 RPD for Flash-Lite, possibly stale — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
  - Google itself says "Specified rate limits are not guaranteed" and shows exact limits only in AI Studio — [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- **Conflict on Gemini Pro.** One source says "Pro models left the free tier April 1, 2026" — [CloudZero, 2026](https://www.cloudzero.com/blog/google-vertex-ai-pricing/). The official pricing page (updated 2026-10-16) still listed 2.5 Pro on the Free Tier — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **Cloudflare Workers AI (official, last updated Sep 17, 2026).** Text generation is "300 requests per minute, unless the model requires the Workers Paid plan". Paid-only models get 20 RPM (standard billing) or 50 RPM (prepaid AI Gateway credits) "per account, per model". The page states no concurrency limit. "Model inferences in local mode using Wrangler will also count towards these limits." — [Cloudflare limits](https://developers.cloudflare.com/workers-ai/platform/limits/). The binding cap is still the 10,000 neurons/day free allocation — [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- **Mistral free / Experiment tier:**
  - "On the Mistral Free Tier, there is a global rate limit of 1 request per second per API key, applicable to all models" (community, r/MistralAI, 2026) — [Reddit](https://www.reddit.com/r/MistralAI/comments/1rc8rwf/mistral_api_quota_and_rate_limits_pools_analysis/)
  - Another source says "approximately 1 request/second and 30 requests/minute" — [getaiperks, 2026](https://www.getaiperks.com/en/blogs/21-mistral-free-credits). The 30 RPM vs 60 RPM difference is unresolved.
  - Officially, "Requests per second and tokens per minute are enforced independently", and exceeding either returns `429` — [Mistral known limitations](https://docs.mistral.ai/resources/known-limitations)
  - One source claims "Paid tiers include specific rate limits on concurrent requests" — [Activepieces](https://www.activepieces.com/blog/compare-mistral-ai-api-pricing-for-2026-models) (secondary, unverified)
- **Z AI (Zhipu).** GLM-4.7-Flash, GLM-4.5-Flash (retirement announced) and GLM-4.6V-Flash are each listed as "1 concurrent request" (community, page updated Oct 11, 2026) — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **ModelScope.** "concurrency is also dynamically rate-limited". It also requires real-name verification — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **LLM7.io.** Anonymous access reaches the `turbo` models. A free token raises limits to 60 RPM and 250 req/hr, with no change in models. Free-token limits from the previous round: 1 RPS, 100K tokens per 24h — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Kilo Code gateway.** 17 free models listed, each at "200 req/hr" with no API key. Includes `nemotron-3-ultra-550b:free` (1M context), `step-3.7-flash:free` (vision), `qwen3.8-27b:free` and `kilo-auto/free` — [mnfst, Oct 11, 2026](https://github.com/mnfst/awesome-free-llm-apis). Whether 200/hr is per IP overall or per model is ambiguous. The earlier round quoted "200 requests per hour per IP".
- **OVHcloud AI Endpoints.** Free anonymous tier "(no API key, no signup): 2 RPM per IP per model". 11 models listed, including Qwen3.5-397B-A17B, gpt-oss-120b and Llama-3.3-70B — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **NVIDIA NIM.** Default free limit is 40 RPM, with "no official way to circumvent this rate limit" — [NVIDIA forum, Jun 2026](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571). No concurrency figure was found.
- **Groq.** Each of 3 chat models gets 30 RPM / 1K RPD / 8K TPM / 200K TPD — [Groq rate limits](https://console.groq.com/docs/rate-limits). No concurrency figure was found.
- **OpenRouter `:free`.** 20 RPM and 50 free-model requests/day (under $10 purchased). "Making additional accounts or API keys will not affect your rate limits" — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits). No concurrency figure was found.
- **Pollinations:**
  - Anonymous (no key) use is "~1 req/15 sec" and "Image generation only" (community) — [aicredits.dev](https://aicredits.dev/submissions/113-pollinations-ai-free-api-no-signup-required)
  - The current docs show text calls authenticated with `Authorization: Bearer $POLLINATIONS_API_KEY`, through OpenAI-compatible and Anthropic Messages endpoints — [Pollinations docs](https://gen.pollinations.ai/docs)
  - The terms describe account balances with an inactivity clock from 2026-06-01 — [Pollinations terms](https://pollinations.ai/terms)
- **Chutes.** No longer free. Its "Early Access perk… provided 200 requests per day for free" — [Chutes announcement, Feb 27, 2026](https://chutes.ai/news/community-announcement-february). The community reports "Chutes is removing Early Access and adding limits" — [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1rgp3p7/chutes_is_removing_early_access_and_adding_limits/). Pricing is now per-token — [Chutes pricing](https://chutes.ai/pricing)
- **GitHub Models.** Retired on July 30, 2026 — [GitHub changelog](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/)

### Inferences
- An RPM cap is not a concurrency cap. If a provider enforces RPM as a bucket and has no concurrency limit, you can briefly have up to "RPM" requests open at once (for example ~40 on NVIDIA or ~300 on Cloudflare). This is an inference: no provider documents its bucket shape.
- Mistral enforces per second, which prevents such bursts. At 1 RPS with ~2-4 s latency, it holds only ~2-4 requests open.
- Z AI's 1-per-model cap means about 3 open requests across its three Flash models.
- By Little's law, average open requests = arrival rate × latency. At 212-636 RPM and an assumed 3 s latency for a 5k-token prompt, 53 agents keep only about 11-32 requests in flight on average. All 53 are in flight at once only if latency approaches the step interval. **The binding constraint is sustained RPM, TPM and daily quota, not concurrency.**

### Gaps
- Groq, NVIDIA, OpenRouter, Kilo, OVH and Cloudflare publish no concurrency limit that I could find. It is unknown whether they reject bursts beyond some hidden concurrency.
- Current official Gemini free-tier RPM/RPD numbers could not be confirmed. Sources range from 20 to 1,500 RPD per model.
- Pollinations' text-generation limits for a free registered key were not found.
- Petals was not researched within the tool budget; its 2026 status is unknown.

## Q2. Combined capacity: how many in flight at once, and how long 53 agents can run (worked calculation)

### Takeaway
A single burst of 53 simultaneous requests is achievable, mainly because Cloudflare (300 RPM) and NVIDIA (40 RPM) publish no concurrency cap. Sustaining 53 agents is not. Even on the most optimistic community numbers, all free tiers combined give ~190-270 RPM while Gemini's daily quota lasts. That covers 53 agents only at the slowest pace (one step every 15 s = 212 RPM), and only for roughly 2-3 hours. On pessimistic Gemini figures it lasts only minutes. After Gemini is exhausted, capacity falls to ~107-149 RPM, about 26-37 agents at the 15 s pace or 9-12 at the 5 s pace. Total free daily supply covers at most ~75% of one day at the slowest pace, and ~23% on pessimistic figures.

### Cited Findings (inputs; dates as cited)
- Groq: 8K TPM and 200K TPD per model, 3 chat models; cached tokens don't count — [Groq rate limits](https://console.groq.com/docs/rate-limits)
- Cloudflare: 10,000 neurons/day shared. Neurons per million input / output tokens:
  - qwen3-30b-a3b-fp8: 4,625 / 30,475
  - glm-4.7-flash: 5,500 / 36,400
  - gemma-4-26b-a4b: 9,091 / 27,273
  - gpt-oss-120b: 31,818 / 68,182
  — [Cloudflare pricing, Oct 15, 2026](https://developers.cloudflare.com/workers-ai/platform/pricing/). 300 RPM text cap — [Cloudflare limits, Sep 17, 2026](https://developers.cloudflare.com/workers-ai/platform/limits/)
- OpenRouter: 20 RPM, 50/day — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- NVIDIA: 40 RPM (forum-confirmed) — [NVIDIA forum](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571). 10,000 RPD per model (community, unverified) — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- Mistral: ~1 RPS per key (community) — [Reddit](https://www.reddit.com/r/MistralAI/comments/1rc8rwf/mistral_api_quota_and_rate_limits_pools_analysis/). ~30 RPM — [getaiperks](https://www.getaiperks.com/en/blogs/21-mistral-free-credits). 500K TPM and ~1B tokens/month — [mistral-vibe #275](https://github.com/mistralai/mistral-vibe/issues/275); [pricepertoken](https://pricepertoken.com/endpoints/mistral/free)
- Gemini: 10 RPM / 1,500 RPD per 3.x Flash model (community) — [klymentiev](https://klymentiev.com/blog/gemini-api-free-tier); or 20 RPD cap — [aifreeapi](https://www.aifreeapi.com/en/posts/google-gemini-api-free-tier); or 250/day — [Gemini CLI](https://geminicli.com/docs/resources/quota-and-pricing/). About 8 free text models are listed (3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, 3 Flash Preview, 2.5 Flash, 2.5 Flash-Lite, Gemma 4, plus 2.5 Pro if still free) — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). 3.7 Flash now routes to 3.8 and 3.5 to 3.6, so those aliases add no capacity — [nocode.mba](https://www.nocode.mba/articles/google-ai-studio-pricing)
- OVH: 2 RPM per IP per model, 11 models. Kilo: 200 req/hr. Z AI: 1 concurrent per model. LLM7: 100K tokens per 24h — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- Gemini free-tier instability in mid-October 2026: 429s, 503s and 403 PERMISSION_DENIED reports — [Google AI forum](https://discuss.ai.google.dev/tag/rate-limits/415)

### Worked calculation

**Demand: 53 agents at 5,100 tokens per request**

| Step interval | RPM per agent | 53 agents, RPM | Tokens/min | Requests/day | Tokens/day |
|---|---|---|---|---|---|
| 15 s | 4 | 212 | 1.08M | 305,280 | 1.56B |
| 10 s | 6 | 318 | 1.62M | 457,920 | 2.34B |
| 5 s | 12 | 636 | 3.24M | 915,840 | 4.67B |

**Supply: sustained RPM at 5,100 tokens per request**

| Provider | Sustained RPM | Daily request cap | How long the cap lasts at full RPM | Confidence |
|---|---|---|---|---|
| Gemini (~8 free text models × 10-15 RPM) | 80-120 | 160 (20/model), 2,000 (250/model) or 12,000 (1,500/model) | ~1.5 min, ~17-25 min, or ~1.7-2.5 h | community, conflicting |
| Mistral free (one key) | 30-60 | no daily cap; ~1B tokens/month ≈ 196,000 requests/month | month's quota gone in ~54 h (60 RPM) to ~109 h (30 RPM) | community |
| NVIDIA NIM | 40 | 10,000 per model (unverified) | ~4.2 h if traffic stays on one model | RPM forum-confirmed; RPD community |
| OVH anonymous (2 RPM × 11 models, per IP) | ~22 | none published (≤31,680/day) | all day, if no hidden cap | community |
| Z AI GLM-Flash (1 concurrent × ~2-3 models) | ~12-24, assuming 5-10 s reasoning latency | unpublished | unknown | community + my latency assumption |
| Kilo gateway | ~3.3 | 4,800 (200/hr) | all day | community |
| Groq (3 models; 8K TPM allows 1 request/min each) | ~3 | ~117 (200K TPD ÷ 5,100 ≈ 39 per model) | ~39 min | official |
| Cloudflare (best useful model, qwen3-30b: 5,000×4,625/1M + 100×30,475/1M ≈ 26.2 neurons per request) | burst up to 300 | ~382 (glm-4.7-flash ~321, gemma-4-26b ~207, gpt-oss-120b ~60) | ~1.3 min at 300 RPM | official |
| OpenRouter `:free` | 20 | 50 | 2.5 min | official |
| LLM7 (100K tokens ÷ 5,100) | 1 RPS | ~19 | seconds | community |
| AI Horde | see Q5 (whole network ~38 text threads) | n/a | unusable for a 5-15 s loop | official live API |

**Aggregate capacity over a day**
- **First ~2 minutes (burst):** everything is live, giving roughly 190-270 RPM sustained plus Cloudflare's 300 RPM and OpenRouter's 20 RPM until their ~430 requests run out. This is the only window in which even the 10 s pace (318 RPM) is covered.
- **While Gemini lasts:** Gemini (80-120) + Mistral (30-60) + NVIDIA (40) + OVH (22) + Z AI (12-24) + Kilo (3.3) + Groq (3) ≈ **190-272 RPM**. That supports:
  - 47-68 agents at the 15 s pace
  - 31-45 agents at the 10 s pace
  - 15-22 agents at the 5 s pace
- **How long 53 agents last at the 15 s pace (212 RPM).** Gemini must supply 212 − (107 to 149) = **63-105 RPM**, so 53 agents are covered only if Gemini sits near the top of its range. Gemini's daily cap then lasts:
  - 12,000 RPD (1,500/model): 12,000 ÷ 63-105 = **~1.9-3.2 hours**
  - 2,000 RPD (250/model): **~19-32 minutes**
  - 160 RPD (20/model): **~1.5-2.5 minutes**
- **After Gemini is exhausted:** Mistral + NVIDIA + OVH + Z AI + Kilo (+ Groq for ~40 min) ≈ **107-149 RPM**. That supports:
  - 26-37 agents at the 15 s pace
  - 17-24 agents at the 10 s pace
  - 9-12 agents at the 5 s pace
- **After ~4 hours,** if NVIDIA's 10K RPD cap is real, capacity falls to ~67-109 RPM, about 16-27 agents at the 15 s pace.
- **The floor with no known caps:** OVH, Z AI and Kilo together give ~37-49 RPM, about 9-12 agents at the 15 s pace. These are all community figures, and the anonymous endpoints are per IP.
- **Mistral's monthly budget:** ~1B tokens is less than one day of demand even at the slowest pace (1.56B tokens/day). Used continuously, it is gone in ~2.3-4.5 days.

**Total free daily supply (requests/day) vs demand**
- **Optimistic:** Gemini 12,000 + NVIDIA 57,600 (40 RPM all day, no RPD cap) + Mistral 86,400 (one day burns most of the month) + OVH 31,680 + Z AI ~34,560 + Kilo 4,800 + Cloudflare/Groq/OpenRouter/LLM7 ~568 ≈ **227,600 requests/day**. That is 75% of the 15 s demand, 50% of the 10 s demand and 25% of the 5 s demand.
- **Pessimistic:** Gemini 160 + NVIDIA 10,000 + Mistral 6,500 (monthly quota spread evenly) + OVH 31,680 + Z AI ~17,280 + Kilo 4,800 + small ones ~568 ≈ **71,000 requests/day**. That is about 23% of the 15 s demand.

### Inferences
- Answer to "can 53 run at once": yes for a burst of one step each, and yes at the 15 s pace for at most about 2-3 hours, and only if the optimistic Gemini figures (≥1,500 RPD per model, 10-15 RPM) and Mistral's 60 RPM both hold. At the 10 s or 5 s pace, 53 agents cannot be sustained beyond the first ~2 minutes.
- A realistic $0 steady state for an all-day run is about 10-35 agents at one step per 15 s, falling as daily caps hit. Mistral's monthly quota is the largest token pool and is gone within days.
- Prompt size is the main lever. Cutting 5,000 input tokens to ~1,500:
  - roughly triples every token-bound figure (Groq TPD, Cloudflare neurons, Mistral monthly, LLM7)
  - leaves RPM-bound figures unchanged (Gemini, NVIDIA, OVH, Kilo, OpenRouter)
- Prefix caching would not help on Gemini free, which has no context caching. On Groq, cached tokens don't count toward limits — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing); [Groq](https://console.groq.com/docs/rate-limits)
- Multiplying accounts or projects on the same provider is the only route that would close the gap. OpenRouter says it doesn't work, NVIDIA says there's no official way, and it is the risky pattern under the terms (see Q4).

### Gaps
- The Gemini figures dominate the result and could not be confirmed officially. The difference between 20 and 1,500 RPD per model changes the 53-agent window from minutes to hours.
- Mistral's real free RPS (1/s vs 30 RPM) and the monthly-token cap are community figures.
- NVIDIA token limits and daily caps are undocumented, and it's unknown whether 40 RPM applies per model or per account.
- OVH and Z AI daily caps are unpublished; the "all day" figures assume none exist.
- Real per-request latency under free-tier load was not measured. The 3 s and 5-10 s figures are my assumptions.

## Q3. Tool calling / JSON mode on the free endpoints that contribute capacity

### Takeaway
Tool calling is confirmed officially only on Groq, and Groq contributes ~3 RPM. For the high-capacity providers (Gemini, Mistral, NVIDIA, OVH, Z AI, Kilo), no source I fetched confirms tool calling or JSON mode on the free tier. Each needs a quick test with a free key. AI Horde shows no sign of tool calling.

### Cited Findings
- **Groq.** "All models hosted on Groq support tool use". gpt-oss-20b and gpt-oss-120b support tool use and JSON mode but not parallel tool calls. qwen3.8-27b supports parallel tool calls and JSON mode — [Groq tool use](https://console.groq.com/docs/tool-use)
- **Gemini.** An OpenAI-compatible endpoint exists at `https://generativelanguage.googleapis.com/v1beta/openai/` and works with a free key — [klymentiev, Oct 2026](https://klymentiev.com/blog/gemini-api-free-tier). Context caching and Google Search grounding on 3.x are "Not available" on the free tier. No sentence restricts function calling — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **OpenRouter.** The `openrouter/free` router reportedly picks a free model "that supports the capabilities you need, such as tool calling or structured outputs" — [KDnuggets](https://www.kdnuggets.com/5-free-llm-api-providers-you-can-use-in-2026) (unverified; the official doc returned 404 on 2026-10-18)
- **Pollinations.** Exposes OpenAI-compatible (`/v1`) and Anthropic Messages endpoints for text, which typically carry `tools` parameters — [Pollinations docs](https://gen.pollinations.ai/docs). Tool support for free keys is not stated.
- **Kilo, OVH, LLM7, Ollama Cloud.** All are listed as OpenAI SDK-compatible, but the tracker says nothing about tool calling or JSON mode — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)

### Inferences
- An agent pool spread across providers should expect mixed tool-call behaviour. The safest common denominator is prompting for a JSON action object and validating it client-side, which works even where native `tools` or `response_format` is missing.

### Gaps
- No official confirmation of function calling or JSON mode on the free tier for Gemini, Mistral, NVIDIA, Cloudflare, OVH, Z AI or Kilo.
- Per-model `supported_parameters` for OpenRouter `:free` models was not enumerated.

## Q4. Terms: parallel or automated use, splitting load, phone requirements

### Takeaway
No term I fetched prohibits parallel requests, automation, or spreading load across different providers. What is restricted is multiplying quota on the same provider: OpenRouter says it doesn't work, and NVIDIA says there's "no official way" around limits. Several free tiers are framed as evaluation or non-commercial. Phone verification is reported for Mistral (SMS) and Z AI. Kilo, OVH, LLM7 (anonymous) and AI Horde (anonymous) need no signup at all.

### Cited Findings
- **OpenRouter.** "Making additional accounts or API keys will not affect your rate limits, as we govern capacity globally." — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- **NVIDIA.** "There is no official way to circumvent this rate limit or to receive a rate limit increase on that same tier." — [NVIDIA forum](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571). Free endpoints are "Trial use only… Your use is logged" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Gemini.** No clause found that explicitly bans multiple projects or circumvention. The terms do say "Do not submit sensitive, confidential, or personal information to the Unpaid Services", and require Paid Services when serving users in the EEA, Switzerland or the UK — [Gemini API terms, 2026-04-28](https://ai.google.dev/gemini-api/terms)
- **Mistral.** The free tier "is for evaluation, not production"; "Credit Card Required: No — phone (SMS) verification only" (verified Sept 2026) — [pricepertoken](https://pricepertoken.com/endpoints/mistral/free). One secondary source says the free tier "is restricted to non-commercial research" — [Activepieces](https://www.activepieces.com/blog/compare-mistral-ai-api-pricing-for-2026-models) (unverified against Mistral's own terms)
- **Z AI.** "Registration accepts overseas phone numbers" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Cohere.** Trial key is "Non-commercial use only", 1,000 calls/month — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Kilo and OVH.** Free models are reachable with no API key and no signup — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **AI Horde.** Paid services that integrate the Horde are expected to give back as much as they take out. Anonymous service "may be restricted for anonymous users during high load" — [AI Horde FAQ](https://github.com/Haidra-Org/AI-Horde/blob/main/FAQ.md); [AI Horde README](https://github.com/Haidra-Org/AI-Horde)
- **Card or paid requirements (flagged).**
  - Cerebras needs a verified payment method, and its $5 expires in 30 days — [Cerebras](https://inference-docs.cerebras.ai/support/rate-limits)
  - OpenRouter's 1,000/day tier needs a $10 purchase — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
  - Chutes is now pay-per-token — [Chutes pricing](https://chutes.ai/pricing)
  - Cloudflare's elevated limits need prepaid credits — [Cloudflare limits](https://developers.cloudflare.com/workers-ai/platform/limits/)

### Inferences
- Routing 53 agents across many different providers is ordinary multi-provider fallback, and nothing found forbids it. Creating multiple Google projects or accounts to multiply Gemini quota is not explicitly banned in the fetched terms, but that is the pattern providers police.
- The "evaluation, not production" framing on Mistral and NVIDIA means a 53-agent, all-day workload sits outside the intended use, even if it isn't a stated breach.
- Gemini's unpaid-services terms make free Gemini unsuitable if the agents see personal or logged-in page data.

### Gaps
- I did not fetch the full ToS for Groq, Mistral, Cloudflare, OVH, Kilo or LLM7. Clauses on automated or bulk use or multiple accounts are unconfirmed.
- Phone or verification requirements for NVIDIA ("create and verify your account"), Groq and Google AI Studio sign-up were not confirmed.

## Q5. AI Horde: cost, concurrency, queue times, quality, privacy

### Takeaway
AI Horde is free and needs no account: the anonymous key `0000000000` works at the lowest queue priority. But it is a small volunteer network. A live snapshot on 2026-10-18 showed 33 text workers with 38 threads and 111 text requests queued, generating ~19.6K tokens per minute across the entire network. 53 agents at the 10 s pace would need ~31.8K output tokens/min (318 RPM × 100) on their own, more than the whole Horde produced. Queues are minutes long, anonymous users rank last, and workers can technically read prompts. It is not viable as capacity for a 5-15 s agent loop.

### Cited Findings
- **Free.** "Because the Horde is free! You will never need to pay to use the horde." — [AI Horde FAQ](https://github.com/Haidra-Org/AI-Horde/blob/main/FAQ.md)
- **Anonymous access.** "Use API key '0000000000'"; "Lowest priority in generation queues"; "No kudos tracking"; "No need to register"; "Service may be restricted for anonymous users during high load" — [AI Horde README](https://github.com/Haidra-Org/AI-Horde)
- **Priority.** Requests enter "a smart 'first in/first out' queue, prioritizing it according to the amount of Kudos you have". Kudos "is merely a prioritization mechanism, not a currency" — [AI Horde FAQ](https://github.com/Haidra-Org/AI-Horde/blob/main/FAQ.md)
- **Live network load** (`/api/v2/status/performance`, fetched 2026-10-18):
  - `text_worker_count`: 33
  - `text_thread_count`: 38
  - `queued_text_requests`: 111
  - `queued_tokens`: 40,470
  - `past_minute_tokens`: 19,618
  — [AI Horde performance API](https://aihorde.net/api/v2/status/performance)
- **Privacy.** "Can workers spy on my prompts or generations? Technically, yes… anyone with the know-how can modify their own code to not just see all prompts passing through, but even save all results they generate." However, "workers do not have any identifying information about individual requestors as they cannot see their ID or IP." The FAQ advises treating requests "as if you're posting in a public forum" — [AI Horde FAQ](https://github.com/Haidra-Org/AI-Horde/blob/main/FAQ.md)
- **Per-user parallel limit.** A per-user parallel-request limit exists: a 2022 user error reads "Parallel requests exceeded user limit" — [r/StableDiffusion, 2022](https://www.reddit.com/r/StableDiffusion/comments/ygo1kq/the_stable_horde_now_supports_inpainting/). The current numeric limit was not found.

### Inferences
- The network had 38 text threads in total. Even if one user could claim every one, peak concurrency would be ~38, shared with 111 already-queued requests.
- The backlog of 40,470 queued tokens against ~19.6K tokens/min is about 2 minutes of queue, with anonymous users served after kudos holders. Waits of minutes per step are therefore likely, not 5-15 s.
- Horde text workers are volunteer GPUs running models they choose. Long 5k-token prompts likely exclude many workers with smaller context settings. This is unverified; see Gaps.

### Gaps
- No current figure for max concurrent requests per user or per IP, max context, or `max_length` for anonymous text requests.
- Which text models were being served on 2026-10-18 and their quality (`/api/v2/status/models?type=text` was not fetched).
- No OpenAI-compatible endpoint, tool calling or JSON mode was documented in the sources fetched.
