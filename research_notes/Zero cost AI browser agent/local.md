# Running the browser-agent AI locally at $0 on this laptop (research as of 2026-10-18)

Hardware under study (user-measured): Windows 11, Intel i5-10500H (6C/12T), 16 GB RAM, NVIDIA RTX 3060 Laptop GPU (likely 6 GB; Windows reported 4 GB), Intel UHD iGPU, 30 GB free disk, Chrome 155.
Workload: rtrvr.ai-style Chrome extension agent (accessibility-tree snapshot up to ~15k tokens -> one tool call per step) plus bulk extraction over ~1,000 pages at ~5k input tokens per page.

Everything below is free (Chrome built-in AI, WebLLM, Ollama, llama.cpp, open-weight models). Dates are given per claim. "Experimental" / "flag" items are flagged.

## Q1. Chrome built-in AI (Gemini Nano via the Prompt API): status, requirements, limits, can an extension use it today?

### Takeaway
Yes for extensions: the Prompt API has been stable for Chrome extensions since Chrome 138 (no flag, no origin trial), and it supports JSON-schema-constrained output plus image/audio input. But it is a poor fit as the main agent brain here: the last measured context window was only 6,144 tokens (far below a 15k snapshot), native tool calling is not shipped (only prototyped), and on this hybrid-GPU laptop Chrome may not use the RTX 3060 by default. Treat it as an optional helper for small jobs (classifying, short extraction), not as the planner.

### Cited Findings
- Status table (Chrome docs): Prompt API is "stable" for Chrome Extensions from Chrome 138; for web pages it was origin-trial with "Chrome 148 intent to ship" listed. Translator, Language Detector, Summarizer are stable at 138 for both web and extensions; Writer, Rewriter, Proofreader are origin/developer trials. Page header says last updated 2025-09-12 (its footer date is inconsistent) — [Chrome for Developers: Built-in AI APIs](https://developer.chrome.com/docs/ai/built-in-apis)
- The Prompt API doc (last updated 2026-08-26) tells extension developers to remove the expired origin-trial permission `"permissions": ["aiLanguageModelOriginTrial"]`, i.e. extensions no longer need a trial — [Chrome for Developers: Prompt API](https://developer.chrome.com/docs/ai/prompt-api)
- The original extension origin trial ran Chrome 131 to 136 (announced Nov 2024), now expired — [Chrome blog: Prompt API for Chrome Extensions origin trial](https://developer.chrome.com/blog/prompt-api-origin-trial)
- A May 2026 third-party article claims Chrome 148 made the Prompt API stable for ordinary web pages; I could not confirm this against an official Chrome release note, so treat as unverified — [pasqualepillitteri.it](https://pasqualepillitteri.it/en/news/3145/gemini-nano-chrome-built-in-ai-client-side-en)
- Hardware requirements (official): Windows 10/11, macOS 13+, Linux, or ChromeOS on Chromebook Plus; at least 22 GB free on the volume holding the Chrome profile (model is deleted if free space drops below 10 GB after download); GPU with "strictly more than 4 GB of VRAM", OR CPU path with 16 GB RAM or more and 4 CPU cores or more; unmetered network for the first download only; audio input requires a GPU; Android/iOS not supported — [Chrome for Developers: Get started with built-in AI](https://developer.chrome.com/docs/ai/get-started); same list in [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api)
- Model download size: Google stated "approximately 1.5 GB to 2.4 GB" (measured in a July 2025 write-up on Chrome 137/138) — [swyx: Gemini Nano in Chrome](https://www.swyx.io/gemini-nano); third-party 2026 sources say roughly 2.7-4 GB (conflicting, unverified) — [pasqualepillitteri.it](https://pasqualepillitteri.it/en/news/3145/gemini-nano-chrome-built-in-ai-client-side-en)
- Context window: the official doc gives no fixed number; read `session.contextWindow` and `session.contextUsage`; on overflow a `QuotaExceededError` exposes `requested` and `contextWindow`; older turns are dropped but the system prompt is kept — [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api). The explainer renamed `inputQuota` to `contextWindow` — [webmachinelearning/prompt-api explainer](https://github.com/webmachinelearning/prompt-api)
- Measured context: `session.inputQuota` returned 6,144 tokens ("6k token context") on Chrome 137/138, July 2025 — [swyx](https://www.swyx.io/gemini-nano). An older (~2024) Chromium dev-preview thread cited 1,024 tokens per prompt / 4,096 per session (superseded) — [chrome-ai-dev-preview-discuss](https://groups.google.com/a/chromium.org/g/chrome-ai-dev-preview-discuss/c/WO2NIK_9Ue4)
- Structured output: pass a JSON Schema via `responseConstraint` to `prompt()` / `promptStreaming()`; schema tokens count against the context window (`measureContextUsage()`), and `omitResponseConstraintInput` can drop the schema from the input — [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api). The explainer also allows a `RegExp` constraint; unsupported schema features throw `NotSupportedError`, non-compliant output throws `SyntaxError` — [explainer](https://github.com/webmachinelearning/prompt-api)
- Tool calling: the explainer defines a `tools` option (name, description, inputSchema) in "open-loop" mode where the model returns `LanguageModelToolCall` objects and the app runs them; automatic execution is "a planned future extension". The explainer lists Chromium as "prototyping behind a flag". The official Chrome Prompt API doc does not mention tools — [explainer](https://github.com/webmachinelearning/prompt-api); [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api). EXPERIMENTAL / not in stable.
- Multimodal: image inputs (HTMLImageElement, canvas, video frames, Blob, etc.) and audio inputs (AudioBuffer, ArrayBuffer, Blob); output text only; declare via `expectedInputs` — [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api)
- Languages: en, ja, es, de, fr ("from Chrome 149") — [Get started](https://developer.chrome.com/docs/ai/get-started); [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api)
- Sampling: extensions may set `topK` and `temperature` (both or neither); `LanguageModel.params()` example shows defaultTopK 3, maxTopK 128, defaultTemperature 1, maxTemperature 2. Web pages need a sampling-parameters origin trial (`samplingMode`, Chrome 148) — [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api)
- Restrictions: not available in Web Workers; cross-origin iframes need `allow="language-model"`; first session creation (model download) needs user activation — [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api)
- Quality observation (2025): few-shot JSON worked for a simple extraction, but instruction following was weak (output omitted a required `name` field) before `responseConstraint` was used — [swyx](https://www.swyx.io/gemini-nano)
- Hybrid-GPU caveat: on Windows, Chrome uses the same adapter it uses for everything else, usually the integrated GPU on laptops; WebGPU `powerPreference` has no effect; `chrome://flags/#force-high-performance-gpu` (flag, experimental) or the per-app Windows graphics setting forces the discrete GPU — [Chrome WebGPU troubleshooting tips](https://developer.chrome.com/docs/web-platform/webgpu/troubleshooting-tips); Chromium issue 369219127 referenced in [transformers.js PR #1199](https://app.semanticdiff.com/gh/huggingface/transformers.js/pull/1199/overview)

### Inferences
- Does this laptop qualify? Disk: 30 GB free meets the 22 GB rule, but only just; installing Ollama models (3-8 GB each) afterwards could push free space toward the 10 GB deletion threshold. GPU: a 6 GB RTX 3060 meets "strictly more than 4 GB" if Chrome evaluates the NVIDIA GPU; if Chrome sits on the Intel UHD iGPU (default on Windows laptops), it may fall back to the CPU path, which this laptop should meet (16 GB RAM, 6 cores), though exactly 16 GB with ~15.8 GB usable is a borderline unknown. Practical check: `await LanguageModel.availability()` in an extension page on Chrome 155.
- A 6,144-token window (last measured value) cannot hold a 15k-token accessibility snapshot plus instructions. Using Nano as the agent brain would require cutting snapshots to ~3-4k tokens (interactive elements only) or a chunk-and-filter pass. The current Chrome 155 window size is unknown (see Gaps).
- Tool calls can be emulated today with `responseConstraint`: a schema like `{action: enum[click,type,scroll,extract,done], elementId: string, text?: string}` gives a reliable single tool call per step without the unshipped `tools` option.
- Best role for Nano: zero-install fallback for short, low-stakes tasks (summarize a section, classify a page, extract a few fields from a trimmed snippet). Too small a context and model for robust multi-step navigation.

### Gaps
- No official Chrome 155 release-note item about the Prompt API was found; the exact Chrome 155 `contextWindow` value for Gemini Nano was not found in any 2026 source (only the 2025 figure of 6,144).
- Whether the Prompt API works inside an extension service worker (vs. needing an extension page / offscreen document) was not confirmed; docs only say "not available in Web Workers".
- No measured Gemini Nano tokens/sec or per-request latency on any Windows laptop was found; no documented rate limits beyond the context window.
- Whether Gemini Nano's GPU check uses the discrete RTX GPU or the iGPU on Optimus laptops was not confirmed.
- A chromestatus "Prompt API: Function Calling" entry was mentioned in a search summary as "Intent to Prototype", but the entry itself was not retrieved.

## Q2. WebLLM / WebGPU in-browser models (MLC): what fits 6 GB, speed, function calling, extension support?

### Takeaway
WebLLM runs inside a Chrome extension (WebGPU in extension service workers since Chrome 124, with an official example), and several useful models fit under 6 GB (Qwen3-4B, Qwen3.5-4B, Gemma-4-E2B, Phi-4-mini, Llama-3.1-8B). But prebuilt models default to a 4,096-token context (too small for 15k snapshots), official function calling is limited to old Hermes models and marked work in progress, and on this laptop Chrome's WebGPU likely lands on the Intel iGPU unless forced. It is viable but a weaker path than a native Ollama/llama.cpp server for this workload.

### Cited Findings
- WebGPU became available in service workers and shared workers in Chrome 124; the Chrome team points to the WebLLM Chrome extension as an example of WebGPU in an extension service worker — [Chrome: What's new in WebGPU (Chrome 124)](https://developer.chrome.com/blog/new-in-webgpu-124)
- WebLLM repo ships two extension examples: `chrome-extension` (no persistent background) and `chrome-extension-webgpu-service-worker` — [web-llm examples](https://github.com/mlc-ai/web-llm/blob/HEAD/examples)
- Latest WebLLM release reported as 0.2.85, published 2026-09-08 (secondary blog, not verified against npm) — [pinggy.io blog](https://pinggy.io/blog/run_llm_in_browser_webgpu/)
- WebLLM exposes OpenAI-compatible function calling (`tools`, `tool_choice`); the official example list marks function calling "work in progress" — [web-llm examples](https://github.com/mlc-ai/web-llm/blob/HEAD/examples)
- `functionCallingModelIds` in the prebuilt config contains only Hermes models: Hermes-2-Pro-Llama-3-8B (q4f16 4,976 MB), Hermes-2-Pro-Mistral-7B (4,033 MB), Hermes-3-Llama-3.1-8B (q4f16 4,876 MB; q4f32 5,779 MB) — [web-llm src/config.ts](https://github.com/mlc-ai/web-llm/blob/main/src/config.ts) (fetched 2026-10-18)
- Prebuilt models under 6 GB VRAM (vram_required_MB, default context 4,096 unless noted) — [web-llm src/config.ts](https://github.com/mlc-ai/web-llm/blob/main/src/config.ts):
  - Qwen3-4B q4f16_1: 3,432 MB; Qwen3-8B q4f16_1: 5,696 MB (too tight for 6 GB with Chrome's own GPU use)
  - Qwen3.5-4B q4f16_1: 3,868 MB; Qwen3.5-2B: 2,245 MB; Qwen3.5-0.8B: 1,629 MB (Qwen3.5 entries use context 4,096 and max_history_size 1)
  - gemma-4-E2B-it q4f16_1: 3,387 MB
  - Phi-4-mini-instruct q4f16_1: 3,438 MB
  - Llama-3.1-8B-Instruct q4f16_1: 5,001 MB (4,096 ctx); a "-1k" variant at 4,598 MB has only 1,024 ctx
  - Qwen2.5-7B-Instruct q4f16_1: 5,107 MB; Mistral-7B-Instruct-v0.3 q4f16_1: 4,573 MB
- A third-party WebLLM extension on the Chrome Web Store says it uses WebGPU and falls back to CPU when unavailable — [Chrome Web Store: WebLLM extension](https://chromewebstore.google.com/detail/commhodlifeiacfckmmlijnnnoghnoem)
- Chrome on Windows ignores WebGPU `powerPreference` and typically uses the integrated GPU on laptops; force the discrete GPU via `#force-high-performance-gpu` (flag) or Windows per-app graphics settings — [Chrome WebGPU troubleshooting tips](https://developer.chrome.com/docs/web-platform/webgpu/troubleshooting-tips)

### Inferences
- The `vram_required_MB` figures are for the default 4k context. Raising `context_window_size` to ~16k for a 15k-token snapshot adds KV-cache memory (roughly 1-2.5 GB for a 4B model, see Q4 math), so a 4B model is the realistic ceiling in WebLLM on 6 GB; 7-8B models would only work with short contexts.
- Because official function calling covers only older Hermes models, a WebLLM agent should use JSON-schema / JSON mode output for the single tool call rather than the `tools` field.
- The user must set Chrome to "High performance" in Windows Settings > System > Display > Graphics (a user-made change) or WebLLM will run on the Intel UHD iGPU with shared memory, which would be slow and memory-limited.
- WebLLM's advantage is zero install outside Chrome (just the extension and a cached model download); its disadvantages vs Ollama are the 4k default contexts, a narrower model set, and less mature tool calling.

### Gaps
- No measured WebLLM tokens/sec on an RTX 3060 Laptop (or any 6 GB laptop GPU) was found.
- WebLLM's JSON-schema / grammar support (via XGrammar) and the exact current `response_format` options were not verified in this session.
- Running WebLLM in an MV3 offscreen document (vs. the service-worker example) was not documented in any source found.

## Q3. Ollama / LM Studio / llama.cpp local servers: which models fit 6 GB VRAM + 16 GB RAM, how good is their tool calling, and how to call Ollama from an extension?

### Takeaway
The strongest $0 option on this laptop is a native local server (Ollama or llama.cpp) running a ~4B model fully on the RTX 3060: Qwen3.5-4B (3.3-4.0 GB, tools + vision, 256K context) is the best-fitting candidate, and Gemma 4 E2B (4.6-7.5 GB download) is a second option. Qwen3.5-9B (6.6-7.6 GB) is stronger (BFCL-V4 66.1, vendor-reported) but spills past 6 GB into system RAM and slows to roughly 15-22 tok/s. A Chrome extension can call Ollama once `OLLAMA_ORIGINS` allows `chrome-extension://*`, and the default 4,096-token context must be raised or 15k snapshots get truncated.

### Cited Findings
- VRAM reading: Windows' `Win32_VideoController.AdapterRAM` is a uint32 and cannot represent more than ~4 GB, so tools that use it under-report larger cards (e.g. a 24 GB Quadro shows 4,095 MB) — [Microsoft: Win32_VideoController](https://learn.microsoft.com/en-ie/Windows/Win32/cimwin32prov/win32-videocontroller); [Lansweeper community](https://community.lansweeper.com/t5/forum/video-card-scans-on-lansweeper-video-card-ram-reported-incorrect/m-p/18275)
- Ollama CORS: by default Ollama allows cross-origin requests only from 127.0.0.1 and 0.0.0.0; extensions must be allowed explicitly, e.g. `OLLAMA_ORIGINS=chrome-extension://*,moz-extension://*,safari-web-extension://*`. On Windows, quit Ollama, set the variable in "Edit environment variables for your account", then restart Ollama — [Ollama FAQ](https://docs.ollama.com/faq) (fetched 2026-10-18)
- Ollama defaults: context window 4,096 tokens (override with `OLLAMA_CONTEXT_LENGTH`); `OLLAMA_NUM_PARALLEL` default 1; `OLLAMA_MAX_LOADED_MODELS` default 3x GPUs; memory scales with `OLLAMA_NUM_PARALLEL * OLLAMA_CONTEXT_LENGTH`; flash attention used automatically when supported (`OLLAMA_FLASH_ATTENTION`); `OLLAMA_KV_CACHE_TYPE` f16 (default), q8_0, q4_0, global for all models — [Ollama FAQ](https://docs.ollama.com/faq)
- Ollama structured outputs: pass a JSON schema in `format` to constrain the response; announced 2024-12-06; recommends temperature 0 for determinism — [Ollama blog: Structured outputs](https://ollama.com/blog/structured-outputs)
- Qwen3.5 on Ollama (page updated ~1 week before 2026-10-18): family tagged vision, tools, thinking; 256K context; downloads: 0.8b 1.2-1.3 GB, 2b 2.7-3.1 GB, 4b 3.3-4.0 GB, 9b (= latest) 6.6-7.6 GB, 27b 17-20 GB — [Ollama library: qwen3.5](https://ollama.com/library/qwen3.5)
- Qwen3.5 small dense models (0.8B/2B/4B/9B) released 2026-03-02 under Apache 2.0; vendor-reported benchmarks claim the 9B beats much larger last-gen models (not independently verified) — [InsiderLLM](https://insiderllm.com/guides/qwen-3-5-small-models-9b-beats-30b/); [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/qwen-3-5-small-models-9b-parameters-that-beat-120b)
- Gemma 4 on Ollama (updated ~2 weeks before 2026-10-18): family tagged vision, tools, thinking, audio; e2b 4.6-7.5 GB (128K ctx), e4b 6.6-9.5 GB (128K), 12b 7.7-8.0 GB (256K); readme cites "native function-calling support" — [Ollama library: gemma4](https://ollama.com/library/gemma4). Gemma 4 E2B = 2.3B effective / 5.1B with embeddings, Apache 2.0, released ~2026-03-31 to 04-02 (dates differ by source) — [Modal: gemma-4-e2b-it](https://modal.com/library/google/gemma-4-e2b-it)
- Speed on a 6 GB RTX 3060 (community-reported, runtime unstated, LM Studio benchmark page): Qwen3.5-9B Q4_K_M 15-22 tok/s; Qwen3.5-4B Q4_K_M 25-40 tok/s; VRAM headroom is the binding constraint — [markaicode: LM Studio Qwen3.5 benchmark](https://markaicode.com/benchmarks/lm-studio-qwen-benchmark/)
- llama.cpp CUDA scoreboard (Llama-2-7B Q4_0, `llama-bench`, pp512 / tg128 tokens/s): RTX 3060 12GB desktop 2,138 / 75.6 (no FA) and 2,408 / 76.9 (FA); same card on WSL2 2,111 / 72.1 and 2,408 / 75.6 (2026-08-21); RTX 4050 Laptop 6GB 1,726 / 43.7; RTX 3050 6GB 1,147 / 37.4 and 1,258 / 38.5 with FA (2026-07-15). No RTX 3060 Laptop row exists — [llama.cpp discussion #15013](https://github.com/ggml-org/llama.cpp/discussions/15013)
- Tool-calling benchmark: BFCL-V4 Qwen3.5-9B 66.1 (vendor-reported), ranked 10th of 22 on llm-stats; Qwen3.5-4B ranked 19th of 22 with no score shown; llm-stats says the board was updated Sept 2026 while another source says the Berkeley board was last updated 2026-04-12 (conflict) — [llm-stats BFCL-V4](https://llm-stats.com/benchmarks/bfcl-v4); [vdf.ai: Best local LLM for agents](https://vdf.ai/blog/best-local-llm-for-agents-tool-calling/)
- No BFCL-V4 score was found for Gemma 4 E2B/E4B; Gemma 4 larger variants are reported on Tau2 instead — [vdf.ai](https://vdf.ai/blog/best-local-llm-for-agents-tool-calling/)

### Inferences
- The "4 GB" Windows reading is almost certainly the uint32 AdapterRAM cap; the RTX 3060 Laptop GPU is a 6 GB part. Confirm with `nvidia-smi` or Task Manager > GPU 1 > Dedicated GPU memory.
- Model picks for 6 GB VRAM + 16 GB RAM:
  - Agent (15k-token snapshots): Qwen3.5-4B Q4 fully on GPU, context set to ~16k (`OLLAMA_CONTEXT_LENGTH=16384` or per-request `num_ctx`), KV cache q8_0 with flash attention to save VRAM, thinking off for speed.
  - Bulk extraction: same Qwen3.5-4B, or Qwen3.5-9B with partial CPU offload for harder pages if speed is acceptable (overnight runs).
  - Gemma 4 E2B is a reasonable alternative; E4B (6.6-9.5 GB) and 12B do not fit fully in 6 GB VRAM.
- Ollama vs llama.cpp vs LM Studio: all three run the same GGUF models on CUDA. Ollama is the simplest to call from an extension (documented `OLLAMA_ORIGINS`, JSON-schema `format`, tools API). llama.cpp's `llama-server` gives the most control (parallel slots, grammars) but its CORS and flags were not verified here.
- Disk budget: Qwen3.5-4B (~4 GB) + Qwen3.5-9B (~7 GB) + Ollama install fits in 30 GB, but combined with Gemini Nano's 22 GB-free rule, pick one stack or watch free space.

### Gaps
- LM Studio's current licence terms (free for work use?), its CORS settings, and its OpenAI-compatible tool-calling support were not researched in this session.
- llama.cpp `llama-server` CORS behaviour for `chrome-extension://` origins, `--parallel` slots, and GBNF/JSON-schema support were not verified from primary docs here.
- No measured Ollama speeds specifically for Qwen3.5-4B or Gemma 4 E2B on an RTX 3060 *Laptop* were found; the markaicode figures are community-reported and do not name the runtime.
- No independent BFCL score for Qwen3.5-4B or Gemma 4 E2B/E4B was found.
- Whether Ollama's Qwen3.5-4B tag includes a vision projector that adds VRAM even for text-only use was not confirmed.

## Q4. Realistic throughput: pages/hour for ~5k-token extraction and parallel requests on this GPU

### Takeaway
No direct benchmark exists for an RTX 3060 Laptop, but bracketing data (RTX 4050 Laptop ~1,726 tok/s prefill, RTX 3060 desktop ~2,100-2,400 tok/s prefill on a 7B Q4 model) puts a 4B model at very roughly 250-700 pages/hour for 5k-token pages, depending mostly on how many output tokens each page needs. So 1,000 pages takes about 1.5-4 hours on a 4B model, or an overnight run (roughly 6-11 hours) on a 9B model that spills into RAM. Parallel requests help decode a bit but not prefill, and each slot costs a full context of KV cache.

### Cited Findings
- Prefill / decode bracket (Llama-2-7B Q4_0, llama-bench): RTX 4050 Laptop 6GB pp512 1,726 tok/s, tg128 43.7 tok/s; RTX 3060 12GB desktop pp512 2,138-2,408 tok/s, tg128 72-77 tok/s; flash attention adds ~13% to prefill on the 3060 — [llama.cpp discussion #15013](https://github.com/ggml-org/llama.cpp/discussions/15013)
- Community decode rates on a 6 GB RTX 3060: Qwen3.5-4B Q4_K_M 25-40 tok/s; Qwen3.5-9B Q4_K_M 15-22 tok/s — [markaicode](https://markaicode.com/benchmarks/lm-studio-qwen-benchmark/)
- Ollama processes 1 request per model at a time by default (`OLLAMA_NUM_PARALLEL=1`); parallel slots multiply context memory (`NUM_PARALLEL * CONTEXT_LENGTH`) — [Ollama FAQ](https://docs.ollama.com/faq)
- Prompt processing is compute-bound and much faster than generation (desktop RTX 4090 llama-bench comparison) — [singhajit.com: LLM inference speed comparison](https://singhajit.com/llm-inference-speed-comparison/)

### Inferences
(All numbers below are my estimates from the cited bracket data, not measurements.)
- RTX 3060 Laptop prefill for a 7B Q4 model is likely between the 4050 Laptop and the 3060 desktop (~1,700-2,200 tok/s at 512 tokens), lower at 5k-15k tokens because attention cost grows; a 4B model should prefill roughly 1.5-2x faster.
- Per extraction page on Qwen3.5-4B fully on GPU (thinking off): 5k-token prefill ~2-4 s, plus output at 25-40 tok/s: ~100 output tokens -> ~5-7 s/page (~500-700 pages/hour, 1,000 pages in ~1.5-2 h); ~300 output tokens -> ~10-16 s/page (~225-360 pages/hour, 1,000 pages in ~3-4.5 h).
- On Qwen3.5-9B with partial CPU offload: decode 15-22 tok/s and slower prefill -> very roughly 20-40 s/page (~90-180 pages/hour, 1,000 pages in ~6-11 h).
- Agent step latency on a 4B model: a 15k-token snapshot is ~5-10 s of prefill plus ~1-2 s for a ~50-token tool call, so ~7-12 s per step; a 20-step task takes ~2.5-4 minutes. Shrinking the snapshot to ~4k tokens cuts this to ~3-4 s per step.
- KV-cache math (assumes Qwen3-4B-style config: 36 layers, 8 KV heads, head dim 128; not verified for Qwen3.5, which may use less): ~147 KB/token at f16, so a 16k context is ~2.4 GB (f16) or ~1.2 GB (q8_0). With ~2.5-3 GB of weights that fits in 6 GB with q8_0 KV, leaving room for maybe 2 parallel 8k slots.
- Parallelism: extraction at 5k input / short output is prefill-dominated (compute-bound), so `OLLAMA_NUM_PARALLEL=2` likely gives only a modest aggregate gain (perhaps 1.2-1.5x) and risks VRAM spill; more than 2 slots on 6 GB is unlikely to help.
- Laptop thermals and power mode (plugged in, high-performance profile) will materially change sustained throughput over multi-hour runs.

### Gaps
- No llama-bench or Ollama measurement for an RTX 3060 Laptop GPU at 5k-15k prompt lengths was found; the user should run `llama-bench -p 512,4096 -n 128` or check Ollama's `eval rate` / `prompt eval rate` with `ollama run --verbose`.
- No source measured aggregate throughput gains from `OLLAMA_NUM_PARALLEL` on a 6 GB card.

## Q5. Quality gap: where small local models fail as browser agents vs frontier models, and mitigations

### Takeaway
Generic small instruct models are weak at multi-step web navigation: Qwen2.5-7B-Instruct scored 8.3% on WebArena versus 21.7% for a web-trained 7B. Purpose-trained 7-9B agents do far better, but they mostly work from screenshots rather than accessibility trees. For this project, expect a local 4B model to be reliable at single-page extraction and simple, well-scaffolded clicks, and unreliable at long multi-step tasks. Mitigate with schema-constrained single tool calls, smaller pruned snapshots, few-shot examples, and validation/retry.

### Cited Findings
- WebArena (text-based): Qwen-2.5-7B-Instruct 8.3%, NNetNav-7B 18.8%, Go-Browse-7B 21.7% (web-trained via structured exploration; 2025 paper) — [Go-Browse, arXiv 2506.03533](https://arxiv.org/pdf/2506.03533)
- Online-Mind2Web (live sites): Fara-7B (Microsoft, 7B computer-use agent) 34.1% — [Fara-7B, arXiv 2511.19663](https://arxiv.org/html/2511.19663v1); Fara1.5-9B 63% (different evaluation setup); GUI-Owl-1.5-8B 48.6% in Microsoft's comparison — [Microsoft Research: Fara1.5](https://www.microsoft.com/en-us/research/articles/fara1-5-computer-use-agent/)
- MolmoWeb-8B (AI2, open, screenshot-only): 78.2% WebVoyager, 35.3% Online-Mind2Web, leading open-weight models at its release — [The Decoder](https://the-decoder.com/ai2s-fully-open-web-agent-molmoweb-navigates-the-web-using-only-screenshots/)
- Avenir-Web with Qwen-3-VL-8B as the action model reached 25.7% — [Avenir-Web, arXiv 2602.02468](https://arxiv.org/pdf/2602.02468)
- Benchmark caveat: the Fara1.5 figure (63%) uses a different evaluation setup than the Fara-7B figure (34.1%), so cross-paper Online-Mind2Web numbers are not directly comparable, and none of them are comparable with WebArena — [Microsoft Research: Fara1.5](https://www.microsoft.com/en-us/research/articles/fara1-5-computer-use-agent/)
- Small-model tool-calling scores: Qwen3.5-9B BFCL-V4 66.1 (vendor-reported) — [llm-stats](https://llm-stats.com/benchmarks/bfcl-v4)
- Instruction-following failure example: Gemini Nano omitted a required JSON field with prompt-only formatting (2025) — [swyx](https://www.swyx.io/gemini-nano)
- Constrained decoding is available for free locally: Ollama `format` (JSON schema) — [Ollama blog](https://ollama.com/blog/structured-outputs); Chrome `responseConstraint` (JSON schema or RegExp) — [Prompt API doc](https://developer.chrome.com/docs/ai/prompt-api)

### Inferences
- Likely failure modes for a 4B model on 15k-token accessibility trees: losing track of the goal over many steps, choosing a plausible but wrong element among many similar ones, looping (re-clicking or re-scrolling), hallucinating element IDs not in the snapshot, ignoring "done" conditions, and degraded attention over long contexts. These are consistent with the large gap between generic instruct models and web-trained agents on WebArena, but no study isolated each failure for 4B models on accessibility-tree input.
- Mitigations, roughly in order of impact:
  1. Constrain every step to one JSON object via schema (`action` enum, `elementId` restricted to IDs present in the snapshot, optional `text`), at temperature 0, thinking off. This removes format errors entirely.
  2. Shrink the snapshot: keep only visible, interactive or text-bearing nodes, collapse repeated list items, number elements compactly. Target ~2-5k tokens instead of 15k; this improves both accuracy and speed and makes Gemini Nano usable.
  3. Few-shot: 2-3 short worked examples of snapshot -> correct action in the system prompt (cached prefix).
  4. Validate and retry in code: reject IDs not in the snapshot, detect repeated identical actions (loop guard), cap steps, re-prompt with the error.
  5. Separate planner from actor: keep a short written plan / scratchpad that is re-sent each step instead of full history.
  6. For bulk extraction, skip the agent loop entirely: navigate deterministically in code, send only the page's main text plus a JSON schema; small models are much more reliable here.
- Screenshot-trained agents (Fara-7B, MolmoWeb-8B) would need vision input and ~5+ GB at Q4; they may not fit alongside a 15k context on 6 GB and do not consume accessibility trees directly.

### Gaps
- No benchmark result was found for Qwen3.5-4B, Gemma 4 E2B/E4B, or Gemini Nano on WebArena, Mind2Web, or any accessibility-tree browser benchmark.
- Two potentially relevant 2026 papers were only seen as titles and not read: "Small Reasoning Models are Instruction Followers in Function Calling" ([arXiv 2608.22472](https://arxiv.org/pdf/2608.22472)) and "OpenJarvis: Personal AI, On Personal Devices" ([arXiv 2605.17172](https://arxiv.org/pdf/2605.17172), includes a Gemma4-E4B row).
- Whether Fara-7B or MolmoWeb-8B are packaged for Ollama / GGUF and fit 6 GB was not checked.
- A search summary said one 2026 preprint questions the reliability of ~90% Online-Mind2Web scores, but the specific paper could not be identified, so that claim is not cited.
