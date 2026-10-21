# llama.cpp / llama-server knobs for many parallel slots of a small model on a 6 GB laptop GPU (state as of 2026-10-21, build b11718)

Scope: Errand's brain server. Command: `-np 53 -c 217088 -ngl 99 -fa on -ctk q8_0 -ctv q8_0 -ctxcp 2 -cram 2048 --reasoning-budget 0`. Model: Qwen3.5-2B Q4_K_M (hybrid: 18 Gated DeltaNet layers + 6 attention layers, 248,320 vocab). Hardware: RTX 3060 Laptop 6 GB (75 W, PCIe 3), i5-10500H, Windows 11, llama.cpp b11718 (commit 547208dca) CUDA 12.4.

Evidence labels: **[CODE]** = b11718 source. **[BINARY]** = strings or `--help` from the local b11718 Windows build at `C:\Users\Omer laptop\AppData\Local\Temp\errand\llama\`. **[LOG]** = Errand's own server logs in `C:\Users\Omer laptop\errand\bench\` (analysed 2026-10-21). **[PRIOR]** = Errand's earlier note `research_notes\Maximum parallel brains on laptop GPU\scaling.md` (measured on this laptop 2026-10-18). **[PUBLISHED]** = web source. **[INFERRED]** = my reasoning, not measured.

---

## 1. Grammar / JSON-schema constrained sampling cost: CPU-bound per slot? scaling with many slots? what reduces it?

### Takeaway
Grammar sampling runs on the CPU, inside the single server thread, one slot after another. It also turns GPU (backend) sampling off. In Errand's own logs, the JSON-schema run had a median per-slot decode step of 344 ms against 194 ms for plain text. Roughly 0.14 s per page of the 0.25 s slowdown is left over after accounting for the longer prompt [INFERRED]. The cheapest fix is no grammar at all: plain or "pointer" output plus a lenient parser. Otherwise use a small, flat schema. llguidance is much faster, but it is **not compiled into the release Windows build**.

### Cited Findings
- **Sample, then verify, is the default path [CODE].** `common_sampler_sample` runs the sampler chain first. It then checks only the chosen token against the grammar, using a one-element candidate array. The grammar is applied to the full vocabulary, followed by a resample, only when that token is rejected, or when `grammar_first` is set. — [b11718 common/sampling.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/common/sampling.cpp)
- **Full-vocabulary candidate array on the CPU [CODE].** Without backend sampling, `set_logits` loops over all `n_vocab` (248,320 here) and builds a candidate entry for each token, for every slot, at every step. — [b11718 common/sampling.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/common/sampling.cpp)
- **Grammar disables backend sampling [CODE][BINARY].** `common_sampler_init` logs "backend sampling is not compatible with grammar, disabling" and sets `backend_sampling = false`. The same applies when a reasoning budget is present. The string is present in the local `llama-common.dll`. — [b11718 common/sampling.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/common/sampling.cpp)
- **Sampling runs serially on one thread [CODE][PUBLISHED].** In `post_decode`, the server calls `common_sampler_sample(...)` inside `iterate(slots, ...)`, one slot after another, with no threads or OpenMP around it. — [b11718 server-context.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/tools/server/server-context.cpp). The dev docs say server_context "runs on a dedicated single thread" and that heavy post-processing "directly impacts multi-sequence throughput". — [README-dev mirror](https://huggingface.co/OpenTransformer/llama.cpp-prismml/blob/main/tools/server/README-dev.md)
- **Errand's measured effect [LOG]**, `server-np53.log` (plain text) against `server-np53-point.log` (JSON schema), 105 tasks each:
  - Per-slot decode ms per token: median **194 vs 344**, max 267 vs 506.
  - Output tokens: mean 74 vs 77.
  - Prompt tokens: about 640 vs a median of 1,250.
  - Throughput as reported by the user: 2.66 vs 1.6 pages/s. Per-slot generation in the JSON run was 1.98 to 2.16 tok/s on typical tasks (for example tasks 126, 129 and 130).
- **Grammar build cost is a separate, one-off, CPU-bound step [PUBLISHED].** Issue #29457 (opened 2026-09-26, unconfirmed): json_schema-to-GBNF construction runs synchronously before generation. An enum of 1,000 values takes 0.75 s, and 10,000 values take 6.5 s. A contributor's M5 comparison of native GBNF against LLGuidance: 1,000 items 516 ms vs 1.92 ms, 10,000 items 5.18 s vs 17.7 ms. — [Issue #29457](https://github.com/ggml-org/llama.cpp/issues/29457)
- **Grammar-writing rules from the official docs [PUBLISHED].**
  - Chained optional repetitions (`x? x? x?...`) "may result in extremely slow sampling". Use `x{0,N}` instead.
  - json_schema defaults to no additional properties, because allowing them is slow and prone to hallucination. — [grammars/README.md](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)
- **Older evidence (2023) [PUBLISHED].** Grammar sampling time grew with the number of grammar stacks. — [Issue #4218](https://github.com/ggml-org/llama.cpp/issues/4218)
- **llguidance [PUBLISHED].**
  - Enabled with CMake `-DLLAMA_LLGUIDANCE=ON`, which needs a Rust toolchain. Grammars that start with `%llguidance` go to it.
  - The vendor quotes about 50 µs of single-core CPU time per token mask for a 128k vocabulary on JSONSchemaBench, with p99 0.5 ms and p100 20 ms. — [llama.cpp docs/llguidance.md mirror](https://huggingface.co/OpenTransformer/llama.cpp-prismml/blob/main/docs/llguidance.md), [guidance-ai/llguidance](https://github.com/guidance-ai/llguidance) (vendor claims)
  - The code throws "llguidance is not enabled" when it was not compiled in. — [b11718 common/sampling.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/common/sampling.cpp)
- **The local b11718 release build has no llguidance [BINARY].** `llama-common.dll` contains the "llguidance is not enabled" fallback string and no `llg_` matcher symbols.
- **Backend (GPU) sampling cannot take grammars [PUBLISHED].** PR #17004 (merged 2026-01-04) lists "Not compatible with grammar sampling" as a limitation. GPU samplers: temp, logit_bias, top_k, greedy, dist, min_p, top_p, temp_ext. Not implemented: penalties, dry, xtc, typical, top_n_sigma, mirostat. — [PR #17004](https://github.com/ggml-org/llama.cpp/pull/17004)
- **Schema failure modes that affect accuracy [PUBLISHED]** (titles and summaries as indexed, 2026):
  - #19051: the server "fails open" when JSON schema grammar parsing fails, so it generates unconstrained output. — [Issue #19051](https://github.com/ggml-org/llama.cpp/issues/19051)
  - #21228: a schema using `$ref`/`$defs` silently fails when the rule count exceeds MAX_REPETITION_THRESHOLD. — [Issue #21228](https://github.com/ggml-org/llama.cpp/issues/21228)
  - #29462: huge or contradictory `min*` bounds make the builder allocate without limit. — [Issue #29462](https://github.com/ggml-org/llama.cpp/issues/29462)
  - #30419: the grammar stack dies with a json_schema response_format under `--spec-type draft-mtp`. Under sustained load of many small strict-schema requests, responses become HTTP 500. — [Issue #30419](https://github.com/ggml-org/llama.cpp/issues/30419)

### Inferences
- **[COMPUTED/INFERRED] Splitting the JSON-run slowdown.** Per page, 1/1.6 − 1/2.66 = **+0.25 s**.
  - The extra ~610 prompt tokens at about 5,500 tok/s of GPU prefill [PRIOR] cost about 0.11 s.
  - That leaves about **0.14 s per page, or about 1.8 ms per output token**, for grammar work on the single thread, longer attention, and other overheads.
  - This needs an A/B run: same long prompt, `response_format` on vs off. That cleanly separates grammar cost from prompt length.
- **[INFERRED] Why cost grows with slot count.** Grammar and candidate building are per slot, serial, and on one CPU thread. Any per-token CPU cost is multiplied by the number of slots generating in that step, and it is not overlapped with GPU work. On this laptop, the same CPU also drives up to 53 browser agents.
- **[INFERRED] Ways to reduce it, in expected order:**
  1. **No grammar:** ask for plain lines or ids, then parse or repair in code. This also lets `-bs` work.
  2. **Fewer rejections:** the full-vocabulary path runs only when the model's preferred token is invalid. Put a literal example of the exact JSON shape and whitespace in the system prompt, and keep keys short and fixed. Avoid optional fields, `pattern`, `minLength`/`maxLength`, `$ref`, large enums and `additionalProperties: true`.
  3. **Shorter output:** grammar cost scales with output tokens, and "point, don't write" already cuts them.
  4. **llguidance:** needs a custom Windows CUDA build with Rust. Of these options it is the only one that keeps strict JSON and avoids a slow GBNF engine.
- **Accuracy:** because grammars can fail open, the tuner must measure the JSON-valid rate and schema-conformance rate per configuration. It cannot assume 100%.

### Gaps
- No published benchmark found of per-token grammar cost as a function of `n_parallel`. Errand's logs are the only data, and they mix grammar with a doubled prompt length.
- Rejection rates (how often the full-vocabulary path runs) for this schema and model are unmeasured. The server does not log them.
- No prebuilt Windows CUDA binaries with llguidance were found. Whether one can be built on this laptop (Rust plus MSVC/Clang plus CUDA 12.4) was not tested.

---

## 2. Prompt/prefix caching across slots: cache_prompt, --cache-reuse, shared system prompt, --slot-prompt-similarity, -cram

### Takeaway
On this hybrid model, prefix reuse works only by restoring a **context checkpoint** whose position is at or before the shared prefix. `--cache-reuse` does nothing here. With `-ctxcp 2`, the checkpoint at the end of the system prompt is usually evicted by the two end-of-prompt checkpoints. Errand's logs show the 99-token prefix reused on only **2 of 105** tasks in the JSON run and **17 of 105** in the plain run. `-ctxcp` (3 to 4) and `-ub` are therefore real knobs for prefix reuse. Moving all static instructions into the system prompt raises the payoff.

### Cited Findings
- **Defaults in b11718 [BINARY]**, from `--help`:
  - `--cache-prompt` is enabled by default. `--cache-reuse N` defaults to 0 and "requires prompt caching".
  - `-sps, --slot-prompt-similarity` defaults to 0.10.
  - `-ctxcp` defaults to 32 checkpoints per slot. `-cms, --checkpoint-min-step` defaults to 8192 tokens.
  - `-cram` defaults to 8192 MiB.
  - `--cache-idle-slots` is enabled by default and "requires cache-ram".
  - `-kvu` defaults on only when the slot count is auto.
  - Source: local `llama-server.exe --help`, b11718.
- **`--cache-reuse` is turned off here [CODE][BINARY].** If `!llama_memory_can_shift(...)`, the server sets `n_cache_reuse = 0` and logs "cache_reuse is not supported by this context". Per request, the binary logs "cache reuse is not supported - ignoring n_cache_reuse". — [b11718 server-context.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/tools/server/server-context.cpp)
- **Reuse needs a checkpoint [CODE].** The server computes `n_past` as the common prefix with the slot's cached tokens, then searches checkpoints for one with `pos_max <= pos_next`. If none qualifies, it sets `n_past = 0` and logs "forcing full prompt re-processing due to lack of cache data". — [b11718 server-context.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/tools/server/server-context.cpp)
- **Where checkpoints are placed [CODE].**
  - At the start of the last user message, plus `4 + n_ubatch` and `4` tokens before the end of the prompt.
  - When the per-slot count reaches `n_ctx_checkpoints`, the oldest checkpoint is removed.
  - Checkpoints closer together than `checkpoint_min_step` are pruned, except those from the current task.
  - Source: [b11718 server-context.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/tools/server/server-context.cpp); line refs `server-context.cpp:4095-4110` in [PRIOR].
- **Errand logs [LOG].**
  - `server-np53-point.log` has 103 lines like "erasing old context checkpoint (pos_min = 98, pos_max = 98, n_tokens = 99, size = 19.266 MiB)". This is the end-of-system-prompt checkpoint being evicted.
  - Computing reused = release `n_tokens` − (prompt-eval tokens + generated − 1) gives:
    - JSON run: **2 / 105 tasks** reused, 99 tokens each.
    - Plain run (`server-np53.log`): **17 / 105** reused, mean 87 tokens.
    - The maximum possible was about 52 (the second-round tasks).
  - Example of a hit: task 126 evaluated 1,139 prompt tokens and released at 1,303 tokens, so 99 were reused.
- **Slot selection [CODE][LOG].**
  - `get_available_slot()` picks a pinned `id_slot` first.
  - Otherwise it takes the best idle slot by LCP fraction `f_sim = lcp / prompt_len` above `-sps`, then falls back to LRU.
  - If `f_keep < 0.5`, the slot's state is saved to the host prompt cache. — [b11718 server-context.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/tools/server/server-context.cpp)
  - In the JSON run, 53 selections were "by LRU" and 52 "by LCP similarity" with `f_sim_best` around 0.125 and `f_keep` 0.18 to 0.28.
  - The logs also show repeated "making room for prompt cache entry, removing oldest entry (size = 61 to 66 MiB)".
- **Docs [PUBLISHED].** `cache_prompt` logits "are **not** guaranteed to be bit-for-bit identical" across batch sizes, so caching "can cause nondeterministic results". `id_slot` pins a request to a slot. — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **[PRIOR]** `-kvu` does not share recurrent state, so it gains nothing for this model. The shared prefix was about 80 to 99 of about 640 tokens, about 12% of prefill.

### Inferences
- **[INFERRED from CODE + LOG] Why `-ctxcp 2` loses the prefix.**
  - For prompts longer than `4 + n_ubatch` (516 tokens at the default `-ub 512`), each task creates 3 checkpoints: user start, end − 516, and end − 4.
  - With a cap of 2, the user-start checkpoint is dropped. The next task on that slot then shares only the 99-token system prompt and finds no checkpoint at or below it.
  - Only slots whose previous prompt was short kept the checkpoint. That fits the 2 vs 17 hit counts, since JSON prompts were about twice as long.
- **Knobs to sweep:**
  - `-ctxcp` ∈ {2, 3, 4}. Each extra checkpoint is 19.27 MiB per slot, about 1 GiB for 53 slots. Where checkpoints live (host RAM or VRAM) was not verified; check memory after a sweep.
  - `-ub` ≥ prompt length. Then the end − (4 + ub) checkpoint is never created and 2 checkpoints suffice.
  - `-ctxcp 0` gives no reuse but no checkpoint copies either.
- **Payoff of prefix reuse.**
  - Today: about 99 of 1,250 tokens (8%), roughly 18 ms of GPU prefill per page.
  - If the static instructions, schema and examples move into the system prompt so that, say, 800 of 1,250 tokens are shared, reuse would save about 0.15 s of prefill per page [COMPUTED at 5,500 tok/s]. That is comparable to the whole grammar penalty.
  - Prompt layout is a tuner knob: shared text first, page text last.
- **`-sps` matters little here.** Every slot holds the same system prompt, so similarity only changes which slot is picked. Reuse is decided by checkpoint survival. With long page text, `f_sim` (99/1,250 = 0.08) falls below 0.10 and selection goes to LRU. `-sps 0` (disabled) is worth one A/B run.
- **`-cram`.** Single-turn bulk jobs gain little from the host cache, because the slot itself holds the same prefix. Each saved entry is about 62 to 66 MiB copied over PCIe 3, and the cache churns constantly at 2048 MiB. Sweep `-cram` ∈ {0, 2048}. `--no-cache-idle-slots` is a related switch.
- **Accuracy:** prefix reuse and batch composition change logits slightly (docs warning). Temperature-0 accuracy can differ run to run, so the tuner should score every setting over several repeats.

### Gaps
- Not verified on the hardware: whether `-ctxcp 3` actually raises reuse to about 52/52, and what it costs in RAM and copy time.
- The "forcing full prompt re-processing" message was not found in these logs. The b11718 wording may differ, or it may only print at a higher verbosity. The reuse count above was derived from token arithmetic.
- How `-cms 8192` (new default) interacts with 4,096-token slots was not traced in detail.

---

## 3. Batch knobs: -b / -ub, --cont-batching, -np vs total throughput, --threads

### Takeaway
On this GPU, prefill is compute-saturated even at one sequence, and decode saturates at about 32 sequences. The server saturates at about 50 to 64 slots because of serial per-token CPU work. `-ub 1024` (+4% prefill, measured) is the only batch knob with a measured gain. Continuous batching is already on. `-t` barely matters with every layer on the GPU, but CPU priority may matter because browsers share the CPU.

### Cited Findings
- **Defaults in b11718 [BINARY]:** `-b` 2048 (logical), `-ub` 512 (physical), `-cb` continuous batching enabled, `-np` −1 (auto), `-t` −1, `--poll` 50, `--prio` 0 (normal), and `--threads-http` −1.
- **Batch filling [CODE].**
  - Prompt tokens are added `while (... batch.size() < n_batch)`.
  - The batch is allocated as `max(n_batch, n_parallel)`, and "update_slots() logic will always submit a maximum of n_batch or n_parallel tokens".
  - On a KV failure, decode halves `n_batch` and retries.
  - Source: [b11718 server-context.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/tools/server/server-context.cpp)
- **[PRIOR] llama-bench pp2048 on this laptop:** ub 256 = 5,010 to 5,120 tok/s; ub 512 = 5,570 to 5,640; **ub 1024 = 5,800 to 5,860 (+4%)**; ub 2048 = 5,870 to 5,930 (+5%).
- **[PRIOR] llama-batched-bench** (npp 640, ntg 64): S_TG 132 tok/s at B=1, 882 at B=32, 956 at 64, 1,006 at 128. Prefill is flat at about 5,500 tok/s. The GPU knee is about 32 sequences.
- **[PRIOR] Server pages/s by slot count:** 1.18 (1 slot), 2.11 (8), 2.66 (53), 2.84 (128 slots, 2k ctx). Fit: Tm = 2.74 pages/s, k = 1.5. About 0.16 s per page is serial, non-GPU overhead.
- **[PUBLISHED]** The server loop is single-threaded. — [README-dev mirror](https://huggingface.co/OpenTransformer/llama.cpp-prismml/blob/main/tools/server/README-dev.md)

### Inferences
- **Sweep ranges:**
  - `-np` ∈ {24, 32, 40, 53, 64}. 24 to 26 slots give a p50 under 10 s at about 92 to 95% of peak throughput [PRIOR].
  - `-ub` ∈ {512, 1024, 2048}, with `-b` ≥ `-ub`. Check the "compute buffer size" log line against the VRAM budget.
  - `-b` ∈ {1024, 2048, 4096}. This only sets how many prompt tokens one iteration takes, so it trades decode-step latency for prefill progress.
- **Context per slot:** `-c` = np × 2,048 is enough for 1,250-token prompts plus about 110 output tokens. It saves VRAM for more `-ub` or checkpoints, but adds no throughput.
- **CPU contention [INFERRED]:** sampling and grammar run on one CPU thread while up to 53 Chrome agents share a 6-core i5. `--prio 1` or `2`, or a CPU affinity mask (`-C`/`-Cb`), are cheap knobs to test. They are unmeasured.
- **`-t`:** keep at the default or small. With `-ngl 99`, CPU threads mostly idle-poll. `--poll 0` might free CPU for the browsers at some latency cost [INFERRED].

### Gaps
- The b11718 code that orders decode tokens against prompt chunks inside one batch was not visible in the fetched excerpt.
- `--prio`, `--poll` and affinity effects on Windows under browser load are unmeasured.

---

## 4. KV-cache quantization (q8_0 vs f16 vs q4_0) and flash attention: speed and accuracy for a 2B hybrid model

### Takeaway
Keep `-fa on -ctk q8_0 -ctv q8_0`. Only 6 of 24 layers have a KV cache in this model, so KV type barely moves speed or VRAM. Per-token state traffic is dominated by the recurrent state. q8_0 is near-lossless on Qwen models. q4_0 costs measurable accuracy for little gain. f16 is a reasonable accuracy-check setting if VRAM allows.

### Cited Findings
- **[PRIOR] Speed and size on this laptop:**
  - Prefill speed is the same within ±2% for every q8_0/f16 mix.
  - KV read is about 4.6 MB per sequence-token against about 40 MB of recurrent state moved per sequence-token.
  - f16 costs +14.5 MiB per slot at 4k context.
  - A quantized V cache requires `-fa on`.
- **[PUBLISHED] Qwen KL divergence against an f16 cache** (llama.cpp, 2026-04-24, about 250k tokens):
  - Qwen 3.6 27B q8_0: KL 0.024. Qwen 3.6 35B-A3B q8_0: 0.039. Both Qwen models at q4_0: 0.087 to 0.117.
  - Gemma 4 is far more sensitive: 26B-A4B gives 0.377 at q8_0 and 1.088 at q4_0, with 68% top-1 agreement.
  - These results include llama.cpp's automatic attention rotation (PR #21038). The models are mid-size, not 2B. — [localbench](https://localbench.substack.com/p/kv-cache-quantization-benchmark)
- **[PUBLISHED, weak source]** Qwen 3.5 9B: q8_0 KV adds about +0.05% perplexity; a q4 V cache adds about +1.4%. — [techplained](https://www.techplained.com/kv-cache-quantization) (methodology unclear)
- **[BINARY]** b11718 `llama.dll` contains Hadamard rotation code ("attention rotation force disabled", "loaded %zu Hadamard-folded weight(s)"). The rotation feature from PR #21038 is in this build.
- **[PUBLISHED]** `llama-perplexity` supports a KL-divergence comparison against a saved f16 baseline, which can be run locally. — [llama-perplexity docs](https://www.mintlify.com/ggml-org/llama.cpp/api/tools/llama-perplexity)

### Inferences
- **Knob:** `-ctk/-ctv` ∈ {q8_0, f16}. Drop q4_0: it saves only about 7 MiB per slot at 4k on 6 attention layers [INFERRED from PRIOR sizes], and Qwen q4_0 KL is 3 to 4 times that of q8_0.
- **Mixed K/V:** `-ctk f16 -ctv q8_0` is a cheap middle option. Keys are generally the more sensitive half, but this was not measured for Qwen3.5-2B.
- **`-fa`:** leave on. It is required for quantized V. `-fa auto` behaves the same on CUDA [INFERRED].

### Gaps
- No KV-quantization accuracy data exists for sub-3B models or for hybrid Gated DeltaNet models. A local `llama-perplexity --kl-divergence` run on Errand pages would settle it.
- f16 against q8_0 decode speed at 53 slots was not benchmarked, only prefill.

---

## 5. Sampling knobs that change accuracy: temperature 0 vs low temperature + voting, top-k/top-p/min-p, penalties, logprobs for confidence

### Takeaway
For extraction, greedy decoding (temperature 0) is the base case. Qwen's official non-thinking settings (temperature 1.0, top_k 20, presence penalty 2.0) target chat and are not meant for extraction. `/v1/chat/completions` in b11718 returns OpenAI-style `logprobs`/`top_logprobs`, so the harness can get a confidence signal. Penalties and DRY cannot run on the GPU, so `-bs` needs a chain of only temp, top_k, top_p and min_p.

### Cited Findings
- **Qwen3.5-2B card [PUBLISHED].**
  - Non-thinking text: temperature 1.0, top_p 1.0, top_k 20, min_p 0, **presence_penalty 2.0**, repetition_penalty 1.0.
  - Thinking text: temperature 1.0, top_p 0.95, top_k 20, presence_penalty 1.5.
  - Higher presence penalty "may cause language mixing and slightly lower performance".
  - The 2B "runs in non-thinking mode by default". — [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)
- **b11718 sampler defaults [BINARY]:**
  - Chain: `penalties;dry;top_n_sigma;top_k;typ_p;top_p;min_p;xtc;temperature`.
  - temperature 0.80, top_k 40, top_p 0.95, min_p 0.05, repeat_penalty 1.00 (off).
  - `--samplers` / `--sampler-seq` set the order and selection. There is also a per-request `samplers` array. — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **Greedy selection [CODE].** The final selector is greedy only when `n_probs == 0` and the chain ends in zero temperature or top-k 1. Otherwise the distribution sampler is used. — [b11718 common/sampling.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/common/sampling.cpp)
- **Logprobs [BINARY][PUBLISHED].**
  - `llama-server-impl.dll` contains `top_logprobs`, `logprobs` and the error "logprobs is not supported with tools + stream". That implies chat-completions logprobs work except for tools combined with streaming.
  - `/completion` has `n_probs` and `post_sampling_probs`, which return probabilities after the sampling chain. — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **Backend sampling limits [PUBLISHED].** GPU samplers cover temp, top_k, top_p, min_p, greedy, dist and logit_bias. Penalties and DRY are not implemented. The PR contains a commit "sampling : handle n_probs case". — [PR #17004](https://github.com/ggml-org/llama.cpp/pull/17004)
- **Determinism [PUBLISHED].** Results with prompt caching are not bit-identical across batch sizes. — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **Errand's prior research** found no measured self-consistency gains for 1 to 4B models on web extraction. It suggests k=3 voting at temperature 0.2 to 0.7 only on fields that fail checks. — `research_notes\Smarter small model web agents\extraction_accuracy.md` (Errand internal)

### Inferences
- **Knobs:**
  - temperature ∈ {0, 0.2, 0.5}, only for voting runs.
  - top_k ∈ {1, 20, 40}.
  - min_p ∈ {0, 0.05}.
  - presence_penalty ∈ {0, 0.5}. Probably 0 for short extraction; Qwen's 2.0 targets long chat.
  - `logprobs: true, top_logprobs` ∈ {0, 3}.
- **Confidence:** use the minimum or mean token logprob over the answer span as an escalation trigger. With grammar on, logprobs reflect the masked distribution only if `post_sampling_probs` is used [INFERRED, check].
- **`n_probs` cost [INFERRED]:** requesting probabilities stops the greedy fast path and adds per-slot CPU work. Measure tok/s with and without it at 53 slots.
- **Voting:** voting needs temperature > 0 and distinct seeds per sample. It multiplies the work by k, so at about 2.7 pages/s a 3-way vote on everything would cut throughput to about a third. Use it only on fields that fail a grounding check.

### Gaps
- Whether backend sampling returns logprobs, and how they compare with CPU-sampling logprobs, is not documented in what I could read.
- No measured accuracy effect of these sampler settings on Qwen3.5-2B extraction was found.

---

## 6. Reasoning controls for Qwen3.5 in llama.cpp (--reasoning-budget, --reasoning-format, enable_thinking) and known bugs

### Takeaway
Use `-rea off`, not `--reasoning-budget 0`. Any budget ≥ 0 installs the reasoning-budget sampler, and that silently disables backend sampling. `enable_thinking: false` through chat_template_kwargs was unreliable for Qwen3.5 in early and mid 2026, and maintainers pointed people to `--reasoning-budget 0`. Hence the tuner should check outputs for `<think>` and empty content after switching.

### Cited Findings
- **b11718 flags [BINARY]:**
  - `-rea, --reasoning [on|off|auto]`, default auto (detected from the template).
  - `--reasoning-budget N`: −1 unrestricted, 0 immediate end, N > 0 a budget.
  - `--reasoning-budget-message`, `--reasoning-effort`, `--reasoning-format` (none, deepseek, deepseek-legacy; default auto), `--reasoning-preserve`, `--chat-template-kwargs`, `--skip-chat-parsing`.
  - Per request, the server binary has `chat_template_kwargs`, `enable_thinking`, `thinking_budget_tokens` and `reasoning_budget`, plus help text "Number of tokens in the reasoning budget (-1 = disabled)".
- **Backend sampling is disabled by a reasoning budget [CODE].** `common_sampler_init` disables backend sampling when a reasoning budget is present. A lazy grammar applies only when the budget is idle or done. — [b11718 common/sampling.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/common/sampling.cpp). [PRIOR]: `sampling.cpp:315` activates it when `reasoning_budget_tokens >= 0`, and `-rea off` sets `enable_thinking=false` (`arg.cpp:3711`).
- **Known bugs (2026) [PUBLISHED]:**
  - #20182: `enable_thinking` cannot turn off thinking for Qwen3.5. Closed as not planned; the maintainer said to use `--reasoning-budget 0`. — [Issue #20182](https://github.com/ggml-org/llama.cpp/issues/20182)
  - #20409: `enable_thinking=false` via `--chat-template-kwargs` is ignored, on both PowerShell and Bash. Closed as not planned; the workaround is the newer `--reasoning` switch. — [Issue #20409](https://github.com/ggml-org/llama.cpp/issues/20409)
  - #20196: "disabling reasoning does not work anymore on certain models". — [Issue #20196](https://github.com/ggml-org/llama.cpp/issues/20196)
  - Discussion #23351: the `enable_thinking` kwarg is deprecated in favour of `--reasoning on/off`. It proposes a native per-request toggle for Qwen3.5/3.6. — [Discussion #23351](https://github.com/ggml-org/llama.cpp/discussions/23351)
  - A user on unsloth's Qwen3.5 GGUF page says `--reasoning-budget 0` "feels like it just hides the thinking". — [HF discussion](https://huggingface.co/unsloth/Qwen3.5-27B-GGUF/discussions/4) (user report)
- **Qwen card [PUBLISHED].** Qwen3.5-2B defaults to non-thinking. In thinking mode, the 2B is "more prone to entering thinking loops" than other Qwen3.5 models. — [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)

### Inferences
- **Knob:** `reasoning_mode` ∈ {`-rea off`, `--reasoning-budget 0`}, crossed with `-bs` on/off. Acceptance check: zero `<think>` in content, non-empty content, and no "backend sampling is not compatible" warning in the server log.
- **Thinking with a budget:** keep `--reasoning-budget N > 0` only for a rare "checker" pool. It also forces CPU sampling for that pool.

### Gaps
- No issue was found confirming that `-rea off` works with Qwen3.5-2B on b11718 specifically, although the 2B defaults to non-thinking. Verify by A/B on outputs.
- The behaviour of the per-request `thinking_budget_tokens` on b11718 is untested.

---

## 7. Speculative decoding / MTP / draft models with -np > 1 (2026 builds)

### Takeaway
Not usable for Errand's current model, and probably not helpful at 53 slots. This Qwen3.5-2B GGUF has no MTP (nextn) tensors. MTP in llama.cpp was built for single-stream use, and its recurrent-state batching across sequences is still unfinished. Grammar plus MTP has an open crash report. The draft-free n-gram modes exist, but on a hybrid model each rejected draft needs a state restore.

### Cited Findings
- **b11718 `--spec-type` values [BINARY]:** none, draft-simple, draft-eagle3, draft-mtp, draft-dflash, draft-dspark, ngram-simple, ngram-map-k, ngram-map-k4v, ngram-mod, ngram-cache. The default is none. `--spec-draft-n-max` defaults to 3. `--spec-draft-backend-sampling` defaults to enabled. The old `--draft*` flags were removed.
- **MTP PR #22673 [PUBLISHED]** (merged 2026-05-16):
  - "Parallel decoding with MTP is supported, but not fully optimized yet."
  - One commenter hit "MTP currently supports only n_parallel=1".
  - "Multi-seq recurrent states are not contiguous, so they cannot be batched" is a post-merge TODO, and prompt processing is slower with MTP.
  - Single-stream gains: decode went from 22.97 to 42.45 tok/s on an RTX 3090 + 3060, and from 18.51 to 32.24 tok/s on 3× RTX 3060. — [PR #22673](https://github.com/ggml-org/llama.cpp/pull/22673)
- **[BINARY]** b11718 `llama-server-impl.dll` no longer contains the "MTP currently supports only n_parallel" string. It does contain "accepted %zu/%zu draft tokens (restore checkpoint)", so rejected drafts on recurrent models roll back through checkpoints.
- **[LOCAL GGUF check]** `Qwen3.5-2B-Q4_K_M.gguf` metadata has no `nextn` keys, only `qwen35.block_count`, `ssm.*` and `full_attention_interval`. That means no MTP head.
- **[PUBLISHED]** Issue #30419: the grammar stack dies with a json_schema response_format under `--spec-type draft-mtp`. — [Issue #30419](https://github.com/ggml-org/llama.cpp/issues/30419)
- **[PUBLISHED, community]** Guides report that the MTP advantage is gone by about 4 concurrent streams, and they recommend `--parallel 1`. — [runaihome guide](https://runaihome.com/blog/speculative-decoding-llama-cpp-local-llm-setup-2026/), [Dre Dyson guide](https://dredyson.com/the-hidden-truth-about-mtp-and-llama-cpp-with-qwen3-6-27b-insider-tips-advanced-configuration-gotchas-and-what-nobody-talks-about-a-complete-behind-the-scenes-guide/) (secondary sources)
- **[PRIOR]** MTP would multiply the recurrent state per slot. At 53 slots the GPU is not idle between steps.

### Inferences
- **Leave `--spec-type none` at high `-np`.** Speculation trades spare GPU compute for latency, and at 53 slots there is no spare compute.
- **Possible low-slot "fast lane" (8 slots or fewer):** test `--spec-type ngram-mod` or `ngram-simple` only for outputs that copy input text verbatim. Each rejection costs a 19 MiB state restore [INFERRED].

### Gaps
- No benchmark of n-gram speculation with a hybrid recurrent model at `-np` > 1 was found.

---

## 8. How to measure all this reliably (llama-bench, llama-batched-bench, /metrics, /slots, logs)

### Takeaway
Use three layers of measurement. llama-bench and llama-batched-bench give the GPU ceiling. The server's `--metrics` and `/slots` endpoints and the per-task `print_timing` and `release` log lines give the server's real behaviour. Errand's own pages/s and accuracy, repeated over several runs, are the objective. Job counts should be a multiple of `-np`.

### Cited Findings
- **`/metrics` (requires `--metrics`) [PUBLISHED][BINARY]:**
  - `llamacpp:prompt_tokens_total`, `prompt_seconds_total`, `prompt_tokens_seconds`
  - `tokens_predicted_total`, `tokens_predicted_seconds_total`, `predicted_tokens_seconds`
  - `requests_processing`, `requests_deferred`
  - `n_tokens_max`, `n_decode_total`, `n_busy_slots_per_decode`
  - `spec_decode_*`
  - Source: [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **`/slots` (enabled by default) [PUBLISHED]:** fields `id`, `id_task`, `n_ctx`, `speculative`, `is_processing`, `params` (samplers, chat_format, reasoning_format) and `next_token` (`n_decoded`, `n_remain`). `?fail_on_no_slot=1` returns 503 when no slot is free. — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **Response fields [PUBLISHED][BINARY]:** `timings` (includes `prompt_per_second` and `predicted_per_second`), `tokens_cached`, `tokens_evaluated`, and the streaming `prompt_progress` {total, cache, processed, time_ms}. — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **Log lines that work for analysis [LOG]:**
  - `print_timing` prompt and eval lines (ms per token, tokens).
  - `release: ... n_tokens = N`. Reused prefix = N − (prompt + gen − 1).
  - `get_available_slot` selection reason ("by LRU" or "by LCP similarity, f_sim_best").
  - `erasing old context checkpoint`.
  - `making room for prompt cache entry`.
  - Backend-sampling disable warnings.
- **[PRIOR]** Measured on this laptop: `llama-batched-bench -npp 640 -ntg 64 -npl 1,8,32,64,128 ...` and `llama-bench` ub sweeps. A job count that is not a multiple of the slot count distorted the 70- and 80-slot results.
- **[PUBLISHED]** PR #17004 lists "extend llama-bench and llama-batched-bench to support backend samplers" as follow-up work. The bench tools may not reflect `-bs`. — [PR #17004](https://github.com/ggml-org/llama.cpp/pull/17004)

### Inferences

#### Knob table for the tuner (b11718; current value → values to sweep)
| knob | current | sweep | main effect | evidence |
|---|---|---|---|---|
| output mode | json_schema grammar | {plain/pointer + parser, flat schema, full schema} | biggest single throughput lever; grammar also blocks `-bs` | LOG 194 vs 344 ms/step; CODE |
| `-bs` | off | {off, on} (only without grammar or reasoning budget) | removes CPU sampling of the full vocab; PRIOR estimate +10–15% | CODE, PR #17004 |
| reasoning | `--reasoning-budget 0` | {`-rea off`, budget 0} | `-rea off` unblocks `-bs`; check for `<think>` | CODE, issues #20182/#20409 |
| `-ctxcp` | 2 | {0, 2, 3, 4} | 3+ keeps the system-prompt checkpoint, so prefix reuse is possible | LOG 2/105 and 17/105 reuse; CODE |
| prompt layout | ~99 shared tokens | shared instructions/schema first, page last | turns prefix reuse into real prefill savings | CODE + COMPUTED |
| `-ub` | 512 | {512, 1024, 2048} | +4–5% prefill; ub ≥ prompt also avoids the third checkpoint | PRIOR bench; CODE |
| `-cram` | 2048 | {0, 2048} | removes 62–66 MiB host-cache saves per task | LOG, PRIOR |
| `-sps` | 0.10 | {0, 0.10} | slot choice only; minor | CODE, LOG |
| `-np` | 53 | {24, 32, 53, 64} | throughput flat past ~50; latency ∝ slots | PRIOR |
| `-c` per slot | 4096 | {2048, 4096} | VRAM headroom for ub or checkpoints | PRIOR |
| `-ctk/-ctv` | q8_0 | {q8_0, f16} | accuracy check; speed ≈ same | PRIOR, localbench |
| temperature / top_k | (client) | {0/1, 0.2/20, 0.5/20} | accuracy and voting diversity | Qwen card |
| presence_penalty | (client) | {0, 0.5} | repetition vs language mixing | Qwen card |
| logprobs | off | {off, top_logprobs 3} | confidence signal; check CPU cost | BINARY |
| `--prio`, `--poll`, affinity | defaults | {prio 0/2, poll 50/0} | single sampling thread vs browsers on the CPU | INFERRED |
| `--spec-type` | none | keep none at high np | no MTP head in GGUF; unfinished at np>1 | PR #22673, local GGUF |

- **Protocol.** For each configuration:
  - Run a fixed job set sized as a multiple of `-np`, at least 3 repeats.
  - Record pages/s, p50/p95 latency, JSON-valid rate and field accuracy.
  - Scrape `/metrics` and check `n_busy_slots_per_decode` and `requests_deferred`.
  - Grep the log for reuse counts and sampling-disable warnings.
  - Run `nvidia-smi` for VRAM, including shared-memory spill.
- **Because of nondeterminism across batch sizes,** compare accuracy with a tolerance band, not single runs.

### Gaps
- Whether `timings` carries `cache_n` and `prompt_n` in b11718 was not confirmed: the `cache_n` string was not found in the binary. Use `tokens_cached` or the log arithmetic instead.
- No official guide to tuning llama-server for many small concurrent requests on a 6 GB GPU was found. The table above rests on Errand's measurements plus code reading.
