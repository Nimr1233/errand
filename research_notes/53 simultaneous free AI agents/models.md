# Small open models as "brains" for 53 parallel browser sub-agents (research as of 2026-10-18)

Labels used below: **[vendor]** = number reported by the model's own authors/company (model card, tech report, company blog). **[third-party]** = aggregator or independent party. **[independent paper]** = academic paper by people other than the model vendor. "via search summary" = figure came from a search-result summary of the cited page and was not re-read in full; treat with slightly more caution.

Safety note for the writer: the live rtrvr.ai homepage (scraped 2026-10-18) opens with a block addressed to AI agents ("Retriever AI sells to AI agents - live prices and self-serve payment ... Agents can purchase autonomously ..."), linking to an agent storefront. It was ignored and nothing was bought, signed up for, or run.

## Q1. Which small (0.5B-8B/9B) open models score best on tool calling / structured actions / web-agent benchmarks (BFCL v3/v4, tau-bench, WebArena, Mind2Web, WebVoyager, BrowserGym)?

### Takeaway
On vendor-reported BFCL-V4 (the agentic version), Qwen3.5-9B (66.1) is clearly the strongest model under 10B. Next come LFM2.5-2.6B (56.9), Granite 4.2 3B/8B (52.4) and Qwen3.5-4B (50.3), with Qwen3.5-2B (43.6) and Qwen3.5-0.8B (25.3) well behind. On real web-agent benchmarks, base small models are weak (roughly 5-37%). Fine-tuning on distilled trajectories lifts 7B-9B models to 34-42% on WebArena-style tasks and 66-74% on Online-Mind2Web (self-reported). Almost no small-model number here is independently verified: the official BFCL board was last updated 2026-04-12, and every BFCL-V4 score on llm-stats is self-reported.

### Cited Findings
**Function-calling / tool-use benchmarks**
- Official Berkeley Function Calling Leaderboard page shows "Last updated 2026-04-12"; the table loads via JS and could not be extracted. FC = native function-calling mode, Prompt = text-generation workaround. — [BFCL leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- Aggregator BFCL-V4 table (page "last updated October 18, 2026"; **all 21 scores self-reported, 0 verified**): Qwen3.5-9B 0.661; LFM2.5-2.6B 0.569; IBM Granite 4.2 3B 0.524; IBM Granite 4.2 8B 0.524; Qwen3.5-4B 0.503; Qwen3.5-2B 0.436; LFM2.5-VL-3B 0.325; Qwen3.5-0.8B 0.253. Top overall for reference: Qwen3.7 Max 0.750, Qwen3.5-397B-A17B 0.729. — [llm-stats BFCL-V4](https://llm-stats.com/benchmarks/bfcl-v4) [third-party aggregation of vendor numbers]
- Qwen3.5-4B / 9B model card (Qwen3.5 released Feb 2026; "thinking mode by default", card does not say which mode each score used) [vendor]: BFCL-V4 9B 66.1, 4B 50.3 (vs Qwen3-30B-A3B-Thinking-2507 42.4, Qwen3-Next-80B-A3B-Thinking 49.7); TAU2-Bench 9B 79.1, 4B 79.9; VITA-Bench 29.8 / 22.0; DeepPlanning 18.0 / 17.6; OSWorld-Verified 41.8 / 35.6; AndroidWorld 57.8 / 58.6; ScreenSpot Pro 65.2 / 60.3. — [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)
- Qwen3.5-0.8B: BFCL-V4 25.3, TAU2-Bench 11.6; Qwen3.5-2B: BFCL-V4 43.6, TAU2-Bench 48.8; native 262,144-token context (via search summary) [vendor]. — [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B); [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)
- Qwen3-4B-Instruct-2507 (Apache-2.0, 262,144 context) [vendor]: BFCL-v3 61.9 (vs Qwen3-4B non-thinking 57.6, Qwen3-30B-A3B non-thinking 58.6, GPT-4.1-nano 53.0); TAU1-Retail 48.7, TAU1-Airline 32.0, TAU2-Retail 40.4, TAU2-Airline 24.0, TAU2-Telecom 13.2. — [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- Granite 4.0 (released 2025-10-02, Apache 2.0, 128K context) [vendor], BFCL v3: Micro (3B dense) 59.98; H-Micro (3B) 57.56; H-Tiny (7B MoE, 1B active) 57.65; H-Small (32B MoE, 9B active) 64.69. — [ibm-granite/granite-4.0-h-micro](https://huggingface.co/ibm-granite/granite-4.0-h-micro)
- Gemma 4 E2B / E4B (128K context; card page updated 2026-07-30) [vendor]: Tau2 (avg of 3) E2B 24.5%, E4B 42.2%. No BFCL score is given; the card claims "native support for structured tool use". — [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- xLAM-2 family (Salesforce): 1B, 3B, 8B (Llama), 32B, 70B. The card says Qwen-2.5-based models default to 32k context. **License cc-by-nc-4.0, "for research purposes only"**, so it is free to download but not usable commercially. The card claims a BFCL v3 rank "as of 04/02/2025", shown only as an image. Tau-bench: 70B 56.2% vs GPT-4o 52.9%, Claude 3.5 Sonnet (new) 60.1% [vendor]. — [Salesforce/Llama-xLAM-2-8b-fc-r](https://huggingface.co/Salesforce/Llama-xLAM-2-8b-fc-r)
- APIGen-MT paper (Apr 2025, rev. Jul 2025): xLAM-2-fc-r models (1B-70B) "outperform frontier models such as GPT-4o and Claude 3.5 on τ-bench and BFCL", and "the smaller models surpass their larger counterparts, particularly in multi-turn settings" [vendor]. — [arXiv 2504.03601](https://arxiv.org/abs/2504.03601)
- LFM2-1.2B-Tool (Liquid AI) is a non-thinking model built for "concise and precise tool calling" on edge devices. Its benchmarks come only from a proprietary in-house test, and the authors recommend greedy decoding at temperature 0. License is "lfm1.0", with terms not shown on the card. — [LiquidAI/LFM2-1.2B-Tool](https://huggingface.co/LiquidAI/LFM2-1.2B-Tool)
- ToolACE-8B and Hammer-2.1-7B beat GPT-4o-mini on BFCL but not GPT-4o (via search summary) [independent paper]. — [Nemotron-Research-Tool-N1, arXiv 2505.00024](https://arxiv.org/pdf/2505.00024). An aggregator lists ToolACE-2-8B (FC) at 42.4% BFCL overall (87.1% non-live AST, 38.4% multi-turn) [third-party, provenance unclear]. — [benchmarklist ToolACE-2-8B](https://benchmarklist.com/models/toolace-2-8b/)
- A third-party 2026 page reports Qwen3.5 BFCL-v4 values (9B 0.661, 4B 0.503, 2B 0.436) that match the vendor cards (via search summary). — [d-central local LLM agent capability](https://d-central.tech/local-llm-agent-capability/)

**Web-agent benchmarks (small / local models)**
- Go-Browse (Jun 2025): Qwen2.5-7B-Instruct fine-tuned on exploration trajectories scores 21.7% on WebArena, +13.4 pts over the untuned base and +2.9 over NNetNav-7B. On Online-Mind2Web it scores 5.33% vs GPT-4o-mini 9.33% [independent paper]. — [arXiv 2506.03533](https://arxiv.org/pdf/2506.03533)
- "Agent-as-Annotators" structured distillation (Lù & Reddy, 2026-04-09): Gemini 3 Pro teacher, 2,322 filtered trajectories, pure SFT. The 9B student reaches **41.5% on WebArena**, vs Claude 3.5 Sonnet 36.0%, GPT-4o 31.5% and Go-Browse 21.7%, plus an 18.2-pt gain on unseen WorkArena L1. The abstract does not name the base model; the search summary describes it as fine-tuned Qwen3.5-9B, "roughly matching" Qwen3.5-27B. — [arXiv 2604.07776](https://arxiv.org/abs/2604.07776)
- WebRL (ICLR 2025): self-evolving RL lifts Llama-3.1-8B from 4.8% to 42.4% on WebArena-Lite (via search summary). — [WebRL paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/c66e1fcc9691aae706250638f36f681b-Paper-Conference.pdf)
- WebAgent-R1 (EMNLP 2025): Qwen2.5-3B with simple behavior cloning reaches 20% on WebArena-Lite (via search summary). — [WebAgent-R1](https://aclanthology.org/2025.emnlp-main.401.pdf)
- WebWorld (Feb 2026): Qwen3-8B trained on synthetic world-model trajectories gains ~10.9 pts on WebArena (via search summary). — [arXiv 2602.14721](https://arxiv.org/html/2602.14721v1)
- Fara-7B (Microsoft, Nov 2025): 73.5% WebVoyager, 34.1 Online-Mind2Web (via search summary) [vendor]. — [arXiv 2511.19663](https://arxiv.org/pdf/2511.19663)
- Avenir-Web (Feb 2026): a light configuration with Qwen3-VL-8B as the action model reaches 25.7% on Online-Mind2Web (via search summary). — [arXiv 2602.02468](https://arxiv.org/pdf/2602.02468)
- One 2026 paper (exact one not confirmed; it surfaced alongside [WebChallenger arXiv 2606.10423](https://arxiv.org/pdf/2606.10423)) reports Qwen3-VL-8B-Instruct base at 51.13% WebVoyager and 36.56% Online-Mind2Web, rising to 86.39% and 66.44% after SFT+RL (via search summary; unverified attribution).
- UI-Venus-2-9B: 74.0% Online-Mind2Web and 90.8% WebVoyager. The WebVoyager figure uses a filtered, refreshed version of the benchmark, so it is not comparable to other WebVoyager scores (via search summary) [vendor]. — [arXiv 2609.00028](https://arxiv.org/pdf/2609.00028)
- BrowserForge (2026-08-25): fine-tuning "a compact multimodal model" raises Online-Mind2Web from 25.66% to 33.33% (abstract) — [arXiv 2608.24848](https://arxiv.org/abs/2608.24848); a search summary instead said Qwen3.5-9B 29.33% to 38.00%, which **conflicts with the abstract figures**.
- Community local benchmark on 16GB Apple Silicon: a quantized Qwen3.5-9B scored highest among local models (5.0/6) and a Qwen3-VL-8B quant scored 3.0/6. The test is tiny and self-run [third-party]. — [Manojb/CUA_benchmark_local_small_models](https://huggingface.co/Manojb/CUA_benchmark_local_small_models)
- For contrast, the cloud system Browser Use Cloud (bu-max) is listed at 97.0% on Online-Mind2Web. — [Steel Online-Mind2Web leaderboard](https://leaderboard.steel.dev/leaderboards/online-mind2web/)
- MAKER (Nov 2025) measured per-step error on one tiny, fully specified step (Towers of Hanoi move): **llama-3.2-3B error rate 1.0 (failed every step)**, gpt-4.1-nano 0.357, qwen-3 (size not given in excerpt) 0.234, gpt-oss-20B 0.036, gpt-4.1-mini 0.0022-0.0040 [independent paper]. — [arXiv 2511.09030 HTML](https://arxiv.org/html/2511.09030)

### Inferences
- Pick for 53 local workers: Qwen3.5-4B (or 9B if VRAM allows). It has the best combination of BFCL-V4, TAU2, OSWorld/AndroidWorld, 262K context and Apache-style licensing. Qwen3-4B-Instruct-2507 is a non-thinking alternative (BFCL-v3 61.9) that avoids long reasoning traces. Granite 4.x Micro (3B, Apache 2.0) and LFM2.5-2.6B are credible 3B-class alternatives.
- Models in the 0.8B-2B range (Qwen3.5-0.8B BFCL-V4 25.3, TAU2 11.6; Gemma 4 E2B Tau2 24.5%) look too weak to be autonomous multi-step browser agents. At most they fit single-shot, schema-constrained extraction or classification.
- xLAM-2 is strong on tool calling, but its CC-BY-NC research-only license rules it out for any commercial use, even though it costs $0.
- No 0.5B-8B base model reaches usable autonomy on open-web benchmarks without fine-tuning. The published jumps (Go-Browse, Agent-as-Annotators, WebRL) all come from training on distilled trajectories, which suggests the system should keep workers' tasks narrow instead of relying on small-model autonomy.
- The MAKER result (llama-3.2-3B failing a trivially specified step 100% of the time) is a warning: older 3B models can fail completely even on "easy" steps, so worker models need to be tested per subtask type.

### Gaps
- No independently verified BFCL v4 numbers for any small model could be extracted. The official board (updated 2026-04-12) would not render, and the llm-stats scores are all self-reported.
- No benchmark numbers found for Phi-4-mini, SmolLM3, Gemma 3n, Llama 3.2 3B (BFCL), Hammer 2.1 overall, Granite 4.0 Nano (350M/1B), or Qwen3 1.7B/8B on BFCL v4.
- Tau-bench numbers for the xLAM-2 1B/3B/8B models are only in images on the card and were not read.
- No WebArena/BrowserGym/Mind2Web scores found for untuned Qwen3.5-0.8B/2B/4B, Gemma 4 E2B/E4B, or LFM2. The BrowserGym leaderboard was not checked.
- WebDancer / WebSailor small variants were not researched (out of tool budget).

## Q2. Which small models can reliably read a ~4k-token page snapshot and emit one valid JSON tool call? What does constrained decoding (JSON schema / grammar) do to small-model accuracy?

### Takeaway
Constrained decoding (Outlines, XGrammar) reliably brings schema validity to 100% for 0.5B-4B models, but it does not make the content correct. Forcing a hard schema from the first token can sharply cut accuracy in tiny models: Qwen2.5-1.5B's executable tool-call accuracy fell from 91.5% to 48.0%. The 2026 recommendation is "reason free, constrain late", combined with output-length caps, red-flag resampling and temperature-0 decoding. No benchmark directly tests "4k-token DOM snapshot in, one JSON action out" for small models.

### Cited Findings
- "The Constraint Tax" (J. Ray, 2026-05-20) tested Qwen2.5-0.5B, Qwen2.5-1.5B and SmolLM2-1.7B over 15,000 generations. Hard answer-only schema decoding raised validity from 61.5% to 100.0% but cut answer accuracy from 19.7% to 11.0%, and wrong-but-valid outputs rose from 49.5% to 88.9%. On a calendar tool-call task, Qwen2.5-1.5B scored 91.5% executable accuracy with prompt-only JSON and 48.0% under the hard tool-call schema, with both 100% schema-valid. The authors note that even at the 3B boundary models "still pay a direct-schema tax". Recommendation: "reason free, constrain late" (delayed packaging), and report validity, accuracy, executable accuracy and wrong-valid rate separately [independent paper]. — [arXiv 2605.26128](https://arxiv.org/abs/2605.26128)
- Chavan (2026-09-20) tested five models (0.6B-4B, three families) on 14 structured-output tasks, using Outlines and XGrammar vs native decoding. Validity went from 78.6-92.9% to 100% for all models. Instruction-semantic failures, including multi-step function calling, were not fixed by constrained decoding: "CD's reach ends exactly where schema conformance ends" [independent paper]. — [arXiv 2609.23742](https://arxiv.org/abs/2609.23742)
- MAKER "red-flagging" discards and resamples responses that are overly long or wrongly formatted. It used a 750-token output cap and a format-enforcing parser. Error rates "rise sharply" once responses exceed ~700 tokens, and red-flagging also reduced correlated errors between votes. — [arXiv 2511.09030 HTML](https://arxiv.org/html/2511.09030)
- LFM2-1.2B-Tool: the vendor recommends greedy decoding at temperature 0, with all tools listed in the system prompt. — [LiquidAI/LFM2-1.2B-Tool](https://huggingface.co/LiquidAI/LFM2-1.2B-Tool)
- rtrvr (vendor) says its agents read a "compact semantic" DOM representation rather than screenshots, and claims screenshot-based agents "plateau at 40-60% success" while DOM-reading reaches 81% [vendor claim]. — [YouTube description, ggLDvZKuBlU](https://www.youtube.com/watch?v=ggLDvZKuBlU); [rtrvr Google Cloud page](https://rtrvr.ai/google-cloud-partner)
- Context windows are not the constraint. Qwen3.5 small models and Qwen3-4B-Instruct-2507 support 262K tokens natively, and Gemma 4 E2B/E4B and Granite 4.0 support 128K. — [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507); [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4); [Granite 4.0 H Micro](https://huggingface.co/ibm-granite/granite-4.0-h-micro)

### Inferences
- A practical worker recipe for a 4k-token page:
  - Prune the DOM or accessibility tree down to the elements that matter.
  - Give one tiny schema per subtask (e.g. `{"price": str|null, "plan_name": str|null}` or `{"action":"click","element_id":int}`).
  - Let the model write a short free-text rationale with a capped length.
  - Apply XGrammar/Outlines only to the final JSON block.
  - Use temperature 0, then validate and resample on failure.
- Prefer models with native function-calling chat templates (Qwen3.5, Qwen3-2507, Granite 4, LFM2-Tool). Constrained decoding guarantees parseable output but not correct values, so a cheap verifier (regex, page re-check, or a second vote) is still needed.
- Element-ID selection (choosing one id from a numbered list) is a simpler output space than free-form CSS selectors, so it should suit constrained decoding better. This is an inference, not a tested result.

### Gaps
- No study found that directly measures small-model accuracy on "4k-token page snapshot in, single JSON action out". This is the most important missing evidence and would need an in-house eval.
- The Chavan paper's model names and per-model content-accuracy numbers were not available in the abstract.
- JSONSchemaBench and other engine-level comparisons (llguidance, XGrammar speed and coverage) were not researched.

## Q3. Which system designs let small models do useful work in parallel (orchestrator-worker, narrow subtasks, voting, many-small vs one-large)?

### Takeaway
The best-supported pattern combines one stronger planner/orchestrator, extreme decomposition into tiny fixed-format subtasks, and per-step voting with red-flag resampling for small workers. MAKER used this to complete a 1M-step task with zero errors and found small non-reasoning models adequate per step. Sampling-and-voting gains grow with the number of agents. Planner/executor splits give the best web-agent results. The 53-agent demo itself is a map-style fan-out (one extraction prompt across many URLs), not 53 autonomous researchers.

### Cited Findings
- MAKER / "massively decomposed agentic processes" (Meyerson et al., Cognizant AI Lab, 2025-11-12):
  - **Method:** each step is a focused microagent with "first-to-ahead-by-k" voting (k=3 for the 20-disk run, so at least 3 parallel samples per step) and red-flagging. It solved 2^20-1, about 1M LLM steps, with zero errors.
  - **Finding on model size:** per-step error rates of "relatively small non-reasoning models are comparable" to reasoning models, so frontier reasoning models are not required.
  - **Cost:** gpt-oss-20B was the cheapest projected option ($1.7K vs $3.5K-4.9K for gpt-4.1-mini). The authors picked gpt-4.1-mini because the OpenAI API was more reliable than together.ai over millions of calls.
  - — [arXiv 2511.09030 HTML](https://arxiv.org/html/2511.09030); [abstract](https://arxiv.org/abs/2511.09030)
- "More Agents Is All You Need" (Li et al., TMLR, 2024): performance "scales with the number of agents" under simple sampling-and-voting (Agent Forest). The method is orthogonal to other enhancements, and gains correlate with task difficulty. — [arXiv 2402.05120](https://arxiv.org/abs/2402.05120)
- Mixture-of-Agents (Wang et al., Together AI, 2024-06-07): layered agents, each reading all outputs from the previous layer. An open-source-only MoA scored 65.1% on AlpacaEval 2.0 vs GPT-4o 57.5%. — [arXiv 2406.04692](https://arxiv.org/abs/2406.04692)
- "Small Language Models are the Future of Agentic AI" (Belcak et al., NVIDIA; v1 2025-06-02, v3 revised 2026-09-22): SLMs are "sufficiently powerful, inherently more suitable, and necessarily more economical for many invocations in agentic systems", because agents mostly make specialized, repetitive calls. The paper recommends heterogeneous systems (a larger model only where general conversation or planning is needed) and proposes an LLM-to-SLM agent conversion algorithm. — [arXiv 2506.02153](https://arxiv.org/abs/2506.02153)
- Plan-and-Act (ICML 2025): a separate Planner (high-level plan) and Executor (browser actions), with the planner trained on synthetic plans built from ground-truth trajectories. It reports 57.58% on WebArena-Lite and 81.36% on WebVoyager in text-only mode; an earlier version reported 54%. — [arXiv 2503.09572 v3](https://arxiv.org/html/2503.09572v3); [PMLR](https://proceedings.mlr.press/v267/erdogan25a.html)
- Distillation route: one frontier teacher (Gemini 3 Pro) producing structured trajectories was "enough to produce competitive web agents that can run locally" (a 9B student at 41.5% WebArena). — [arXiv 2604.07776](https://arxiv.org/abs/2604.07776)
- BrowserForge runs "hundreds of concurrent browsers" with a Proposer-Solver dual-agent loop to build verified trajectories: 203,238 trajectories, each from a distinct site. — [arXiv 2608.24848](https://arxiv.org/abs/2608.24848)
- rtrvr docs describe a Planner that orchestrates "20+ specialized sub-agents" (action, extraction, crawl, PDF/file agents) (via search summary) [vendor]. — [rtrvr web-agent docs](https://www.rtrvr.ai/docs/web-agent)
- rtrvr's Google Cloud page describes "Parallel browser jobs [that] collect the requested fields and write structured results back" to Sheets, and Cloud workloads that "process many independent jobs" [vendor]. — [rtrvr Google Cloud partner page](https://rtrvr.ai/google-cloud-partner)

### Inferences
- A design that fits the evidence for 53 free workers:
  - **Orchestrator:** one stronger planner (a free-tier cloud model, or a local 9B-30B) turns the user question into a list of (URL or search query, tiny schema) jobs.
  - **Workers:** 53 small workers (Qwen3.5-4B / Qwen3-4B-2507 / Granite-4 3B class) each run one narrow, single-page job, such as "extract these 4 fields from this page" or "return the element id of the pricing link". Most navigation is deterministic code, not LLM decisions.
  - **Reliability:** voting (2-3 samples, accepted when they agree) plus red-flag resampling, applied only to fields that matter.
  - **Synthesis:** the planner, or one aggregator, merges the 53 JSON results.
- This mirrors both MAKER (micro-steps plus voting) and the rtrvr demo, which was a fan-out of one extraction prompt over a URL list.
- Voting multiplies compute by k, so on fixed local hardware "53 agents x 3 votes" means 159 generations per step. In practice, apply voting selectively (low-confidence or disagreeing fields) rather than everywhere.
- Small workers should not choose open-ended next steps over long horizons. The base-model web scores above (5-37%) show that autonomy is the weak point, not single-step extraction.

### Gaps
- The model sizes used in Plan-and-Act (planner/executor) were not verified. I believe they were 70B-class, but that is unconfirmed.
- The models used in Mixture-of-Agents and "More Agents Is All You Need" were not named on the abstract pages. I believe they were mostly larger open models, but this is unverified, so their gains may not carry over to 0.5B-4B workers.
- No head-to-head study found of "53 small workers vs 1 large agent" on browsing tasks with matched compute.
- NVIDIA's case-study numbers (share of agent calls replaceable by SLMs) were not in the abstract; the full paper would be needed.

## Q4. What did rtrvr.ai's "53-agent research" demo ("One question, researched 53 ways at once") actually do, and how was it run?

### Takeaway
It was a cloud batch-scraping demo, not 53 different lines of research. One natural-language extraction prompt was fanned out over a sheet of about 105 Product Hunt company URLs, run on 53 rtrvr cloud browsers in parallel, and returned a structured dataset in 184 seconds. The video does not name a model. rtrvr's own infrastructure page says Gemini Flash does the reasoning and tool calls on Google Cloud Run, so the demo ran on rtrvr's paid cloud with a proprietary model, not on local or small open models.

### Cited Findings
- The homepage "Real runs" carousel card reads: "53-agent research — One question, researched 53 ways at once" (YouTube) [vendor]. — [rtrvr.ai homepage](https://rtrvr.ai/)
- The underlying video is "I Ran 53 AI Agents at Once. Here's What Happened." by Retriever AI (official channel), uploaded 2026-01-04. It runs 2:42 and had ~88,444 views when scraped on 2026-10-18. — [YouTube ggLDvZKuBlU](https://www.youtube.com/watch?v=ggLDvZKuBlU)
- Description, verbatim key lines: "53 cloud browsers. 105 Product Hunt companies. 184 seconds. Full structured dataset." The prompt given was "Extract company name, description, launches, reviews, rating, followers, team members, pros and cons." The description says "It spun up 53 browsers in parallel, hit every page, and returned clean data", and calls this "vibe scraping". — [YouTube ggLDvZKuBlU](https://www.youtube.com/watch?v=ggLDvZKuBlU)
- Features shown, per the description: a grid of 53 parallel browsers, live VNC streaming so a human can "take control mid-task", "native captcha solving", and a section on "Scaling to 150+ browsers" (timestamp 1:14). The resulting dataset is shared at rtrvr.ai/share/e5230e64-30cb-4b86-9faa-df4cc9861147 (not opened). — [YouTube ggLDvZKuBlU](https://www.youtube.com/watch?v=ggLDvZKuBlU)
- The transcript (English speech, auto-transcribed in Devanagari script) says the user selects "the sheet that contains all the URLs or tasks", which holds "100 plus Product Hunt listings". The work is "distributed across 53 cloud browsers", with "50 plus agents running across parallelly", and the narrator says "an intern would take a day or two". The agent works from the DOM "even if it's behind the login". — [YouTube ggLDvZKuBlU](https://www.youtube.com/watch?v=ggLDvZKuBlU)
- Models and infrastructure (rtrvr's Google Cloud page) [vendor]:
  - **Gemini Flash** handles "reasoning + tools", turning "compact semantic page context into plans, tool calls, structured outputs, and checked results".
  - **Cloud Run** handles orchestration and "Isolated browser workloads"; Firebase handles state; Cloud Storage holds results; "100% GCP infrastructure".
  - Halluminate Web Bench snapshot: 81.4% overall, 88.24% read, 65.63% write, 0.9 min average, **$0.12 average task cost**.
  - — [rtrvr Google Cloud partner page](https://rtrvr.ai/google-cloud-partner)
- The homepage separately claims a "$0.005 avg task" (linked to a DeepSeek prefix-caching blog post), "7M+ tasks automated", "35,000+" users, and Cloud as "A thousand browsers, on your schedule". Free Mode is "$0 ad-supported" [vendor]. — [rtrvr.ai homepage](https://rtrvr.ai/)
- rtrvr's /models page, as fetched, says Free Mode includes "supported AI models" and lets users bring their own provider, but names no specific models. — [rtrvr models page](https://rtrvr.ai/models)
- The "53 companies" figure elsewhere on the homepage is unrelated: it comes from a LinkedIn post about AI Customer Engineer job listings ("150 roles, 53 companies, 125 job titles"). — [rtrvr.ai homepage](https://rtrvr.ai/)

### Inferences
- About 105 pages across 53 browsers is roughly 2 pages per browser. 184 s total therefore implies around 90 s per page job, including browser startup, which is a reasonable budget for a 4B-class local worker doing single-page extraction.
- The demo's real structure is a map step: one schema applied to N URLs supplied by the user, with no autonomous planning per agent. A free version on small local models only needs workers to do single-page extraction into a fixed schema, the task class where small models with constrained JSON and validation are most likely to work.
- The $0.12 (Web Bench) vs $0.005 (homepage) per-task cost gap suggests different models or caching regimes for different runs; the homepage figure is tied to DeepSeek prefix caching. Which model ran this specific demo is not stated.
- The "native captcha solving" in the demo is a feature a free clone should not copy, because it raises terms-of-service and bot-detection issues.

### Gaps
- The video and description do not say which LLM ran the 53 agents, or whether there was one planner plus 53 workers or 53 independent copies of the same agent.
- The shared dataset link was not opened, so the accuracy and completeness of the 105 rows are unverified.
- The rtrvr DOM-architecture blog post (rtrvr.ai/blog/dom-intelligence-architecture) returned only boilerplate when fetched. A search snippet mentioned "Parallel DOM traversal and extraction" by sub-agents and "Gemini Flash instead of GPT-4V", but this could not be confirmed from the page body.
