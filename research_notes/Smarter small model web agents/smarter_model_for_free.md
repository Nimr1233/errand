# Making the small local model smarter for $0 on a 6 GB laptop GPU (as of October 20, 2026)

Scope: Errand's brain fleet. Today it runs 53 slots of Qwen3.5-2B Q4_K_M (1.2 GB) on llama-server b11718 with `-np 53 -c 217088 -fa on -ctk q8_0 -ctv q8_0 --reasoning-budget 0`, so thinking is already off and the memory cache is already q8_0. Measured: 2.66 pages/s and 4,426 MiB used. The hardware is an RTX 3060 Laptop (6 GB), i5-10500H, 16 GB RAM, Windows 11.

**Slot arithmetic used throughout (from Errand's own measurements):** total graphics memory ≈ 1,655 MiB + slots × (19.3 + tokens per slot × 8.4 ÷ 1,024). That is **52.8 MiB per 2B brain at 4,096 tokens**. About **5,800 MiB is usable** under Windows before memory spills into system RAM ([Errand report: Maximum parallel brains](C:\Users\Omer laptop\errand\reports\Maximum parallel brains on laptop GPU.md), fitted to `bench/brains-*.json`). So **1 slot is about 53 MiB**, and spare headroom at 53 slots is about 1,370 MiB, or 26 more slots.

"Measured" means someone ran a benchmark. "Vendor claim" means the model's maker reports it. "Calculated" means I worked it out from published model configs plus Errand's measured formula. Calculated numbers are not measurements.

---

## 1. Better small GGUF models for structured extraction and agent work, and whether mixed sizes fit

### Takeaway
Running 53 slots, the per-slot memory cost (cache plus running state) matters more than the size of the weights. Qwen3.5's hybrid Gated-DeltaNet design (only 1 layer in 4 keeps a growing cache) makes it far cheaper per slot than any pure-attention model. So Qwen3.5 gives the best accuracy per VRAM in this setup. **Qwen3.5-4B is a large step up from the 2B** (Intelligence Index 27 vs 16). It costs about 2.3× the weights and about 2.6× the memory per slot. Calculated: about 19 slots fit at 4k tokens, or about 28 at 2k. **"45 × 2B + 1 × 4B" does not fit in 6 GB** (calculated about 7.2 GB). About 16 × 2B + 2 × 4B fits. Speculative decoding will not speed up a 53-slot fleet.

### Cited Findings
**Qwen3.5 small family (released March 2–5, 2026; Apache 2.0; 262K context; vision built in)**
- Sizes are 0.8B, 2B, 4B and 9B, plus base versions. Artificial Analysis Intelligence Index (reasoning mode): **9B 32, 4B 27, 2B 16, 0.8B 9**. For comparison, Qwen3-4B-2507 scores 18 and Qwen3-1.7B about 13. The 4B is "the most intelligent under 5B" — [Artificial Analysis, Mar 5 2026](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- Output tokens used to run the Intelligence Index: **2B about 390M**, 4B about 240M, 0.8B about 230M, against 98M for the 27B. The 2B is the most long-winded reasoner in the family — [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- AA-Omniscience hallucination rate: 4B 80%, 9B 82%, Qwen3-4B-2507 84%. Small models mostly guess when they don't know — [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- **Qwen3.5-2B model card (Errand's current model).** Non-thinking is the default. Non-thinking scores: IFEval **61.2**, MMLU-Pro 55.3. Qwen3-1.7B scores IFEval 68.2 / MMLU-Pro 40.2, and Qwen3-4B-2507 scores **IFEval 83.4** / 69.6 in the same mode. Thinking scores: IFEval 78.6, IFBench 41.3, BFCL-V4 43.6, TAU2 48.8, MMLU-Pro 66.5. 0.8B non-thinking IFEval: 52.1 — [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)
- 2B architecture: 24 layers, laid out as 6 × (3 Gated DeltaNet + 1 Gated Attention). The attention layers have 2 KV heads at head dim 256. DeltaNet has 16 heads at dim 128 — [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)
- **Qwen3.5-4B model card.** Thinking is on by default (`enable_thinking: False` turns it off). Scores, with no mode split published: **IFEval 89.8, IFBench 59.2, BFCL-V4 50.3, TAU2 79.9, MMLU-Pro 79.1**. The 9B scores 91.5 / 64.5 / 66.1 / 79.1 / 82.5. Architecture: 32 layers = 8 × (3 DeltaNet + 1 attention). Attention has 4 KV heads at dim 256; DeltaNet has 32 V-heads at dim 128 — [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)
- Qwen3.5-4B GGUF sizes: Q4_K_M **2.74 GB**, UD-Q4_K_XL 2.91, Q5_K_M 3.14, Q6_K 3.53, Q8_0 4.48, BF16 8.42. The Unsloth repo has **no separate MTP GGUF** files — [unsloth/Qwen3.5-4B-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF)
- At 4-bit, the 9B needs about 6 GB, the 4B about 3 GB, and the 2B and 0.8B under 2 GB — [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- Qwen3-4B-Instruct-2507 config: 36 layers, all full attention, 8 KV heads at head_dim 128 — [config.json](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/main/config.json)
- No Qwen3.6 small (≤9B) models were found. Qwen3.6 seems to be 27B and 35B-A3B only, but the sources are community posts — [search summary, artificialanalysis / reddit snapshot](https://reddit.sentinel-team.org/posts/1taafs4/snapshots/2026-05-15T23%3A40%3A01.25497Z)

**Gemma 4 (released April 2, 2026; now Apache 2.0, replacing the old Gemma Terms)**
- Licence moved to Apache 2.0 — [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/google-releases-gemma-4-frontier-open-models-under-apache-2-0/)
- E2B: 2.3B effective, 5.1B with embeddings, 128K context. E2B vs E4B: MMLU-Pro 60.0 / 69.4, GPQA-D 43.4 / 58.6, **Tau2 24.5 / 42.2**, LiveCodeBench 44.0 / 52.0. No IFEval or BFCL published. Thinking is toggled with the `<|think|>` token — [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it)
- Q4_K_M sizes: E2B about **3.11 GB**, E4B about 4.98 GB (third-party listing) — [skills.cat](https://skills.cat/skills/luckyegg168/gemma-4). Unsloth gives about 4 GB (E2B) and 5.5–6 GB (E4B) total memory at 4-bit — [Unsloth Gemma 4](https://unsloth.ai/docs/models/gemma-4)
- Ollama injects a thinking token for E2B, which made it 5–10× slower than E4B on short tasks (one RTX 3070 test) — [thekodelab](https://thekodelab.com/en/posts/gemma4-e2b-vs-e4b-benchmark/)

**SmolLM3-3B (2025, Apache 2.0)**
- Non-thinking: IFEval **76.7**, BFCL 92.3, GPQA-D 35.7. The original Qwen3-4B scores 68.9 / 95.0 / 44.4, Qwen3-1.7B 74.0 / 89.5, and "Llama3.1-3B" [sic] 71.6. Thinking: SmolLM3 IFEval 71.2 vs Qwen3-4B 85.4 — [HuggingFaceTB/SmolLM3-3B](https://huggingface.co/HuggingFaceTB/SmolLM3-3B)

**Specialised extraction models**
- **NuExtract-2.0** (template-JSON extraction). 2B = Qwen2-VL-2B base, **MIT**. 4B = Qwen2.5-VL-3B base, **Qwen Research Licence (non-commercial)**. 8B = MIT. Input is the document plus a JSON template with typed fields (verbatim-string, enum, multi-label…), and missing fields return null. Temperature about 0 is recommended. Quantized variants exist on HF. Scores are published only as an image — [numind/NuExtract-2.0-2B](https://huggingface.co/numind/NuExtract-2.0-2B)
- NuExtract vendor claims: 1.5 (3.8B) "better than GPT-4o" on their English zero-shot benchmark (older, 2024). 2.0 PRO (API only, not open) beats GPT-4.1 by 9 F1 — [NuMind blog](https://numind.ai/blog/outclassing-frontier-llms----nuextract-2-0-takes-the-lead-in-information-extraction)
- **Schematron-3B / 8B** (inference.net, Sep 2025). HTML→JSON with schema, 128K context, trained on about 1M Common Crawl pages using frontier-model teachers. Open weights on HF under "permissive licenses" (not named). Vendor claim: the 8B is "just as accurate" as Gemini 2.5 Flash, graded 1–5 by Gemini 2.5 Pro — [inference.net blog](https://inference.net/blog/schematron/). Schematron V2 (Apr 2026) weights are **closed**, API only — [inference.net V2](https://inference.net/blog/schematron-v2/)
- **LFM2-1.2B-Extract** (Liquid AI). Vendor claim: beats Gemma 3 27B and matches GPT-4o on extraction to JSON/XML/YAML in 9 languages. No independent numbers found — [Liquid AI press](https://www.liquid.ai/ja/press/liquid-unveils-nanos-extremely-small-foundation-models-that-match-frontier-model-quality--running-directly-on-everyday-devices)
- **ReaderLM-v2** (Jina, 1.5B, Qwen2.5 base). Claims +15–20% over GPT-4o, mostly on HTML→Markdown. On JSON extraction it is "competitive" but larger models still lead — [arXiv 2503.01151](https://arxiv.org/html/2503.01151v1)

**Running two model sizes in llama.cpp**
- llama-server **router mode** (`--models-dir` / `--models-preset`) loads models on request. `--models-max N` caps how many stay resident, with LRU eviction, and `--no-models-autoload` is also available. These details come from community write-ups, not official docs — [glukhov.org](https://glukhov.org/llm-hosting/llama-cpp/llama-server-router-mode/), [glukhov.org unload](https://glukhov.org/llm-hosting/llama-cpp/unload-llama-cpp-router-models/)
- Errand's measured scaling: 1 slot gives 1.18 pages/s, 8 slots 2.11, 53 slots 2.66. Beyond about 53 slots there is no gain (70 slots: 2.17), so the GPU is compute-saturated — [Errand report](C:\Users\Omer laptop\errand\reports\Maximum parallel brains on laptop GPU.md)

**Speculative decoding**
- llama.cpp MTP self-speculation (`--spec-type draft-mtp`) merged around May 2026. It needs a GGUF that includes the MTP head, and it **currently requires `--parallel 1`**. Reported speed-ups of about 2× and more are for single-stream 27B/35B models (secondary sources) — [mer.vin](https://mer.vin/2026/05/run-qwen-3-6-mtp-in-llama-cpp-faster-local-inference-with-built-in-speculative-decoding/?amp=1), [Jetson AI Lab](https://www.jetson-ai-lab.com/tutorials/speculative-decoding)

### Inferences
- **Per-slot memory at 4,096 tokens with q8_0 cache (calculated).** I scaled Errand's measured 2B components (19.27 MiB running state, 6.375 KiB/token cache, 2 KiB/token scratch) by each model's published head and layer counts.
  - Qwen3.5-2B: **52.8 MiB per slot**, measured.
  - Qwen3.5-4B: state × (24·32)/(18·16) = 2.67, giving about 51 MiB. Cache × (8·4)/(6·2) = 2.67, giving about 17 KiB/token. Scratch about 4 KiB/token. Total **≈ 135 MiB per slot (≈ 2.6 slots of 2B)**. Weights are +1.5 GB over the 2B, worth about 29 slots of 2B.
  - Qwen3-4B-2507 (pure attention): 36 × 8 × 128 × 2 × 1.0625 B ≈ 76.5 KiB/token, giving **≈ 320 MiB per slot (≈ 6 slots of 2B)**. That leaves room for only about 8 slots at 4k, or about 17 at 2k. Its better non-thinking IFEval (83.4) is real, but it costs most of the fleet.
- **4B-only fleet (calculated):** fixed cost ≈ 1,655 − ~1,150 (2B weights) + 2,613 (4B weights) ≈ 3,100 MiB. That gives (5,800 − 3,100) / 135 ≈ **19–20 slots at 4k**, or ≈ 28 at 2k (93 MiB/slot). Throughput per token is roughly half the 2B's, because the 4B does about twice the compute per token and the GPU is already compute-bound (inference). Pages/s would fall to roughly a third or half of today's 2.66. That needs measuring.
- **Mixed fleet, two llama-server processes (calculated):** the 2B server takes 1,655 + N₂ × 52.8. The 4B server takes about 2,900–3,100 fixed (weights, its own CUDA context and buffers) + N₄ × 135.
  - **45 × 2B + 1 × 4B ≈ 4,031 + 3,135 ≈ 7,170 MiB: does NOT fit.**
  - About 16 × 2B + 2 × 4B fits (≈ 2,500 + 3,270 ≈ 5,770 MiB), as does about 11 × 2B + 4 × 4B.
- **Alternatives that keep all 53 2B slots:**
  - (a) Router or manual swapping: run the 2B fleet, then swap in the 4B for batches of checking and fixing. Loading 2.7 GB from NVMe should take a few seconds (inference, unmeasured).
  - (b) Run the 4B "senior" on the CPU with `-ngl 0` in the 16 GB of RAM, so it costs no VRAM. Decode is bounded by DDR4 bandwidth (about 45 GB/s ÷ 2.74 GB ≈ 16 tok/s theoretical, single stream). Prompt processing of a 4k-token page on 6 cores will likely take tens of seconds. Usable only for rare escalations (inference, unmeasured).
- **Qwen3.5-9B** (about 6 GB at 4-bit) cannot share the GPU with anything. Do not use it on the GPU.
- **Gemma 4 E2B** is dominated for this job. Its Q4_K_M file is larger than Qwen3.5-4B's (3.11 vs 2.74 GB), yet it scores lower on MMLU-Pro (60.0 vs 79.1) and Tau2 (24.5 vs 79.9). Mode differences make these comparisons rough, and its per-slot cost is unknown.
- **The 0.8B** is too weak to be a worker (IFEval 52.1, AA index 9). Its only plausible role is as a draft model for a single-stream 4B senior, since it uses the same 248,320-token vocabulary.
- **Specialised models:** NuExtract-2.0-2B (MIT) is the one open, permissive, small, schema-template extractor to A/B against Qwen3.5-2B on Errand's 105 cached pages. Its Qwen2-VL base is pure attention, so per-slot cost will be higher; measure it. Schematron-3B is purpose-built for HTML→JSON, but its base model and licence must be checked before use.
- **Speculative decoding: no throughput gain at 53 slots.** The GPU is compute-saturated, and llama.cpp MTP needs `--parallel 1`. It only helps the latency of a single-stream senior brain.

### Gaps
- No published **non-thinking** scores for Qwen3.5-4B (the card gives one score per benchmark, apparently thinking mode). Its non-thinking extraction quality is unknown and must be measured.
- No independent IFEval or JSON-extraction numbers for Phi-4-mini, Granite 4.0 (Micro/H-Micro/Nano), Llama 3.2 3B or LFM2 were retrieved this session. Their licences were not verified here.
- Schematron-3B base model and licence were not stated on the page fetched. LFM2-Extract and ReaderLM-v2 licences were not verified.
- Per-slot memory for Gemma 4, SmolLM3 and NuExtract under llama.cpp was not measured. The 4B per-slot figure is calculated, not measured.
- Router-mode flags come from third-party blogs. Check `llama-server --help` on b11718.

---

## 2. Fine-tuning on a 6 GB GPU (LoRA/QLoRA with Unsloth on Windows)

### Takeaway
A **bf16 LoRA of Qwen3.5-2B (about 5 GB) just fits** in the 6 GB card, provided the brain fleet is stopped first. **Qwen3.5-4B does not fit** (about 10 GB), and Unsloth says not to use QLoRA on Qwen3.5. Native Windows works through conda. Narrow task fine-tunes have repeatedly matched or beaten GPT-4-class models (vendor and academic results). The trained adapter can be merged and exported to Q4_K_M GGUF at **zero slot cost**.

### Cited Findings
- Unsloth bf16 LoRA VRAM for Qwen3.5: **0.8B about 3 GB, 2B about 5 GB, 4B about 10 GB, 9B about 22 GB**. Unsloth also warns against QLoRA: "not recommended … on the Qwen3.5 models, no matter MoE or dense" because of larger-than-normal quantization differences (paraphrased). Transformers v5 is required. Example `max_seq_length = 2048`. Custom Mamba/linear-attention Triton kernels make compilation slow — [Unsloth Qwen3.5 fine-tune](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- To keep the model's reasoning ability, Unsloth advises at least 75% reasoning-style examples in the mix — [Unsloth Qwen3.5 fine-tune](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- Export with `save_pretrained_gguf` to q4_k_m, q8_0 or f16. The most common cause of a GGUF that performs worse is a mismatched chat template or EOS token — [Unsloth Qwen3.5 fine-tune](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- Windows: Unsloth Core installs natively through conda (Python 3.12) in PowerShell, and Unsloth Studio through `irm https://unsloth.ai/install.ps1 | iex`. **vLLM does not run on native Windows**, so GRPO/RL training needs WSL or Linux. The sample uses `dataset_num_proc = 1`. The sample machine shown is an RTX 3060 12 GB — [Unsloth Windows install](https://unsloth.ai/docs/get-started/install/windows-installation)
- General Unsloth QLoRA minimums (non-Qwen3.5): about 3.5 GB for 3B, 5 GB for 7B, 6 GB for 8B (secondary source). Timing found: "QLoRA fine-tunes a 7B on an RTX 3060 12GB in 2–4 hours" (unspecified dataset) — [search summary: computingforgeeks / pinggy](https://computingforgeeks.com/fine-tune-llm-unsloth-qlora/)
- **LoRA Land (older, May 2024).** 310 4-bit LoRA adapters on 10 base models across 31 tasks. On average they beat GPT-4 by **+10 points** and the base models by **+34 points**. 7B bases generally beat 2B bases — [arXiv 2405.00732](https://arxiv.org/html/2405.00732v1)
- NuExtract: "even the tiny model surpasses GPT-4o after fine-tuning" on a chemistry extraction task (older, 2024; secondary summary) — [NuMind](https://numind.ai/blog/nuextract-a-foundation-model-for-structured-extraction)
- ETLCH: a 1B LLaMA fine-tuned on a few hundred to 1,000 samples per task beats strong baselines on most metrics — [arXiv 2509.08381](https://arxiv.org/pdf/2509.08381v1)
- Extract-0: a 7B fine-tuned extractor scores higher than GPT-4.1 (0.457) and o3 (0.464) on a held-out set of 1,000 document-extraction tasks. The benchmark is the author's own — [arXiv 2509.22906](https://www.arxiv.org/pdf/2509.22906)
- s1 (2025): **1,000 carefully selected** examples were enough for large gains. Random, longest-trace or diversity-only selection was about −30% on AIME24. That was for a 32B model trained on 16 H100s — [arXiv 2501.19393](https://arxiv.org/pdf/2501.19393)

### Inferences
- **Time per 1,000 examples (calculated, not measured).** LoRA with gradient checkpointing costs about 6 × params FLOPs per token. Assume 2B params, 1,000 examples × about 1,500 tokens (page snippet + JSON) = 1.5M tokens, giving about 1.8 × 10¹⁶ FLOPs. The RTX 3060 Laptop does about 20–25 TFLOPS bf16 tensor peak; at 20–35% utilisation that is **about 35–60 minutes per epoch**. 2–3 epochs means about 1–3 hours. The 0.8B would take about 40% of that. Laptop thermal throttling at 75 W could lengthen it. Measure one epoch first.
- **Operational cost:** training needs about 5 GB of the 5.8 GB usable, so **all 53 brains must be offline while training** (overnight jobs). A merged LoRA exported to Q4_K_M has the same size as today's GGUF, so it costs **0 slots** at inference.
- **Fine-tuning the 4B on this card is not viable at bf16.** The only route is QLoRA, which Unsloth discourages for Qwen3.5. The safest plan is to fine-tune the 2B (or the 0.8B for experiments). Rent nothing; keep $0.
- Training only on direct (non-thinking) answers will likely weaken the 2B's thinking mode. Errand runs with thinking off, so that is acceptable, but the checker should not rely on thinking afterwards.
- Expected gain: the evidence base (LoRA Land, NuExtract, ETLCH, Extract-0) consistently shows **narrow extraction fine-tunes closing most of the gap to frontier models**. None is on Errand's exact task or on Qwen3.5-2B, so the size of the gain must be measured on a held-out set of sites the model never trained on.

### Gaps
- No measured Unsloth timing on a 6 GB RTX 3060 Laptop or on Windows for Qwen3.5 was found.
- No published fine-tune of **Qwen3.5-2B** specifically for web extraction was found.
- Whether the Qwen3.5 linear-attention Triton kernels compile cleanly on native Windows was not confirmed. The docs mention only Mamba Triton kernels and slow compilation.

---

## 3. Where $0 training data can come from, and what the Gemini and Qwen terms allow

### Takeaway
The safest $0 label source is **Errand's own verified outputs**: rows where the CSS recipe replay, the brain's extraction, the checker and the vote all agree. Self-training methods built on verified outputs (STaR, ReST-EM) have shown gains of about 5–6 points, with a known risk of overfitting after the first iteration. **Gemini's current terms say you "may not use the Services to develop models that compete with the Services"**, which is ambiguous for a 2B extraction LoRA. Grounded (Search/Maps) results are explicitly off-limits for training. Qwen3.5 is Apache 2.0, so derivatives and fine-tunes are unrestricted.

### Cited Findings
**Gemini API Additional Terms of Service (last updated 2026-04-28; effective March 23, 2026)**
- Use Restrictions: you "may not use the Services to develop models that compete with the Services". The example given in parentheses is the Gemini API or Google AI Studio. The same section forbids reverse engineering, extracting or replicating components, including underlying data or model weights (paraphrased) — [Gemini API Terms](https://ai.google.dev/gemini-api/terms)
- **Grounding with Google Search:** you may not cache, syndicate, analyze, **train on**, or otherwise learn from Grounded Results or Search Suggestions. **Grounding with Google Maps:** no training on Maps data (paraphrased) — [Gemini API Terms](https://ai.google.dev/gemini-api/terms)
- **Unpaid (free) Services:** Google uses submitted content and responses to provide and improve products. Human reviewers may read, annotate and process input and output, and you should not submit sensitive, confidential or personal information (paraphrased) — [Gemini API Terms](https://ai.google.dev/gemini-api/terms)
- Google will not claim ownership of generated content, but may generate similar content for others (paraphrased) — [Gemini API Terms](https://ai.google.dev/gemini-api/terms)
- The terms say the Services are for professional or business developer use, "not for consumer use". Users in the EEA, Switzerland or the UK must use Paid Services (paraphrased) — [Gemini API Terms](https://ai.google.dev/gemini-api/terms)
- **Older (no longer applies):** the Generative AI Additional Terms (Aug 9, 2023) banned using the Services to develop ML models or related technology. Those terms state they **no longer apply as of May 22, 2024** — [policies.google.com/terms/generative-ai](https://policies.google.com/terms/generative-ai)
- **Generative AI Prohibited Use Policy** (last modified Dec 17, 2024): no clause about training models on outputs. It covers abuse and circumvention of safety filters — [Prohibited Use Policy](https://policies.google.com/terms/generative-ai/use-policy)
- **Google APIs Terms** (Nov 9, 2021), which the Gemini terms incorporate. Do not create an API client that "functions substantially the same as the APIs". For content returned by APIs, do not scrape, build databases or make permanent copies, or create derivative works, unless the content owner or the law allows it (paraphrased) — [Google APIs Terms](https://developers.google.com/terms)

**Qwen licences**
- Qwen3.5-2B and Qwen3.5-4B are **Apache-2.0** — [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B), [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B). Apache 2.0 grants a perpetual, worldwide, royalty-free licence to reproduce, prepare derivative works of and distribute the work. It has no clause restricting outputs or competing models — [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- Exception: **Qwen2.5-3B-Instruct is under "qwen-research"**, a non-commercial research licence. Avoid it as a base. The same applies to NuExtract-2.0-4B, which is built on Qwen2.5-VL-3B — [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct), [NuExtract-2.0-2B card](https://huggingface.co/numind/NuExtract-2.0-2B)

**Self-training evidence**
- **STaR (older, 2022):** generate rationales, keep only those that give correct answers (retrying with the answer as a hint when wrong), fine-tune, repeat. GPT-J 6B reached **72.5% on CommonsenseQA vs 73.0% for a 30× larger fine-tuned model**. That is +12.5 over direct-answer fine-tuning and +35.9 over few-shot — [STaR, NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/639a9a172c044fbb64175b5fad42e9a5-Abstract.html)
- **ReST-EM (older, Dec 2023):** sample, keep only answers a binary checker accepts, fine-tune, iterate. MATH: **+5.94% for PaLM 2-S**, +6.34% for PaLM 2-L. APPS: +5.6% / +6.4%. Most of the gain came in the first iteration. **More iterations regressed on APPS and HumanEval**. Training accuracy keeps rising while test accuracy does not (overfitting). Gains grow with model size — [arXiv 2312.06585](https://arxiv.org/abs/2312.06585)
- s1 distilled its 1,000 traces from Gemini Thinking Experimental (2025). That shows Gemini distillation is a known pattern, but it is a research use, not a licence ruling — [arXiv 2501.19393](https://arxiv.org/pdf/2501.19393)

### Inferences
- **Label sources for Errand, ranked by legal and quality safety (all $0):**
  1. **Recipe-replay agreement.** A CSS recipe re-run on the same template gives the same values the brain extracted, and the values pass schema and type checks. The labels come from the page itself, which is deterministic. This is the closest thing to ReST-EM's "binary correctness check".
  2. **Checker-approved plus vote-agreeing outputs.** These are cheap but correlated. Every brain is the same 2B, so shared blind spots get reinforced. Use them only when independently confirmed by item 1.
  3. **Recipe-fix traces.** A broken recipe, then the brain's fix, then the replay succeeds. These are verified examples for the "fix recipe" skill (a STaR-style "rationalization" analogue).
  4. **Gemini outputs: legally ambiguous, so use with care.** The clause bans developing "models that compete with the Services". A field-extraction LoRA on a 2B model is arguably not a competing general model, but the term is undefined, and building with a single account carries account-ban risk. The lowest-risk pattern is to use Gemini only to *judge or spot-check* local candidates and to measure accuracy, not as the source of training text. Never train on Gemini **grounded** (Search/Maps) results; that is explicitly forbidden. Do not send personal data, because the free tier allows human review. This is not legal advice.
- **Apply ReST-EM's lesson:** run 1–2 iterations at most, always evaluate on held-out *sites* (not just held-out pages from the same sites), and stop when held-out accuracy plateaus.
- s1's data-selection result suggests that **about 1,000 diverse, hard, verified examples** (failures that were later fixed, many different site templates) beat a large pile of easy agreeing rows.

### Gaps
- No Google FAQ or official interpretation of "models that compete with the Services" was found for small task-specific models.
- Exact free-tier daily request limits as of October 2026 are unverified. Third-party sources conflict (for example, Flash-Lite at 15–30 RPM and about 100–1,000 RPD) — [tinkerllm](https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/), [agentdeals](https://agentdeals.dev/gemini-api-pricing-changes). Check Google's official rate-limits page.
- The model-collapse literature (training on one's own outputs) was not searched this session. ReST-EM's overfitting result is the only direct evidence here.

---

## 4. Reasoning (thinking) on or off for small models

### Takeaway
For plain field extraction, **keep thinking off**, as Errand already does with `--reasoning-budget 0`. Thinking raises the 2B's instruction-following benchmarks (IFEval 61.2 → 78.6). But on real extraction tasks it has *collapsed* small-model F1, it multiplies tokens per page, and the Qwen3.5-2B card warns specifically about thinking loops. A capped thinking budget is worth testing only for the rare checker or recipe-fixer calls on disputed cases.

### Cited Findings
- Qwen3.5-2B non-thinking → thinking: IFEval 61.2 → 78.6, MMLU-Pro 55.3 → 66.5. The card warns that the 2B "is more prone to entering thinking loops" than other Qwen3.5 sizes and may fail to stop generating; it suggests streaming plus interruption — [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)
- Thinking token cost: the 2B used about 390M output tokens on the AA index, the most in its family — [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- **ContractEval (Aug 2025), clause extraction:** Qwen3-4B F1 was **0.411 non-thinking vs 0.075 thinking**. Qwen3-8B went 0.530 → 0.540, and Qwen3-14B 0.473 → 0.387. The authors conclude that thinking "reduces correctness, likely due to over-complicating simpler tasks" — [arXiv 2508.03080](https://arxiv.org/html/2508.03080)
- A document-understanding study found thinking helped chart analysis but gave smaller gains on information extraction, sometimes causing hallucinations — [arXiv 2608.26141](https://arxiv.org/pdf/2608.26141)
- OptimalThinkingBench: thinking models spend hundreds of tokens on simple queries with no accuracy gain — [arXiv 2508.13141](https://www.arxiv.org/abs/2508.13141)
- With Qwen3 at 0.6B, 1.7B and 4B, thinking beat non-thinking by about 10 points on RewardBench, a *judging* task, not extraction — [arXiv 2509.13332](https://arxiv.org/html/2509.13332v1)
- **Budget forcing (s1, 2025):** cap thinking, or extend it by suppressing the end-of-think token and appending "Wait". AIME24 went 50% → 57% for a 32B model — [arXiv 2501.19393](https://arxiv.org/pdf/2501.19393)
- llama.cpp `--reasoning-budget N`: 0 ends thinking immediately and −1 means unlimited. It applies to the whole server, not per request. Builds after about April 10, 2026 default to INT_MAX when thinking tags are detected. There are reported Qwen3.5 bugs with the budget being ignored or cutting off early (GitHub issues #22717, #25067) — [forge issue](https://github.com/antoinezambelli/forge/issues/54), [llama.cpp #22717](https://github.com/ggml-org/llama.cpp/issues/22717), [SSD Nodes](https://www.ssdnodes.com/learn/lang/pcm/reasoning-effort-settings-local-llm)
- Errand's own report found that `--reasoning-budget 0` silently disables GPU-side sampling. It recommends `-rea off` plus `-bs` instead, for about +10–15% expected (experimental) — [Errand report](C:\Users\Omer laptop\errand\reports\Maximum parallel brains on laptop GPU.md)
- Qwen3.5-4B **thinks by default**, while the 2B does not — [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B), [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)

### Inferences
- **Workers:** keep thinking off. Thinking would cut pages/s several-fold, because output grows from tens of tokens of JSON to hundreds or thousands. The ContractEval 4B result shows extraction can get *worse*.
- **Checker or recipe-fixer on disagreements only:** try a separate server, or the senior 4B, with a hard budget (for example 256–512 tokens) and stream-kill on loops. The RewardBench result hints that judging benefits from thinking even at small sizes. Measure on Errand's disputed cases before adopting.
- If the fleet moves to Qwen3.5-4B, thinking must be switched off explicitly (`-rea off` or the chat template's `enable_thinking: false`), or every page will pay for thinking tokens.

### Gaps
- No head-to-head study of Qwen3.5 (as opposed to Qwen3) thinking vs non-thinking on web or JSON extraction was found.
- How well `--reasoning-budget` behaves at a small non-zero cap on build b11718 with Qwen3.5 is unknown, given the open bug reports.

---

## 5. Quantisation effects: weights and KV cache

### Takeaway
At 4-bit, **smaller models lose more**. Per-channel 4-bit cost Qwen3 1.7B 6–7 MMLU points and Qwen3 4B about 4, while 8-bit is lossless. GGUF K-quants with imatrix lose less than that. Quantisation hurts **thinking-mode** extraction far more than non-thinking. For the 2B, moving Q4_K_M → Q6_K costs about 6 slots and Q8_0 about 14 slots (calculated). The KV cache is already q8_0, which is close to lossless. Going to q4_0 would add at most about 12 slots and carries real quality risk.

### Cited Findings
- **Empirical study of Qwen3 quantization (May 2025), per-channel, MMLU 5-shot:**
  - Qwen3-1.7B: FP16 60.0, 8-bit about 60.0, **4-bit AWQ 53.9 / GPTQ 52.8 / RTN 47.9**, 3-bit AWQ 35.6.
  - Qwen3-4B: FP16 69.7, 8-bit 69.8, **4-bit AWQ 66.0 / GPTQ 65.8 / RTN 63.0**, 3-bit AWQ 43.9.
  - Qwen3-0.6B: 47.1 → 4-bit AWQ 43.1.
  - The authors find Qwen3 more sensitive than LLaMA3 at 3 bits or fewer, with smaller models degrading more — [arXiv 2505.02214](https://arxiv.org/html/2505.02214)
- **ContractEval:** Qwen3-8B non-thinking F1 was 0.530 (bf16), 0.491 (FP8) and 0.475 (AWQ). In thinking mode it fell **0.540 → 0.307 (FP8) → 0.187 (AWQ)**. The authors say quantization's "harms to performance are more evident in reasoning models" — [arXiv 2508.03080](https://arxiv.org/html/2508.03080)
- **Unsloth Qwen3.5 GGUF KLD** (35B-A3B; no small-model table): mean KLD for Q4_K_M 0.0192, UD-Q4_K_XL 0.0137, Q5_K_XL 0.0069, Q6_K_XL 0.0041, Q8_K_XL 0.0026. In hybrid models, the `attn_*` and `ssm_out` tensors are "especially sensitive" to quantization. Imatrix lowers KLD at a cost of about 5–10% slower inference. Lower PPL or KLD did not always mean better benchmark scores — [Unsloth Qwen3.5 GGUF benchmarks](https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks)
- A third-party blog reports Qwen3-4B Q4_K_M losing 6.4% on HumanEval vs Q8 (unverified) — [kunalganglani](https://www.kunalganglani.com/blog/llm-quantization-levels-q4-q8-fp16.md)
- **KV cache:** q8_0 is close to lossless. One user measured +0.0043 PPL on Qwen2.5-Coder-7B, and an output-similarity test called q8_0 "nearly lossless". q4_0 degraded much more, with value-cache quantization more harmful than key-cache. Users report Qwen breaking at long context with q4 KV. All of this is small, non-peer-reviewed evidence — [InventiveHQ](https://inventivehq.com/blog/kv-cache-quantization-quality-benchmark), [DEV](https://dev.to/breachprotocol/quantizing-v4-flashs-kv-cache-in-llamacpp-changes-which-tokens-it-picks-38np), [reddit snapshot](https://reddit.sentinel-team.org/posts/1suur3s/snapshots/2026-05-02T03%3A06%3A21.60641Z)
- Errand measured that the 2B's running state (19.27 MiB per slot) is **not** shrunk by `-ctk/-ctv`. Only the 6 attention layers' cache (6.375 KiB/token at q8_0) is — [Errand report](C:\Users\Omer laptop\errand\reports\Maximum parallel brains on laptop GPU.md)

### Inferences
- **Slot cost of higher-precision weights for the 2B (calculated by applying the 4B's file-size ratios to the 1.2 GB Q4_K_M):**
  - UD-Q4_K_XL: about 1.27 GB, +70 MiB, about **1 slot**.
  - Q5_K_M: about 1.37 GB, +175 MiB, about **3 slots**.
  - Q6_K: about 1.55 GB, +330 MiB, about **6 slots**.
  - Q8_0: about 1.96 GB, +730 MiB, about **14 slots**.
  - Decode becomes slightly slower because more bytes are read per token.
- Today there are about 26 slots of spare headroom at 53 slots, so **Q6_K or even Q8_0 fits without dropping below 53 brains**. This is the cheapest intelligence upgrade available: a single config change, Apache 2.0, no training. Expected gain is a few points, based on the 4-bit vs 8-bit gap in the Qwen3 study; GGUF K-quants likely lose less. Measure it on Errand's extraction set.
- KV q8_0 → q4_0 saves about 3 KiB/token ≈ 12 MiB per 4k slot, which at most adds about 12 more brains. It is not worth it: throughput is already saturated at about 53 slots, so extra slots add nothing.
- Keep any thinking-mode checker at Q6 or higher, given how badly quantization hurt thinking-mode extraction in ContractEval.

### Gaps
- No published KLD or accuracy table for **Qwen3.5-2B or 4B** GGUF quants was found. Run `llama-perplexity --kl-divergence` locally against a BF16 reference to settle it.
- The exact Qwen3.5-2B Q5/Q6/Q8 file sizes were not retrieved; the figures above are scaled from the 4B.

---

## 6. Proven out-of-the-box methods: retrieval of solved examples, routing by difficulty, model merging

### Takeaway
**Retrieving 1–5 solved examples from the same site or template** is well supported for LLM information extraction, and more than 5 shows no further gain. In Errand it is cheap, because solved examples are already in the recipe library, but each example eats tokens in a 4k slot. **Difficulty routing or cascades** cut big-model use by more than 2× with no quality loss in RouteLLM. **Model merging** has weak evidence for LLMs: only plain Task Arithmetic reliably helps.

### Cited Findings
- kNN retrieval of the nearest training examples as demonstrations "yield[s] more consistent and robust performance". It is common practice for relation extraction (GPT-RE, GPT-FinRE). Sentence-level embeddings can retrieve ambiguous neighbours, which motivates task-aware retrieval — [GPT-FinRE arXiv 2306.17519](https://arxiv.org/pdf/2306.17519), [GPT-RE arXiv 2305.02105](https://arxiv.org/pdf/2305.02105)
- Skill extraction: kNN demonstrations work well, but **more than 5 demonstrations doesn't improve extraction** — [arXiv 2402.03832](https://arxiv.org/pdf/2402.03832)
- C-ICL: adding hard negative examples (wrong extractions) to the demonstrations beats plain few-shot on NER and relation extraction — [arXiv 2402.11254](https://arxiv.org/pdf/2402.11254)
- BM25 retrieval beats random demonstrations, and a task-trained retriever beats off-the-shelf ones (Dr.ICL) — [Dr.ICL](https://astro.paperswithcode.com/paper/dr-icl-demonstration-retrieved-in-context)
- NuExtract 2.0 accepts optional input/output example pairs alongside the template — [NuExtract-2.0-2B](https://huggingface.co/numind/NuExtract-2.0-2B)
- **RouteLLM (ICLR 2025; first released 2024):** routers trained on preference data cut costs by **more than 2× without sacrificing quality**. The LMSYS blog reports 95% of GPT-4 quality with 85% (MT-Bench), 45% (MMLU) and 35% (GSM8K) less GPT-4 use. Routers kept working when the strong and weak models were swapped — [arXiv 2406.18665](https://arxiv.org/html/2406.18665v2), [LMSYS blog](https://lmsys.org/blog/2024-07-01-routellm/)
- **Merging:** a study of 6 merging methods on 3B–8B Qwen3/Llama3 models found **Task Arithmetic is the only method that reliably gains**; others "typically result in significant performance drops" — [arXiv 2511.21437](https://www.arxiv.org/pdf/2511.21437). Example: TIES averaged about 49.6 vs Task Arithmetic about 66.3 at 14B (2024) — [arXiv 2408.03092](https://arxiv.org/pdf/2408.03092)

### Inferences
- **Retrieval for Errand:** for each page, pull 1–2 solved (page snippet → JSON) pairs from the *same domain or template*, plus optionally 1 known-wrong extraction as a hard negative in C-ICL style. Keep snippets short, because each demonstration steals from the 4,096-token slot. A 2-example prompt of about 600 tokens costs about 15% of the slot. It costs 0 VRAM if the slot size is unchanged; raising the slot to 6k tokens would cost about 16.8 MiB more per brain. Expect gains mainly on repeat sites. This is the in-context version of the recipe library and needs no training.
- **Routing:** route by observed difficulty rather than a trained router. Signals include vote disagreement, schema-validation failure, recipe-replay mismatch and page length. Easy pages go to the 2B fleet; hard ones go to the swapped-in or CPU 4B, then to Gemini as a judge. This matches RouteLLM's finding that most traffic can stay on the weak model. (The `collaboration_and_escalation.md` notes cover escalation design in more depth.)
- **Merging:** low priority. If separate LoRAs are trained for extraction and recipe-fixing, try simple Task Arithmetic first, or merge just one LoRA into the base. Keeping one merged GGUF keeps the cost at 0 extra slots.

### Gaps
- No clean effect size (points gained) for kNN vs random demonstrations on a standard IE benchmark was retrieved. The papers above report the direction of the effect, not comparable numbers.
- Whether llama-server b11718 supports per-request LoRA adapter switching (which would allow several skill adapters on one base) was not checked this session.

---

## Objective: which options give the most intelligence per slot (comparison)

### Takeaway
In order of gain per cost: (1) **2B Q4_K_M → Q6_K or Q8_0** (about 6–14 slots, which fit in today's headroom; Apache; a few points). (2) **Same-site retrieved examples** (0 slots, costs prompt tokens). (3) A **bf16 LoRA fine-tune of the 2B on recipe-verified labels** (0 slots at inference; GPU offline for about 1–3 hours per 1,000 examples; gains from comparable tasks are large). (4) A **Qwen3.5-4B senior via swapping or CPU** (0 GPU slots), or a mixed GPU fleet of about 16 × 2B + 2 × 4B (costs about 37 slots). (5) **Thinking only for checkers, with a hard cap.** Speculative decoding, KV q4_0 and merging are not worth doing now.

### Cited Findings
- All figures are as cited in sections 1–6 above. The slot unit is 52.8 MiB per 4k-token 2B brain, measured; 5,800 MiB is usable — [Errand report](C:\Users\Omer laptop\errand\reports\Maximum parallel brains on laptop GPU.md)

### Inferences

| Option | Evidence of gain | VRAM / slot cost (1 slot ≈ 53 MiB) | Speed cost | Licence | Main risks |
|---|---|---|---|---|---|
| 2B Q4_K_M → Q6_K / Q8_0 | Qwen3 1.7B: 4-bit −6 to −7 MMLU vs 8-bit lossless (per-channel); GGUF K-quants likely less | +6 / +14 slots (calculated); fits in the about 26-slot headroom | Small decode slowdown | Apache 2.0 | Gain may be small; measure KLD locally |
| Retrieved same-site examples (1–2, max 5) | IE papers: kNN demonstrations beat random; no gain beyond 5 | 0 VRAM; about 15% of a 4k slot per 2 examples | Longer prompts, more prefill | n/a | Wrong examples spread errors |
| LoRA fine-tune of the 2B (Unsloth, bf16) | LoRA Land +10 vs GPT-4 avg (2024); NuExtract, Extract-0 narrow wins | 0 slots at inference; needs about 5 GB, so fleet offline | About 35–60 min per epoch per 1k examples (calculated) | Apache 2.0 base | Overfitting to seen sites; template/EOS mismatch on export |
| Self-training on verified outputs (ReST-EM/STaR) | +5.6 to 6.3 points (MATH/APPS, PaLM 2; 2023) | As LoRA | Same | Own data; no ToS issue | Regression after more than 1–2 rounds; shared blind spots |
| Gemini labels | (not measured here) | 0 | Free-tier rate limits | **Ambiguous**: "develop models that compete" clause; grounded results banned | Account ban; free-tier human review of data |
| Qwen3.5-4B fleet replacing the 2B | AA index 16→27; IFEval (thinking) 78.6→89.8; TAU2 48.8→79.9 | About 19 slots at 4k / 28 at 2k total (calculated) | Likely 1/3 to 1/2 the pages/s (inference) | Apache 2.0 | Thinks by default; no non-thinking scores published |
| Mixed 2B + 4B on GPU | As above, for the senior only | 45+1 does **not** fit (about 7.2 GB); about 16+2 fits (−37 slots) | Two processes compete for compute | Apache 2.0 | Tight VRAM; spills to RAM |
| 4B senior via router swap or CPU | As above | 0 GPU slots | Swap: seconds per switch; CPU: slow prefill | Apache 2.0 | Latency; CPU speed unmeasured |
| Qwen3-4B-2507 | Non-thinking IFEval 83.4 (vs 2B 61.2) | About 320 MiB/slot, so about 8 slots total (calculated) | Large | Apache 2.0 | Kills the fleet |
| NuExtract-2.0-2B | Vendor benchmarks only | Unknown; pure-attention base, likely more than 53 MiB | Similar to 2B | MIT | Template format; not a recipe writer |
| Gemma 4 E2B | MMLU-Pro 60, Tau2 24.5 | 3.11 GB weights, more than the Qwen3.5-4B | n/a | Apache 2.0 | Dominated by Qwen3.5-4B |
| Thinking on, capped, checkers only | IFEval +17 on the 2B; but extraction F1 0.41→0.08 on Qwen3-4B | 0 VRAM | Many more tokens per call | n/a | Loops; budget-flag bugs |
| Speculative decoding (MTP / draft) | About 2× single-stream only | Draft model or MTP GGUF | **None at 53 slots**; MTP needs `--parallel 1` | n/a | No gain at batch |
| KV cache q8_0 → q4_0 | — | Up to +12 slots | None | n/a | Quality loss; extra slots add no throughput |
| Model merging | Only Task Arithmetic reliable (3–8B) | 0 | 0 | n/a | Drops with TIES and similar methods |

### Gaps
- All gains are from benchmarks other than Errand's task. Errand's own 105 cached pages (Set A), plus a held-out set of unseen sites, are needed to rank these options on what actually matters.
