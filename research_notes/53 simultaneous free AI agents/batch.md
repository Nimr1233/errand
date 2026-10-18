# 53 simultaneous LLM conversations on one RTX 3060 Laptop GPU (6 GB) via batched/parallel serving, as of Oct 2026

Research date: 2026-10-18. All sources were fetched that day unless noted. Labels: **[measured]** means a number someone actually ran. **[calc]** means arithmetic on published model configs. **[estimate]** means my extrapolation, not measured on this hardware.

Assumed workload per agent step: about 4k prompt tokens (pruned page snapshot plus short history) and about 50-150 output tokens of JSON. 53 slots x 4,096 tokens = **217,088 KV tokens** in total. 53 x 6,144 = 325,632 tokens.

---

## 1. llama.cpp server: parallel slots, continuous batching, unified KV, KV quantization, flash attention, and how context is split

### Takeaway
llama-server can run 53 slots in one process with one loaded model (`-np 53`), and continuous batching is on by default. With `-kvu` (unified KV), `-c` becomes one shared pool rather than a fixed split per slot. The newer `--kv-unified-per-slot N` flag caps each slot. KV can be quantized to q8_0 or q4_0, and flash attention is set to auto.

### Cited Findings
- `-np, --parallel N`: "number of server slots (default: -1, -1 = auto)" — [llama.cpp server README (master, fetched 2026-10-18)](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- `-kvu, --kv-unified`: "use single unified KV buffer shared across all sequences (default: enabled if number of slots is auto)" — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- `--kv-unified-per-slot N`: "context limit per parallel slot (default: unset, behavior unchanged)". When set without `-c`, "the shared KV pool is sized to n_parallel*N" — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- `-cb, --cont-batching`: continuous (dynamic) batching, "default: enabled" — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- `-ctk/-ctv` cache types: f32, f16, bf16, q8_0, q4_0, q4_1, iq4_nl, q5_0, q5_1. The default is f16 — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- `-fa, --flash-attn [on|off|auto]`, default 'auto' — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- Prompt caching is enabled by default (`--cache-prompt`). `--cache-reuse N` reuses chunks via KV shifting. `-cram, --cache-ram N` sets the host-RAM prompt cache, default 8192 MiB. `--cache-idle-slots` saves idle slots to the prompt cache. `-ctxcp, --ctx-checkpoints` sets the "max number of context checkpoints to create per slot (default: 32)". `-cms, --checkpoint-min-step` defaults to 8192 tokens — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- Batch sizes: `-b` logical max is 2048 by default, `-ub` physical max is 512 by default — [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- How the context is split. With explicit `--parallel N` and no unified KV, `--ctx-size M` gives M/N tokens per slot, so `-c 32768 -np 8` means 4,096 per request. With unified KV, n_ctx is one pool shared by the slots (secondary guide) — [openclawdc guide](https://openclawdc.com/blog/check-runtime-kv-cache-allocation/), [llama-cpp-ex performance guide](https://llama-cpp-ex.hexdocs.pm/performance.html)
- With a unified KV cache, `--ctx-size` "sets the total unified kv cache size that is shared by all slots during parallel processing, and also sets the max prompt length for any single prompt" (a user discussion asking for a separate per-request cap; `--kv-unified-per-slot` appears to be the later answer) — [llama.cpp discussion #22658](https://github.com/ggml-org/llama.cpp/discussions/22658)
- Slot defaults have shifted between builds. One issue reports the server switching to 4 slots with unified KV when parallel wasn't set as expected — [llama.cpp issue #17989](https://github.com/ggml-org/llama.cpp/issues/17989)

### Inferences
- **[estimate] Suggested launch line for this laptop, not tested:**
  `llama-server -m <model>.gguf -ngl 99 -np 53 -kvu --kv-unified-per-slot 4608 -fa on -ctk q8_0 -ctv q8_0 -b 2048 -ub 1024 -ctxcp 2 -cram 2048`
  - `--kv-unified-per-slot` keeps one runaway conversation from eating the shared pool.
  - q8_0 KV halves KV memory. Flash attention is needed for quantized V cache in practice. The Ollama docs say KV quantization only applies with FA on (see section 6).
  - `-ctxcp 2` matters. On hybrid models (Qwen3.5, LFM2) each checkpoint holds a copy of the recurrent state, about 19 MiB per Qwen3.5-2B sequence (see section 3). The default of 32 checkpoints per slot x 53 slots x 19 MiB is about 32 GiB worst case, which is more than the 16 GB of system RAM. My assumption is that checkpoints live in host RAM.
  - `-cram 2048` keeps the host prompt cache from competing with the browsers for the 16 GB of RAM.
- Use the server's JSON-schema/grammar-constrained output (`response_format` / `json_schema`, documented in the same README) so every 50-150-token tool call parses. This also stops runaway generations from eating decode time.
- Put the page snapshot at the end of the prompt (system prompt, then tool schema, then history, then snapshot). Each slot's prompt cache can then reuse the unchanged prefix on the next step.

### Gaps
- I could not find what `-np -1` "auto" resolves to on the current build. The secondary sources say 4.
- I found no documentation of what happens when the unified pool fills (error, eviction, or a stall).
- I could not confirm whether context checkpoints are stored in VRAM or host RAM, or how `-cms 8192` interacts with 4k prompts on hybrid models (prefix reuse may be limited).

---

## 2. vLLM / SGLang / LMDeploy / ExLlamaV2-V3 + TabbyAPI / Aphrodite on Windows with a 6 GB GPU

### Takeaway
vLLM is Linux-only. It works under WSL2, but on 6 GB cards users report only about 5 GiB usable, and they had to cut sequences and context sharply. llama.cpp (native Windows CUDA build) is the low-friction choice for 53 slots on this laptop. I found no evidence that vLLM or SGLang does better on a 6 GB WSL2 setup.

### Cited Findings
- "vLLM does not support Windows natively." The docs recommend WSL with a compatible Linux distro or community forks. OS: Linux. NVIDIA minimum is compute capability 7.5 — [vLLM GPU installation docs](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html)
- On a 6 GiB Quadro RTX 3000 Max-Q under WSL2, a user reported about 4.99 GiB usable. They ran Qwen3-0.6B only after lowering context and batch, with `--max-num-seqs 1` and `--gpu-memory-utilization 0.80`. FlashInfer JIT needed nvcc, so the CUDA Toolkit had to be installed inside WSL2. (This came via a search summary. The exact page was one of the linked results and was not fetched in full.) — [dev.to: tiny LLMs with vLLM on WSL2](https://dev.to/lugerlogic/running-tiny-llms-on-your-local-machine-with-vllm-wsl2-no-cloud-needed-5c44), [hackmd note](https://hackmd.io/@alphast0rm/Hy2cwV0Vfe.md)
- For hybrid (Mamba-style) models, the default `max-num-seqs` of 256 can exceed the available Mamba cache blocks, and a guide recommended 64 (on a larger GPU) — [Qwen3.6-27B-FP8 HF discussion](https://huggingface.co/Qwen/Qwen3.6-27B-FP8/discussions/10) (search summary, not fetched in full)
- An 8 GB laptop-GPU user under WSL2 reported vLLM was only usable with ~1B models — [r/LocalLLaMA thread (mirror)](https://redlib.ssps.io/r/LocalLLaMA/comments/1l8t8n8/huge_vram_usage_with_vllm) (search summary)

### Inferences
- **[estimate]** vLLM's PagedAttention and automatic prefix caching would in principle suit 53 agents sharing a system prompt. On 6 GB under WSL2, though, the PyTorch/CUDA-graph overhead plus the gpu-memory-utilization headroom leaves roughly 2-3 GiB for KV after the weights of a 1-2B model. That is less than llama.cpp leaves, and WSL2 adds RAM overhead on a 16 GB machine that also has to run 53 browser contexts.
- SGLang, LMDeploy and Aphrodite are Linux-first like vLLM. They would also need WSL2, with the same VRAM and RAM pressure.
- ExLlamaV2/V3 + TabbyAPI run natively on Windows and support dynamic batching. Whether they support Qwen3.5 (Gated DeltaNet) or LFM2 is unverified.

### Gaps
- I found no measured vLLM, SGLang or LMDeploy runs with 32-64 concurrent sequences on an RTX 3060 Laptop 6 GB.
- I did not verify whether vLLM prefix caching works for hybrid models (Qwen3.5) in current releases.
- I did not verify ExLlamaV3/TabbyAPI architecture support for Qwen3.5 or LFM2, or Aphrodite's status in 2026.

---

## 3. KV-cache memory math: which models fit weights + 53 x ~4k contexts in ~6 GB

### Takeaway
Only hybrid models with very few attention layers fit. **Qwen3.5-0.8B, Qwen3.5-2B, LFM2.5-1.2B and LFM2-2.6B fit 53 x 4k in about 2.6-4.3 GiB with q8_0 KV [calc+estimate].** Qwen3.5-4B (about 8-9.5 GiB) does not fit. Pure-attention small models like Qwen3-1.7B need 6.5-23 GiB of KV and do not fit at 53 x 4k.

### Cited Findings
- **Qwen3.5-2B** text_config: 24 layers, `full_attention_interval` 4 (3 linear GDN : 1 full attention, so 6 full-attention layers), 8 attention heads, **2 KV heads, head_dim 256**, hidden 2048. Linear attention: 16 key heads, 16 value heads, key/value head dim 128, conv kernel 4. Vocab 248,320, tied embeddings, max positions 262,144 — [Qwen3.5-2B config.json](https://huggingface.co/Qwen/Qwen3.5-2B/raw/main/config.json)
- **Qwen3.5-0.8B**: 24 layers, interval 4, 8 heads, **2 KV heads, head_dim 256**, hidden 1024. Linear: 16 k-heads, 16 v-heads, dims 128, conv 4. Vocab 248,320 — [Qwen3.5-0.8B config.json](https://huggingface.co/Qwen/Qwen3.5-0.8B/raw/main/config.json)
- **Qwen3.5-4B**: 32 layers, interval 4 (8 full-attention layers), 16 heads, **4 KV heads, head_dim 256**, hidden 2560. Linear: 16 k-heads, **32 v-heads**, dims 128, conv 4 — [Qwen3.5-4B config.json](https://huggingface.co/Qwen/Qwen3.5-4B/raw/main/config.json)
- The Qwen3.5 small series (0.8B, 2B, 4B, 9B) was released March 2, 2026 under Apache 2.0 — [Gigazine](https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small), [InsiderLLM](https://insiderllm.com/guides/qwen-3-5-small-models-9b-beats-30b/)
- **LFM2.5-1.2B-Instruct**: 16 layers, of which 6 are full attention (indices 2, 5, 8, 10, 12, 14) and 10 are short conv. 32 heads, **8 KV heads**, hidden 2048 (so head_dim 64), conv_L_cache 3, vocab 65,536, max positions 128,000 — [LFM2.5-1.2B-Instruct config.json](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct/raw/main/config.json)
- **LFM2-2.6B**: 30 layers, 8 full attention (indices 2, 5, 9, 13, 17, 21, 24, 27), the rest conv. 32 heads, **8 KV heads**, hidden 2048 (so head_dim 64), conv_L_cache 3, vocab 65,536 — [LFM2-2.6B config.json](https://huggingface.co/LiquidAI/LFM2-2.6B/raw/main/config.json)
- llama.cpp's recurrent memory (used for the linear/conv layers of hybrid models) is sized per sequence by `n_seq_max`, and its size does not depend on context length — [llama-memory-recurrent.h mirror](https://huggingface.co/OpenTransformer/llama.cpp-prismml/blob/main/src/llama-memory-recurrent.h)
- KV quantization in Ollama/llama.cpp: q8_0 uses about half the memory of f16, q4_0 about a quarter — [Ollama FAQ](https://docs.ollama.com/faq)

### Inferences
**[calc] KV bytes per token** = full-attention layers x KV heads x head_dim x 2 (K and V) x bytes per element. Bytes per element: f16 = 2, q8_0 = 34/32 = 1.0625, q4_0 = 18/32 = 0.5625.

| Model | Attn layers x KV heads x head_dim | f16 B/token | q8_0 B/token | 53x4k (217,088 tok) f16 / q8_0 / q4_0 |
|---|---|---|---|---|
| Qwen3.5-0.8B | 6 x 2 x 256 | 12,288 | 6,528 | 2.48 / 1.32 / 0.70 GiB |
| Qwen3.5-2B | 6 x 2 x 256 | 12,288 | 6,528 | 2.48 / 1.32 / 0.70 GiB |
| Qwen3.5-4B | 8 x 4 x 256 | 32,768 | 17,408 | 6.63 / 3.52 / 1.86 GiB |
| LFM2.5-1.2B | 6 x 8 x 64 | 12,288 | 6,528 | 2.48 / 1.32 / 0.70 GiB |
| LFM2-2.6B | 8 x 8 x 64 | 16,384 | 8,704 | 3.31 / 1.76 / 0.93 GiB |
| Qwen3-1.7B (config not fetched; assumed 28 layers x 8 KV x 128) | 28 x 8 x 128 | 114,688 | 60,928 | 23.2 / 12.3 / 6.5 GiB |

At 53 x 6k (325,632 tokens), multiply the 4k column by 1.5. For example, Qwen3.5-2B q8_0 is 1.98 GiB.

**[calc] Recurrent state per sequence.** It is fixed, independent of context, and assumed stored in f32 as llama.cpp does by default.
- Qwen3.5-0.8B and 2B: 18 GDN layers. Each layer holds an S state of 16 v-heads x 128 x 128 = 262,144 floats plus a conv state of 3 x (2048 + 2048 + 2048) = 18,432 floats, which is 1.12 MB per layer. That gives **19.3 MiB per sequence, or about 1.00 GiB for 53 sequences.**
- Qwen3.5-4B: 24 GDN layers x (32 x 128 x 128 + 3 x 8192) floats x 4 B = **50.3 MiB per sequence, or about 2.60 GiB for 53.**
- LFM2 family: the conv state is about 10-22 layers x (2-3) x 2048 x 4 B, which is about 0.2-0.5 MiB per sequence, or about 10-30 MiB for 53. That is negligible.

**[estimate] Totals for 53 x 4k with q8_0 KV.** Weights are rough Q4_K_M GGUF sizes, not checked file sizes. Overhead for CUDA context and compute buffers is assumed at about 0.6-0.8 GiB.
- Qwen3.5-0.8B: about 0.55 + 1.32 + 1.00 + 0.75, so **~3.6 GiB. Fits.**
- Qwen3.5-2B: about 1.25 + 1.32 + 1.00 + 0.75, so **~4.3 GiB. Fits.** At 6k contexts with q8_0 it is about 5.0 GiB, which is borderline. Use q4_0 KV for 6k (about 4.0 GiB).
- LFM2.5-1.2B: about 0.7 + 1.32 + 0.01 + 0.6, so **~2.6 GiB. Fits easily.** Even Q8_0 weights with f16 KV come to about 4.3 GiB.
- LFM2-2.6B: about 1.55 + 1.76 + 0.03 + 0.7, so **~4.0 GiB. Fits.**
- Qwen3.5-4B: about 2.6 + 3.52 + 2.60 + 0.75, so ~9.5 GiB (about 7.8 GiB with q4_0 KV). **Does not fit.** It would need roughly 20 or fewer slots, or partial CPU offload.
- Qwen3-1.7B: does not fit at 53 x 4k. A ~3.5 GiB q8_0 KV budget holds about 61k tokens, which is about 15 slots at 4k.
- Usable VRAM: on Optimus laptops the iGPU usually drives the screen, so most of the 6 GB is free. The WSL2 data point (about 4.99 GiB usable of 6 GiB) suggests planning for **about 5.0-5.3 GiB**.
- The large Qwen3.5 vocabulary (248k) adds weight size but not KV. Decode logits for 53 sequences take 53 x 248,320 x 4 B, which is about 53 MB.

### Gaps
- I did not fetch the configs for Gemma 3n/4 E2B/E4B (KV sharing plus sliding window could make them competitive, but the math needs the configs), SmolLM3-3B, Phi-4-mini, Granite 4.0-H (Mamba2 hybrids) or Qwen3-1.7B/4B. The Qwen3-1.7B row above is assumed, not verified.
- Exact GGUF file sizes and llama.cpp compute-buffer sizes for these models at `-ub 1024` with 53 sequences were not measured.
- I did not confirm whether llama.cpp allows a quantized recurrent-state type, which would shrink the 1-2.6 GiB of Qwen3.5 state.

---

## 4. Prefill is the bottleneck: time to prefill 53 x 4k on an RTX 3060 Laptop, and whether prefix caching helps

### Takeaway
Prefill is compute-bound and does **not** speed up with more slots. 217k tokens at about 4-12k tok/s means **roughly 20-55 s per "round" of 53 steps [estimate]**. Caching a shared system prompt only saves the fraction of each prompt that is shared, probably about 10-30%. Per-slot caching of the unchanged history prefix helps more if the snapshot sits at the end of the prompt.

### Cited Findings
- Desktop RTX 3060 12 GB, Llama 2 7B Q4_0: **pp512 2,407.67 t/s with FA on**, 2,137.50 with FA off. tg128 is 76.92 / 75.57 t/s. Under WSL2: pp512 2,407.93 (FA on), tg128 75.58 **[measured]**. There was no RTX 3060 Laptop entry — [llama.cpp CUDA scoreboard discussion #15013](https://github.com/ggml-org/llama.cpp/discussions/15013)
- The llama-batched-bench README example (hardware and model unstated) shows prompt-processing speed flat to slightly falling as parallel sequences grow: S_PP 1,186.64 t/s at B=1, 1,373.96 at B=4, 1,201.73 at B=32 **[measured]** — [batched-bench README](https://github.com/ggml-org/llama.cpp/blob/master/tools/batched-bench/README.md)
- batched-bench has a shared-prompt mode (`-pps`) where all sequences share one prompt, so N_KV = PP + B x TG instead of B x (PP + TG) — [batched-bench README](https://github.com/ggml-org/llama.cpp/blob/master/tools/batched-bench/README.md)

### Inferences
- **[calc]** Effective prefill compute on a desktop 3060 is about 2,408 t/s x 2 FLOP x 6.74B params, roughly 32 TFLOP/s. The laptop 3060 (power-limited, TGP-dependent) probably reaches about 70-100% of that **[estimate]**.
- **[estimate] Prefill speed on this laptop:** Qwen3.5-2B is about 1.4-1.5B non-embedding params, so roughly 2.9 GFLOP per token, giving a ceiling around 8-10k t/s. Small-model inefficiency and the less-optimized GDN kernels suggest **about 4-8k t/s** in practice. LFM2.5-1.2B (about 1.0B non-embedding) is about 6-12k t/s. Qwen3.5-0.8B is about 8-15k t/s.
- **[estimate] Prefill for 53 x 4k (217k tokens):** Qwen3.5-2B about 27-54 s. LFM2.5-1.2B about 18-36 s. Qwen3.5-0.8B about 15-27 s. This is the same total whether the requests run in parallel or one after another. Parallel slots only change who waits.
- If all 53 agents submit at once, every agent's first token comes only after most of the round's prefill is done. Per-agent step latency becomes about 30-60 s, compared with about 1.5 s for a lone agent.
- Prefix caching in llama.cpp is mainly per slot: each slot reuses its own previous prompt prefix. A 1k shared system prompt in a 4k prompt saves at most about 25% of prefill. The page snapshot (2-6k, new every step) can't be cached, and it dominates. The biggest real lever is **shrinking the snapshot**: 2k instead of 4k halves the round time.
- On hybrid models, prefix reuse depends on context checkpoints, because recurrent state can't be rolled back. See section 1 for the memory caveat.

### Gaps
- I found no measured pp numbers for the RTX 3060 Laptop specifically, nor for Qwen3.5 or LFM2 on any 30-series GPU.
- I found no data on Gated DeltaNet prefill kernel efficiency in llama.cpp CUDA versus standard attention.

---

## 5. Decode speed per conversation and in aggregate at 53 concurrent, and comparison with 53 sequential steps

### Takeaway
Batching multiplies aggregate decode throughput roughly 10x or more, but each stream slows down. **[estimate] At 53 concurrent on a 1-2B hybrid model: about 10-40 tok/s per conversation, about 500-2,000 tok/s aggregate**, so 100-token tool calls take about 3-10 s of decode per round. Because prefill dominates, a full round of 53 steps takes about 30-65 s versus about 70-95 s run one after another. That is **only ~1.5-2.5x throughput**, not 53x.

### Cited Findings
- batched-bench README example (128-token prompts, 128 generated): S_TG **41.57 t/s at B=1, 139.43 at B=8, 242.23 at B=16, 465.40 at B=32**. Aggregate scaling is about 11x at B=32, and per-sequence speed is about 14.5 t/s, which is about 35% of single-stream **[measured; hardware/model unstated]** — [batched-bench README](https://github.com/ggml-org/llama.cpp/blob/master/tools/batched-bench/README.md)
- A comparison article reports llama.cpp aggregate throughput rising about 7-14x from 1 to 64 concurrent requests, depending on the card. The RTX 3060 was not tested, and I saw this only as a search summary — [computingforgeeks: Ollama vs vLLM vs llama.cpp](https://computingforgeeks.com/ollama-vs-vllm-vs-llama-cpp/)
- Desktop RTX 3060, 7B Q4_0: tg128 about 77 t/s single-stream **[measured]** — [llama.cpp discussion #15013](https://github.com/ggml-org/llama.cpp/discussions/15013)

### Inferences
- **[calc]** 77 t/s x 3.56 GiB (7B Q4_0) gives about 290 GB/s effective bandwidth on the desktop 3060. The laptop's 192-bit GDDR6 is similar, so a 1.2 GB Q4 model has a ceiling of about 200+ t/s. **Expect about 120-200 t/s single-stream** for Qwen3.5-2B or LFM2.5-1.2B **[estimate]**.
- **[estimate] Per decode step at batch 53 (Qwen3.5-2B, 4k contexts, q8_0 KV), memory traffic is:**
  - weights, about 1.25 GB
  - KV reads, about 1.3 GiB
  - recurrent state read and write, about 2 x 1.0 GiB
  
  That totals about 4.6 GB, roughly 14 ms at about 336 GB/s. Compute adds about 53 x 2.9 GFLOP ≈ 154 GFLOP, roughly 5-6 ms. With kernel overhead, a step takes about 25-60 ms, giving **17-40 tok/s per conversation and about 900-2,100 tok/s aggregate**. LFM2.5-1.2B has almost no state traffic and should land at the faster end. Qwen3.5's per-sequence recurrent-state traffic is a real decode cost.
- **[estimate] Round comparison for 53 agent steps (4k in, 100 out, Qwen3.5-2B):**
  - Sequential: each step is about 0.6-1.0 s prefill plus 0.5-0.8 s decode, so 1.1-1.8 s. 53 steps take **about 60-95 s**.
  - Batched (`-np 53`): about 27-54 s prefill plus 3-6 s decode, so **about 30-60 s per round**. That is about 0.6-1.1 s per step amortized.
  - Net: **about 1.5-2.5x more total steps per second**. Each agent waits much longer per step (30-60 s instead of about 1.5 s).
- In practice the agents won't step in lockstep. Continuous batching interleaves arrivals, so the steady state is about 1-1.7 agent steps/s across all 53 "brains" **[estimate]**.
- Separate constraint: 53 concurrent browser contexts on 16 GB of RAM (at roughly 100-300 MB each) may bind before the GPU does **[estimate]**.

### Gaps
- I found no measured llama-batched-bench numbers at B≈48-64 with 2-6k prompts on any RTX 3060 (laptop or desktop). The user should run something like:
  `llama-batched-bench -m model.gguf -ngl 99 -fa on -ctk q8_0 -ctv q8_0 -kvu -c 230000 -b 2048 -ub 1024 -npp 4096 -ntg 128 -npl 1,8,16,32,53`
- I found no reports of 32-64-slot llama-server runs specifically on 6-8 GB laptop GPUs.
- The laptop's TGP (60-115 W variants exist) can shift all of these numbers by tens of percent. This is unverified for this unit.

---

## 6. Ollama: OLLAMA_NUM_PARALLEL limits and practicality for 53, versus raw llama.cpp

### Takeaway
Ollama allows parallel requests per model through OLLAMA_NUM_PARALLEL (default 1), and memory scales with parallel x context. The docs list no hard cap, but Ollama exposes fewer of the knobs that matter here: unified-KV per-slot caps, ubatch size, and checkpoint count. Raw llama-server is the better tool for 53 slots.

### Cited Findings
- OLLAMA_NUM_PARALLEL: "The maximum number of parallel requests each model will process at the same time, default 1." "Required RAM will scale by `OLLAMA_NUM_PARALLEL` * `OLLAMA_CONTEXT_LENGTH`." Example: a 2K context with 4 parallel requests becomes 8K — [Ollama FAQ](https://docs.ollama.com/faq)
- OLLAMA_MAX_QUEUE defaults to 512. OLLAMA_MAX_LOADED_MODELS defaults to 3 x number of GPUs. The default context is 4096 tokens — [Ollama FAQ](https://docs.ollama.com/faq)
- OLLAMA_KV_CACHE_TYPE can be f16 (default), q8_0 (about 1/2 memory) or q4_0 (about 1/4). It applies only when OLLAMA_FLASH_ATTENTION=1 — [Ollama FAQ](https://docs.ollama.com/faq)

### Inferences
- `OLLAMA_NUM_PARALLEL=53` with `OLLAMA_CONTEXT_LENGTH=4096`, `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0` should allocate the same about 217k-token KV as llama.cpp, so the memory math in section 3 applies **[estimate]**.
- llama-server is preferable because it exposes `--kv-unified-per-slot`, `-ub`, `-ctxcp`, `-cram` and grammar/JSON-schema output directly. It also avoids Ollama's scheduler deciding to offload or reduce parallelism.

### Gaps
- I could not confirm whether Ollama has an internal maximum for NUM_PARALLEL, or whether it auto-reduces parallelism when memory is short.
- Whether Ollama's engine currently supports Qwen3.5 GDN or LFM2.5 with parallel requests is unverified.

---

## 7. Multi-device tricks: Intel iGPU (Vulkan/SYCL) or CPU as extra workers

### Takeaway
Not worth it. The i5-10500H's iGPU and its 6 CPU cores share the roughly 40-47 GB/s system RAM bus with the browsers, so they would add perhaps 1-3 slow "brains" while starving the 53 browser contexts **[estimate]**.

### Cited Findings
- I found no sources for this question in my search budget.

### Inferences
- **[estimate]** CPU inference of a 1.2B Q4 model on 6 Skylake-class cores with AVX2: decode is perhaps 20-40 t/s and prefill perhaps 100-300 t/s. One 4k snapshot would take about 15-40 s to prefill, so the CPU adds well under one GPU-equivalent agent. It would also take CPU time away from Chromium.
- The Intel UHD iGPU (Gen9.5) through llama.cpp Vulkan would likely be slower than the CPU for prefill, and it shares the same RAM bandwidth.
- The better use of spare CPU is the browsers and the snapshot pruning, which shrinks prefill, the real bottleneck.

### Gaps
- I found no measured llama.cpp Vulkan or SYCL numbers for Intel UHD 630 or Gen9.5 iGPUs, and no CPU numbers for the i5-10500H.
- I did not check whether running a second llama-server on the CPU alongside the CUDA one causes contention problems on Windows.
