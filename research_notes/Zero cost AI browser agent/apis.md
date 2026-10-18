# Free hosted LLM APIs for a zero-cost AI browser agent (state as of 2026-10-18)

Research date: 2026-10-18. Every number below carries its source and that source's date. "Official" means the provider's own docs; "community" means a third-party tracker. Free tiers in 2026 change month to month: GitHub Models was shut down, Groq retired models in September, and NVIDIA NIM endpoints started returning HTTP 410 in October. Re-check each provider's console before you build on it.

Throughput assumption used throughout: one LLM call per page, about 5,000 input tokens plus about 500 output tokens, so about 5,500 tokens per page.

## Q1. Which providers have a genuinely free ($0, no paid plan) tier in October 2026?

### Takeaway
Free with no card and no expiry: Google Gemini API (AI Studio), Groq, OpenRouter `:free` models, Mistral free mode, Cloudflare Workers AI, NVIDIA NIM / build.nvidia.com (labelled "trial use"), plus smaller ones: Kilo Code gateway, OVHcloud anonymous endpoints, LLM7.io, Z AI GLM-Flash, Cohere trial key (non-commercial), Ollama Cloud, Aion Labs. Not free: Cerebras now needs a verified payment method and gives only $5 that expires in 30 days. GitHub Models was retired on July 30, 2026. Together and SambaNova offer trial credits only. Hugging Face gives a negligible $0.10/month.

### Cited Findings
- **Google Gemini API.** The pricing page (last updated 2026-10-16) lists a Free Tier for Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, 3 Flash Preview, 2.5 Pro, 2.5 Flash, 2.5 Flash-Lite and Gemma 4. These are NOT on the free tier: Gemini 4 Argon, Gemini 3.1 Pro Preview, Gemini Omni Flash, and all image-generation, Veo and Lyria models — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Gemini's free usage tier qualifies with "Active project or free trial" and has no billing tier cap. Tier 1 requires linking a billing account — [Gemini rate limits, updated 2026-10-15](https://ai.google.dev/gemini-api/docs/rate-limits)
- An Oct 2026 article reports that, per Google's October 8 release notes, Gemini 3.7 Flash now routes to 3.8 Flash and 3.5 Flash routes to 3.6 Flash — [nocode.mba](https://www.nocode.mba/articles/google-ai-studio-pricing)
- **Groq.** Has a free tier with no credit card. Its listed chat models are `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b` — [mnfst/awesome-free-llm-apis, refresh 2026-10-05](https://github.com/mnfst/awesome-free-llm-apis)
- Groq shut down `qwen/qwen3.6-27b` on Sept 14, 2026 and `groq/compound` / `compound-mini` on Sept 21, 2026 — [mnfst, citing Groq deprecations](https://github.com/mnfst/awesome-free-llm-apis)
- **OpenRouter.** Free model variants have IDs ending in `:free` and carry their own free-usage request limits — [OpenRouter limits docs, fetched 2026-10-18](https://openrouter.ai/docs/api-reference/limits)
- A community tracker lists 16 named `:free` models plus "+6 more" as of 2026-10-05. It also found `openai/gpt-oss-20b:free`, `inclusionai/ling-3.0-flash:free` and `nvidia/nemotron-3-nano-30b-a3b:free` removed from the free tier — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Mistral.** Free mode is "enabled by default, no credit card required" — [mnfst, citing Mistral quickstart/pricing](https://github.com/mnfst/awesome-free-llm-apis)
- Mistral's free tier is described as an "Experiment" tier with rate-limited access to all API models at $0 (verified Sept 2026) — [pricepertoken](https://pricepertoken.com/endpoints/mistral/free)
- **Cloudflare Workers AI.** Free allocation of 10,000 Neurons per day. When you exceed it, "further operations will fail" until you move to Workers Paid at $0.011 per 1,000 Neurons (page updated Oct 15, 2026) — [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- Seven Cloudflare models need Workers Paid or prepaid credits: kimi-k2.6, kimi-k2.7-code, glm-5.2, glm-5.3, glm-5.3-flash, deepseek-v4-flash-0731 and deepseek-v4-pro-0813. About 60 models remain free — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **NVIDIA NIM (build.nvidia.com).** Free with NVIDIA Developer Program membership, 100+ models, base URL `https://integrate.api.nvidia.com/v1` — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- An NVIDIA forum moderator, quoted repeatedly in 2026 threads: "Many of you are using free tier API access to NVIDIA NIMs… There is no official way to circumvent this rate limit or to receive a rate limit increase on that same tier." — [NVIDIA forums, Jun 2026](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571)
- **Cerebras is NOT permanently free.** Its own FAQ: "Is there a permanently free tier? No. The Free Trial is time- and credit-bounded: $5 in credits that expire 30 days after they're granted." New accounts get the $5 "after adding a verified payment method" — [Cerebras rate limits/FAQ, fetched 2026-10-18](https://inference-docs.cerebras.ai/support/rate-limits)
- **GitHub Models is retired.** "GitHub Models will be fully retired on July 30, 2026. After this date, the playground, model catalog, inference API, and BYOK endpoints will no longer be available" — [GitHub changelog, 2026-07-01](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/)
- GitHub's docs page now says "GitHub Models has been retired." — [docs.github.com](https://docs.github.com/en/github-models)
- **Hugging Face.** Free users get $0.10/month in Inference Provider credits ("subject to change"), routed to Fireworks, Together, Novita and others — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Together AI** offers "Trial credits only… Credits expire — not a lasting free tier" — [stationx](https://app.stationx.net/articles/free-llm-api)
- **SambaNova** is listed under "Providers with trial credits", not free providers — [raullenchai/free-llm-api-resources](https://github.com/raullenchai/free-llm-api-resources). An OpenRouter blog table lists it as a "$5 trial credit" that needs a credit card — [OpenRouter blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/). That table looks stale (it lists Llama 3.3 70B / Mixtral for Groq), so treat it as low confidence.
- **Other permanent free tiers (community list):**
  - Kilo Code gateway: free models, no API key, 200 req/hr per IP.
  - OVHcloud AI Endpoints: anonymous, no key, 2 RPM per IP per model, EU-hosted.
  - LLM7.io: free token.
  - Z AI (Zhipu): GLM-4.7-Flash, GLM-4.6V-Flash.
  - Cohere: trial key, 1,000 calls/month, non-commercial.
  - Ollama Cloud: free tier with session and weekly limits.
  - Aion Labs: 15 RPM, 20K TPD.
  - ModelScope and SiliconFlow: both need real-name verification.
  — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- The often-cited `cheahjs/free-llm-api-resources` repo returned HTTP 404 on 2026-10-18 — [GitHub](https://github.com/cheahjs/free-llm-api-resources). A fork with the same name exists — [raullenchai fork](https://github.com/raullenchai/free-llm-api-resources)

### Inferences
- Under the hard $0 / no-card rule, drop Cerebras, GitHub Models, Together, SambaNova and Hugging Face (too small). Also drop OpenRouter's 1,000 RPD tier, which needs a $10 purchase.
- The usable core for a browser agent is Gemini, Mistral, Groq, NVIDIA NIM, Cloudflare and OpenRouter `:free`. Kilo, OVH and Z AI work as opportunistic overflow.

### Gaps
- I could not fetch Together's or SambaNova's official pages to confirm their October 2026 terms. Their status comes from secondary sources only.
- I did not check Ollama Cloud's numeric free limits; they are unpublished per the community list.

## Q2. Exact free limits, models, context, tool calling / JSON, vision

### Takeaway
Only Groq, OpenRouter, Cerebras (trial) and Cloudflare publish exact free numbers. Google and Mistral no longer publish per-model free limits and show them only in each account's console, so the Gemini and Mistral figures below are community-reported. For an agent loop, the binding limits are Groq's 8K TPM, OpenRouter's 50 requests/day and Cloudflare's 10K neurons/day.

### Comparison table (all $0, no card unless flagged)

| Provider | Free limits (date, source type) | Notable free models / context | Tools / JSON on free | Vision on free |
|---|---|---|---|---|
| Gemini API | Per project; RPD resets midnight Pacific. Google no longer publishes per-model numbers. Community-reported: 2.5/3.5/3.6 Flash 15 RPM / 1,500 RPD; Flash-Lite 30 RPM / 1,500 RPD; 2.5 Pro 5 RPM / 50 RPD; 3.8 Flash unpublished | 3.8 Flash, 3.6 Flash, Flash-Lite, 2.5 Pro/Flash, Gemma 4; 1M context, 65K output | Not confirmed on free tier in sources fetched (see Gaps) | Yes: text+image+audio+video input |
| Groq | gpt-oss-120b / gpt-oss-20b / qwen3.8-27b: 30 RPM, 1K RPD, 8K TPM, 200K TPD each (official, fetched 2026-10-18) | 131K context; gpt-oss 65K output; qwen3.8 16K output | Tool use and JSON mode on all three; parallel tool calls only on qwen3.8-27b | Unclear for qwen3.8-27b |
| OpenRouter `:free` | 20 RPM, 50 free-model requests/day if under $10 ever purchased; 1,000/day only after $10 (official) | ~22 free models, e.g. nemotron-3-ultra-550b (1M), gemma-4-31b (262K, image), qwen3.8-27b (262K, image+video) | Varies per model | Some models (gemma-4, qwen3.8, dots-3, inkling) |
| Mistral free / "Experiment" | ~1 req/s, 500K TPM, ~1B tokens/month (community; Mistral shows exact limits only in Admin → Limits). One source says $10/month in credits instead | Mistral Medium 3.5, Small 4, Large 3, Ministral 3B/8B/14B, Codestral; 256K context | Not verified in sources fetched | Text+image on Medium 3.5, Small 4, Ministral 3 |
| Cloudflare Workers AI | 10,000 neurons/day shared across all models; resets 00:00 UTC; ~300 RPM for text generation (official pricing; RPM from community quoting the limits page) | gpt-oss-120b (128K), llama-3.3-70b-fp8-fast (24K), gemma-4-26b-a4b (256K, vision), mistral-small-3.1 (128K, vision), llama-4-scout (131K) | Not verified | gemma-4-26b, mistral-small-3.1, llama-3.2-11b-vision, llama-4-scout |
| NVIDIA NIM | Default 40 RPM (forum-confirmed, Jun–Aug 2026); "10,000 RPD" (community, unverified) | nemotron-3-super-120b (1M), nemotron-3-ultra-550b (1M), gemma-4-31b (262K), gpt-oss-20b (131K); several models returned HTTP 410 from 2026-10-03 | Not verified | Some models (e.g. kimi-k3 text+image) |
| Kilo Code gateway | 200 req/hr per IP, no API key (community) | nemotron-3-ultra (1M), step-3.7-flash (262K, vision), qwen3.8-27b:free | Not verified | step-3.7-flash, qwen3.8-27b, dots-3 |
| OVHcloud anonymous | 2 RPM per IP per model, no key (community) | Qwen3.5-397B (262K, vision), gpt-oss-120b (128K), Llama-3.3-70B | Not verified | Qwen3.x VL models |
| LLM7.io | 1 RPS, 60 RPM, 250 req/hr, 100K tokens / 24h with free token (community) | DeepSeek-V4-Flash (400K), gpt-oss:20b | Not verified | No |
| Z AI (Zhipu) | 1 concurrent request (community) | GLM-4.7-Flash (200K), GLM-4.6V-Flash (128K, multimodal) | Not verified | GLM-4.6V-Flash |
| Cerebras (trial, needs card, flagged) | 5 RPM, 30K uncached TPM, 1M TPH, 1M TPD per model; $5 that expires in 30 days | gpt-oss-120b, qwen-3.8-27b | n/a | qwen-3.8-27b (2 images per request) |

### Cited Findings
- **Gemini rate limits page (2026-10-15).** Limits cover RPM, input TPM and RPD. They are "applied per project, not per API key." RPD resets at midnight Pacific. "Rate limits are more restricted for experimental and preview models." Exact limits appear only in AI Studio: "Specified rate limits are not guaranteed and actual capacity may vary." — [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- "Google no longer publishes per-model free-tier rate limits; check your quotas in AI Studio." The tracker still shows 15 RPM / 1,500 RPD for 3.6 Flash, 3.5 Flash and 2.5 Flash; 30 RPM / 1,500 RPD for the Flash-Lites; 5 RPM / 50 RPD for 2.5 Pro; and "—" for 3.8 and 3.7 Flash. All have 1M context and 65K max output — [mnfst](https://github.com/mnfst/awesome-free-llm-apis). These figures are carried over from older published values and may be stale.
- **Gemini free-tier feature gaps.** Context caching is "Not available" on the free tier for all models. Google Search grounding is "Not available" on the free tier for Gemini 3.x models; 2.5 Flash and Flash-Lite get 500 RPD of grounding, shared — [Gemini pricing, 2026-10-16](https://ai.google.dev/gemini-api/docs/pricing)
- **Gemini instability signals.** Forum threads from mid-October 2026 report a "Gemini 3.8 Flash: Free Tier Rate Limit stuck… not resetting", "Free Tier Access Restricted — 403 PERMISSION_DENIED", and free-tier 503s on 3.8 Flash and 429s on 3.6 Flash — [Google AI forum](https://discuss.ai.google.dev/tag/rate-limits/415); [forum thread](https://discuss.ai.google.dev/t/free-tier-interactions-api-getmodel-succeeds-but-generation-returns-503-on-gemini-3-8-flash-and-429-on-gemini-3-6-flash/189550)
- **Groq table (fetched 2026-10-18).**
  - `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`: 30 RPM, 1K RPD, 8K TPM, 200K TPD each.
  - `openai/gpt-oss-safeguard-20b`: 3 RPM, 2K TPM.
  - Limits apply at the organization level. Cached tokens don't count.
  — [Groq rate limits](https://console.groq.com/docs/rate-limits). Caveat: the page also says "the limits shown below are the base limits for the Developer plan", which conflicts with the community reading that this is the free-plan table ([mnfst](https://github.com/mnfst/awesome-free-llm-apis)). The scrape may have captured only one tab of a tabbed table. Check your own limits page.
- **Groq tool use.** "All models hosted on Groq support tool use." gpt-oss-20b and gpt-oss-120b support tool use and JSON mode but not parallel tool calls. qwen3.8-27b supports parallel tool calls and JSON mode. The page doesn't say whether these work on the free plan — [Groq tool use](https://console.groq.com/docs/tool-use)
- Groq contexts: gpt-oss-120b and gpt-oss-20b 131K with 65K output; qwen3.8-27b 131K with 16K output — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **OpenRouter free limits (official).** Under 10 credits purchased: 20 RPM and 50 requests per day. At least 10 credits: 20 RPM and 1,000 per day. The daily counter is a single `free_model_daily_requests` value ("Free-model requests allowed per UTC day") — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits). A community list says "50 RPD per model" ([mnfst](https://github.com/mnfst/awesome-free-llm-apis)), which conflicts with the single-counter description in the official doc.
- OpenRouter: "If your account has a negative credit balance, you may see 402 errors, including for free models." Upstream providers can also rate-limit, returning 429 with `provider_code` — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- The `openrouter/free` router reportedly picks a free model "that supports the capabilities you need, such as tool calling or structured outputs" — [KDnuggets](https://www.kdnuggets.com/5-free-llm-api-providers-you-can-use-in-2026). The official router doc URL returned 404 on 2026-10-18, so this is unverified.
- **Mistral.** "Mistral no longer publishes numeric free-tier rate limits." Last published values were about 1 RPS and 500K TPM. Models include Medium 3.5, Small 4, Large 3, Ministral 3 (3B/8B/14B) and Codestral, with 256K context (Codestral 128K) — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- One user-posted table shows the Experiment plan at Mistral Small 500,000 TPM and 1,000,000,000 tokens/month, with "lower priority… and 1 request/second limit" — [mistral-vibe issue #275](https://github.com/mistralai/mistral-vibe/issues/275)
- Mistral's official docs point to Admin Panel → API → Limits for current limits — [Mistral usage limits](https://docs.mistral.ai/admin/billing-usage/usage-limits)
- **Conflict on Mistral's free allowance.** One tracker says the Free plan carries "$10/month in API credits", shared across Studio, the API and Vibe Code ([mnfst](https://github.com/mnfst/awesome-free-llm-apis)). Another says "rate-limited free access, no credits… ~1 billion tokens/month" ([pricepertoken](https://pricepertoken.com/endpoints/mistral/free)). Mistral's own pricing page didn't expose either detail to my scraper.
- **Cloudflare neuron costs (official, Oct 15, 2026), per million input / output tokens:**
  - gpt-oss-120b: 31,818 / 68,182
  - llama-3.3-70b-fp8-fast: 26,668 / 204,805
  - gemma-4-26b-a4b-it: 9,091 / 27,273
  - qwen3-30b-a3b-fp8: 4,625 / 30,475
  - glm-4.7-flash: 5,500 / 36,400
  - mistral-small-3.1-24b: 31,876 / 50,488
  - llama-3.2-11b-vision: 4,410 / 61,493
  - granite-4.0-h-micro: 1,542 / 10,158
  — [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- Cloudflare contexts: llama-3.3-70b-fp8-fast 24K; gpt-oss-120b 128K; gemma-4-26b 256K with Text+Vision; mistral-small-3.1 128K with Text+Vision. The limits page says text generation allows "300 requests per minute, unless the model requires the Workers Paid plan" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **NVIDIA NIM.** The default free limit is 40 RPM. The community says there is no official increase path on the free tier ([NVIDIA forum, Aug 2026](https://forums.developer.nvidia.com/t/request-to-increase-nvidia-nim-api-rate-limit-40-200-rpm/379653)). The tracker lists "40 RPM, 10,000 RPD" per model ([mnfst](https://github.com/mnfst/awesome-free-llm-apis)).
- NVIDIA model churn: `openai/gpt-oss-120b`, `meta/llama-3.3-70b-instruct`, `minimaxai/minimax-m3` and `mistralai/mistral-nemotron` returned "HTTP 410 Gone… reached its end of life" from 2026-10-03 — [mnfst README refresh notes, 2026-10-05](https://github.com/mnfst/awesome-free-llm-apis)
- **Cerebras trial limits (official).** gpt-oss-120b and qwen-3.8-27b: 5 RPM, 30K uncached TPM, 90K total TPM, 1M TPH and 1M TPD each. qwen-3.8-27b allows 2 images per request — [Cerebras](https://inference-docs.cerebras.ai/support/rate-limits)
- **LLM7.io** free token: 1 RPS, 60 RPM, 250 requests/hr and 100,000 tokens per 24h; "may be reduced without notice." **Kilo Code**: "Free models are reachable with no API key, at 200 requests per hour per IP." **OVH**: 2 RPM per IP per model, anonymous — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)

### Inferences
- For a browser agent that sends ~5K-token page snapshots, Groq's 8K TPM means about one agent step per minute per model. It's fast per call but can't sustain a multi-step loop.
- Groq is useful for short, compressed prompts or as a fallback, not as the main agent brain.
- Tool calling is confirmed on the free tier only for Groq, and even there implicitly ("all models hosted on Groq"). For Gemini, Mistral, OpenRouter, NVIDIA and Cloudflare, test function calling and JSON mode on a free key before committing.

### Gaps
- I couldn't retrieve current official Gemini free-tier RPM/RPD/TPM numbers; Google shows them only per-account in AI Studio. The 15 RPM / 1,500 RPD figures are community carry-overs and possibly stale.
- No source I fetched explicitly confirms that Gemini function calling or structured output works on the free tier, though the pricing page doesn't exclude it.
- Mistral's exact free limits and the "$10/month credits vs ~1B tokens/month" question are unresolved. Check Admin → Limits after signup.
- NVIDIA NIM daily caps and token limits aren't documented officially.
- Per-model tool-calling support for OpenRouter `:free` models wasn't enumerated. The model catalog's `supported_parameters` field is the place to check.

## Q3. Credit card, phone, and expiry

### Takeaway
No card and no expiry: Gemini, Groq, OpenRouter (stay under $10 lifetime purchases), Mistral (phone/SMS verification reported), Cloudflare, NVIDIA (account verification needed), Kilo, OVH and LLM7. Flagged: Cerebras needs a verified payment method and the credits expire in 30 days. OpenRouter's higher 1,000/day tier needs a $10 purchase. ModelScope and SiliconFlow need real-name ID.

### Cited Findings
- **Gemini.** Free tier: "Free tier, no credit card" ([mnfst](https://github.com/mnfst/awesome-free-llm-apis)). The free usage tier is "Active project or free trial"; moving to Tier 1 requires linking billing ([Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)). Users must be 18 or older ([Gemini API terms, updated 2026-04-28](https://ai.google.dev/gemini-api/terms)).
- **Groq.** "Free tier, no credit card" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **OpenRouter.** "20+ free models, a single API key, and no credit card" — [OpenRouter blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/). The 1,000/day tier needs at least $10 in credits purchased — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- **Mistral.** "Credit Card Required: No — phone (SMS) verification only" (verified Sept 2026) — [pricepertoken](https://pricepertoken.com/endpoints/mistral/free)
- **Cerebras.** "$5 in free credits after adding a verified payment method. These credits expire 30 days after they're granted… If you skip adding a payment method at sign-up, Playground and API access remain inactive" — [Cerebras](https://inference-docs.cerebras.ai/support/rate-limits)
- **Cloudflare.** 10,000 neurons/day free, no credit card. "Going over does not bill you, the request fails." — [mnfst](https://github.com/mnfst/awesome-free-llm-apis); [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- **NVIDIA.** build.nvidia.com: "Create and verify your account to unlock full access to NVIDIA NIM APIs" — [NVIDIA Build](https://build.nvidia.com/)
- **Kilo Code / OVH.** No API key or signup required for the free and anonymous tiers — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Z AI.** "Registration accepts overseas phone numbers." Chat API does not require real-name verification — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **SiliconFlow / ModelScope.** SiliconFlow requires real-name identity verification (from May 15, 2026), and its verification supports mainland-Chinese documents. ModelScope requires Alibaba Cloud account binding plus real-name verification — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Cohere.** Trial key, no card, 1,000 calls/month, "Non-commercial use only" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)

### Inferences
- Of the services that start as trials and later require payment, Cerebras is the only one still offering an LLM API. Exclude it under the hard constraint.
- For OpenRouter, never buy credits. Note that a negative balance can block even free models.

### Gaps
- I couldn't confirm whether NVIDIA's "verify your account" step requires a phone number in Oct 2026.
- I couldn't confirm Groq's sign-up verification requirements (email only vs phone).

## Q4. Terms: training on data, automation and scraping limits, calling from a Chrome extension

### Takeaway
On free tiers, Google uses prompts and responses to improve products, including human review, outside the EEA/UK/CH. Mistral's free mode trains on prompts unless you opt out. NVIDIA logs free usage. OpenRouter's free providers may log prompts. Google explicitly says not to send sensitive or personal data to unpaid services, which matters for an agent reading logged-in pages. None of the terms I fetched ban automated or bulk use outright. A Chrome extension's service worker can call any of these APIs cross-origin if it declares `host_permissions`, so browser CORS support doesn't matter. Keys shipped inside a distributed extension are exposed to anyone who installs it.

### Cited Findings
- **Gemini, unpaid services.** "Google uses the content you submit to the Services and any generated responses to provide, improve, and develop Google products and services and machine learning technologies"; "human reviewers may read, annotate, and process your API input and output." For EEA, Switzerland and the UK, the paid-services data terms apply even to unpaid quota — [Gemini API Additional Terms, updated 2026-04-28](https://ai.google.dev/gemini-api/terms)
- **Gemini.** "Do not submit sensitive, confidential, or personal information to the Unpaid Services." — [Gemini API terms](https://ai.google.dev/gemini-api/terms)
- **Gemini.** "You may use only Paid Services when making API Clients available to users in the European Economic Area, Switzerland, or the United Kingdom." — [Gemini API terms](https://ai.google.dev/gemini-api/terms)
- The pricing page marks Free Tier "Used to improve our products: Yes" and Paid Tier "No" — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **Gemini on circumvention.** A targeted query of the Gemini Additional Terms found no clause that explicitly prohibits circumventing rate limits or using multiple projects — [Gemini API terms](https://ai.google.dev/gemini-api/terms). Rate limits are enforced per project — [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- **Mistral.** "Free-mode inputs and outputs may be used to train Mistral models, and you can opt out at any time" — [mnfst, citing Mistral data-usage docs](https://github.com/mnfst/awesome-free-llm-apis)
- **NVIDIA free endpoints**, quoted via Kilo: "Trial use only - do not submit personal or confidential data. Your use is logged for security purposes and to improve NVIDIA products and services." — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- An NVIDIA moderator says production-level access means paying to deploy — [NVIDIA forums](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571)
- **OpenRouter.** "Free providers may log prompts for training" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Kilo.** Its `kilo-auto/free` router "may route your requests to providers that log prompts and outputs" — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Groq.** GroqCloud documents "standard 30-day retention, Zero Data Retention (ZDR) options" — [Groq Your Data page description](https://console.groq.com/docs/your-data). A secondary table claims Groq does not train on data — [OpenRouter blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/), low confidence.
- **Cohere** trial keys are non-commercial only — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Chrome extensions.** "A script executing in an extension service worker or foreground tab can talk to remote servers outside of its origin, as long as the extension requests host permissions." But "Cross-origin requests are always treated as such in content scripts, even if the extension has host permissions." — [Chrome for Developers: Cross-origin network requests](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests)
- Chrome's guidance also says not to let content scripts request arbitrary URLs through the background script, and to avoid `innerHTML` on fetched responses — [Chrome docs](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests)
- **Security note on the community list itself.** The mnfst repo removed a "malicious security-audit workflow (credential stealer)" on Oct 11, 2026 — [mnfst commit history](https://github.com/mnfst/awesome-free-llm-apis). Don't run that repo's scripts blindly.

### Inferences
- Architecture: make every LLM call from the MV3 service worker with `host_permissions` for each API host, and pass page snapshots from content scripts via messaging.
- Keep keys in `chrome.storage.local`, entered by the user and not bundled. If the extension is ever published, each user must bring their own free key.
- For an agent that reads pages behind logins (email, banking, dashboards), the free tiers of Gemini, NVIDIA, Mistral (without opt-out) and OpenRouter-logged providers are a privacy risk, and Google's terms tell you not to send that data. Bulk extraction of public pages is the safer fit.
- Keys are per-provider and accounts are per-person, so using several different providers in parallel is ordinary multi-provider routing. OpenRouter itself promotes model fallbacks. The risky pattern is creating several accounts or projects on the same provider to multiply quota.

### Gaps
- I didn't fetch Groq's, Mistral's, Cloudflare's or OpenRouter's full Terms of Service, so I can't confirm or rule out clauses on automated or bulk use, scraping-derived content, or multiple accounts for those providers.
- I didn't fetch the general Google APIs Terms of Service, which the Gemini terms build on, to check for an anti-circumvention clause.
- Cloudflare data-use conditions for Workers AI weren't stated on its pricing or limits pages, per the community list.

## Q5. Realistic throughput (~5K input tokens per page) and best free combination; is rotation allowed?

### Takeaway
On officially published free limits alone, capacity is small: Groq ~108 pages/day across 3 models, OpenRouter 50/day, Cloudflare ~40–260/day depending on model. That's roughly 200–400 pages/day verified. A 1,000-page job in a day needs the larger but community-reported buckets: Mistral free (~1 req/s, ~1B tokens/month ≈ 6,000 pages/day if accurate), Gemini (~1,500 RPD per model if accurate), NVIDIA NIM (40 RPM), plus Kilo and OVH overflow. Spreading work across different providers is not restricted by any terms found. Multiplying accounts on one provider either doesn't help (OpenRouter) or has no official path (NVIDIA).

### Cited Findings and calculations (5,500 tokens per page; dates as cited above)
- **Groq (official table).** 8K TPM gives about 1 page/min per model. 200K TPD gives about 36 pages/day per model. Three chat models (gpt-oss-120b, gpt-oss-20b, qwen3.8-27b) give about 108 pages/day. The 1K RPD cap is never reached at this page size — [Groq rate limits](https://console.groq.com/docs/rate-limits). Cached tokens don't count toward limits, which helps with repeated system prompts — [Groq](https://console.groq.com/docs/rate-limits)
- **OpenRouter (official).** 50 free-model requests/day total, 20 RPM, so 50 pages/day. Making extra keys or accounts doesn't help: "Making additional accounts or API keys will not affect your rate limits, as we govern capacity globally." — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- **Cloudflare (official neuron prices, 10K/day).** Neurons per page and pages per day:
  - gpt-oss-120b: ~193 neurons, ~51 pages/day
  - llama-3.3-70b-fp8-fast: ~236 neurons, ~42 pages/day; only 24K context
  - gemma-4-26b-a4b: ~59 neurons, ~169 pages/day; vision
  - glm-4.7-flash: ~46 neurons, ~219 pages/day
  - qwen3-30b-a3b-fp8: ~38 neurons, ~261 pages/day
  - granite-4.0-h-micro: ~13 neurons, ~780 pages/day; tiny model
  — computed from [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- **Gemini (community numbers).** If free models still get ~15 RPM / 1,500 RPD (Flash) and 30 RPM / 1,500 RPD (Flash-Lite), each model is capped at about 900–1,800 pages/hour and 1,500 pages/day, with limits per model per project — [mnfst](https://github.com/mnfst/awesome-free-llm-apis); per-project scoping from [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). Free-tier TPM is unknown, and October forum reports of 429/503/403 errors suggest real capacity may be lower — [Google AI forum](https://discuss.ai.google.dev/tag/rate-limits/415)
- **Mistral (community numbers).** At ~1 RPS and 500K TPM, the RPS limit binds at about 60 pages/min (~3,600/hr). A ~1B tokens/month cap is about 181,000 pages/month, or ~6,000/day — [mistral-vibe issue](https://github.com/mistralai/mistral-vibe/issues/275); [pricepertoken](https://pricepertoken.com/endpoints/mistral/free). Experiment-plan traffic has "lower priority (may be slower during peak times)" — [mistral-vibe issue](https://github.com/mistralai/mistral-vibe/issues/275)
- **NVIDIA NIM.** 40 RPM gives up to ~2,400 pages/hr, if the per-model daily cap (community: 10,000 RPD) and undocumented token limits allow. Limits depend on "model, use-case and the amount of current overall traffic" — [NVIDIA forum](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571); [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Kilo Code.** 200 req/hr per IP is up to ~4,800/day; token limits unknown. **OVH anonymous**: 2 RPM per IP per model is about 120 pages/hr per model. **LLM7**: 100K tokens/24h is about 18 pages/day. **Aion Labs**: 20K TPD is about 3 pages/day — [mnfst](https://github.com/mnfst/awesome-free-llm-apis)
- **Cerebras** (excluded, card required): 1M TPD per model would be ~180 pages/day per model, but only for 30 days — [Cerebras](https://inference-docs.cerebras.ai/support/rate-limits)
- **Rotation on the same provider.** OpenRouter says extra accounts or keys don't raise limits ([OpenRouter](https://openrouter.ai/docs/api-reference/limits)). NVIDIA: "There is no official way to circumvent this rate limit" ([NVIDIA forum](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm-personal-agentic-ai-development/373571)). OpenRouter's own docs recommend model fallbacks across providers when you hit 429s ([OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)).

### Inferences
- **Peak parallelism**, if the community numbers hold:
  - Mistral ~60/min
  - NVIDIA ~40/min
  - Gemini ~15–30/min per free model, with several free models
  - Cloudflare up to 300 RPM, but limited by neurons
  - Groq ~3/min
  - OpenRouter 20/min until the 50/day cap
  - Kilo ~3/min
  - OVH 2/min per model

  That's roughly 150–200 calls/min in aggregate. A 1,000-page job could finish in well under an hour, with "dozens in parallel" possible only by fanning out across providers and models. Daily caps, not per-minute limits, bind first.
- **Suggested $0 stack for bulk extraction (1,000 pages/job):**
  - Mistral free (Small 4 / Ministral) as primary.
  - Gemini Flash-Lite and Flash as co-primary, split across models because limits are per model.
  - NVIDIA NIM as overflow.
  - Cloudflare gemma-4-26b or qwen3-30b for ~170–260 pages/day.
  - OpenRouter `:free` (50/day) and Groq (~108/day) as small top-ups.
  - Kilo and OVH as anonymous last resorts.

  Expect real capacity to be lower than the theoretical figures. Build 429 back-off and multi-provider fallback in from day one.
- **For the interactive agent loop** (few calls, latency-sensitive): Gemini Flash (1M context, vision) or Groq gpt-oss-120b (tool use, JSON mode, very fast) are the best candidates. Groq's 8K TPM means you need to compress page snapshots well under 8K tokens.
- **Reduce tokens per page.** Strip pages to text or accessibility trees and use cached system prompts (Groq and Cerebras don't count cached tokens). Dropping from 5K to 2K tokens per page roughly doubles or triples every token-bound figure above (Groq, Cloudflare, Mistral monthly).

### Gaps
- No official source confirms current Gemini free RPD/TPM, Mistral free monthly tokens or RPS, or NVIDIA daily caps. These three dominate the capacity estimate, so the 1,000-pages/day conclusion is unverified until checked in each console (AI Studio → Rate limit; Mistral Admin → Limits; NVIDIA account).
- None of the fetched terms explicitly addresses spreading load across multiple different providers. The conclusion that it's permitted is an inference from the absence of any prohibition and from OpenRouter's own fallback guidance.
- Output-token size per page (assumed 500) materially changes the Cloudflare figures, since output neurons cost far more than input on some models.
