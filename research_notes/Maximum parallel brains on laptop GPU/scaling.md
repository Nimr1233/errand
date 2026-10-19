# How throughput scales with parallel slots ("brains") on a 6 GB RTX 3060 Laptop

Scope: llama.cpp b11718 (CUDA 12.4, Windows 11), Qwen3.5-2B Q4_K_M (1.18 GiB, 1.88 B params per llama-bench), `-fa on -ctk q8_0 -ctv q8_0`, extraction job of about 640 prompt tokens and 74 output tokens (mean). Notes written 2026-10-18.

Labels: **[MEASURED-USER]** = the user's `bench/brains.py` runs and server logs. **[MEASURED-HERE]** = llama-bench / llama-batched-bench I ran on this laptop on 2026-10-18. **[PUBLISHED]** = web source. **[CODE]** = b11718 source. **[COMPUTED]** = my arithmetic. **[INFERRED]** = reasoning I did not verify on the hardware.

---

## 1. The hardware

- **[MEASURED-HERE]** `nvidia-smi`: "NVIDIA GeForce RTX 3060 Laptop GPU", 6,144 MiB, power limit **75 W**, max SM clock 2,100 MHz, max memory clock 6,001 MHz, max PCIe link **gen 3 x16**. During a bench it sat at about 1,760 MHz and 57 W.
- **[COMPUTED]** A 6,001 MHz GDDR6 clock means 12 Gbps per pin. On a 192-bit bus that is **288 GB/s**, not the 336 GB/s of the higher-power variants.
- **[PUBLISHED]** LaptopMedia lists 336 GB/s for the 95 to 140 W variants, 282 GB/s for the 75 W variant and 288 GB/s for the 65 W variant. They also give 3,840 cores, 192-bit GDDR6, and up to 105 INT8 TOPS. TechPowerUp returned 403, so I could not check its numbers.
- **[COMPUTED]** Peak rates for GA106 (30 SM, 120 3rd-gen tensor cores, 3,840 FP32 lanes) at a sustained 1.5 to 1.7 GHz:
  - FP32 or FP16 on the shaders: 11.5 to 13.1 TFLOPS.
  - FP16 on the tensor cores: 46 to 52 TFLOPS with FP16 accumulate, 23 to 26 TFLOPS with FP32 accumulate (GeForce runs that at half rate).
  - INT8 on the tensor cores: 92 to 105 TOPS. This is the path llama.cpp's MMQ kernels use for Q4_K weights.
- PCIe 3.0 x16 gives roughly 12 GB/s in practice [INFERRED]. That matters because logits (248,320 x 4 B = 0.99 MB per output) and state saves cross this link.

## 2. The model as a workload

- **[COMPUTED]** Token embedding: 248,320 x 2,048 = 0.51 B params. Non-embedding: about 1.37 B.
  - Prefill: about 2 x 1.37 = **2.7 GFLOP per token**. Only the last prompt token pays for the LM head.
  - Decode: about 2 x 1.88 = **3.8 GFLOP per token**.
  - Attention FLOPs are small: only 6 of the 24 layers attend, at about 700 tokens.
- Per decode step and per sequence, the GPU must also move the Gated DeltaNet recurrent state: 19.27 MiB read plus written, about **40 MB per sequence per token** (see `limits.md` section 3b). The q8_0 KV read at about 700 tokens adds about 4.6 MB. That is **about 45 MB per sequence-token** on top of the 1.27 GB of weights shared by the whole batch.
- **[MEASURED-USER]** Each job is 627 to 655 prompt tokens and **74.4 output tokens on average** (max 111, so `max_tokens 300` never binds). The system prompt is about 80 tokens, roughly 12% of the prompt.
- Compute split per page **[COMPUTED]**: prefill 640 x 2.7 = 1.7 TFLOP, decode 74 x 3.8 = 0.28 TFLOP. **Prefill is about 86% of the FLOPs.**

## 3. Roofline: where decode should turn compute-bound

**[COMPUTED]** For weights only, arithmetic intensity is 3.8e9 x B / 1.27e9 = **3.0 x B FLOP/byte**. Decode turns compute-bound at B* = ridge / 3.0, where ridge = peak compute / bandwidth.

| compute ceiling used | ridge at 288 GB/s | B* (sequences) |
|---|---|---|
| INT8 tensor peak, 92 to 105 TOPS | 320 to 365 FLOP/B | about 105 to 120 |
| FP16 tensor (FP32 acc), 23 to 26 TFLOPS | 80 to 90 | about 27 to 30 |
| **Achieved prefill, 5,640 tok/s x 2.7 GFLOP = 15.5 TFLOPS** [MEASURED-HERE] | 54 (at 288 GB/s) to 93 (at the 167 GB/s achieved at B=1) | **about 18 to 31** |

What changes for this hybrid model: the per-sequence state traffic grows with B, so intensity tops out at 3.8e9 / 45e6 = **about 84 FLOP/byte** as B grows. That is below the INT8 ridge. In theory, decode never becomes compute-bound against INT8 peak; it ends up bound by per-sequence state traffic. That traffic alone would cap decode at 288e9 / 45e6 = **about 6,400 tok/s**.

**[MEASURED-HERE]** `llama-batched-bench -npp 640 -ntg 64 -npl 1,8,32,64,128 -c 92160 -np 128 -b 2048 -ub 512 -fa on -ctk q8_0 -ctv q8_0` (pure GPU work, no HTTP, no per-slot server work):

| B | S_PP tok/s | S_TG tok/s | ms per decode step | sequences/s (640+64 tokens each) |
|---|---|---|---|---|
| 1 | 5,235 | 132 | 7.6 | 1.64 |
| 8 | 5,388 | 425 | 18.8 | 3.71 |
| 32 | 5,647 | 882 | 36.3 | 5.38 |
| 64 | 5,600 | 956 | 66.9 | 5.52 |
| 128 | 5,522 | 1,006 | 127.2 | 5.57 |

- Prefill is flat at about 5,500 tok/s for every B. It is compute-saturated from one sequence on.
- Decode at B=1 moves 1.27 GB in 7.6 ms, about 167 GB/s, or 58% of 288 GB/s.
- Fitting S_TG = Tm x B / (B + k) gives Tm = 1,120 tok/s and k = 11.
- From B = 64 to 128, each extra sequence costs **0.94 ms per token**.
  - Floor for that cost [COMPUTED]: 3.8 GFLOP at 15.5 TFLOPS is 0.24 ms, plus 45 MB at 288 GB/s is 0.16 ms, giving 0.40 ms.
  - The other 0.5 ms or so goes to kernels that run less efficiently at decode shapes: the Gated DeltaNet and conv state updates, state gathers and copies, the LM head at small M, per-stream FA, and logits D2H (about 0.08 ms per sequence over PCIe 3) [INFERRED].
- **The GPU-only knee is at about 32 sequences.** At B=32 you already get 97% of the B=128 job rate (5.38 vs 5.57 seq/s). That fits the practical B* of 18 to 31 above.

## 4. Why the server saturates at about 2.8 pages/s, half the GPU ceiling

**[MEASURED-USER]**, from the result JSONs and `server-np*.log` `print_timing` lines:

| slots | pages/s | p50 s | prompt tok/s, whole run | gen tok/s, whole run | per-slot decode ms/step (median / min) | per-slot prefill tok/s (median) |
|---|---|---|---|---|---|---|
| 1 | 1.18 | 0.84 | 741 | 88 | 8.2 / 7.6 | 3,621 |
| 8 | 2.11 | 3.71 | 1,326 | 157 | 43.7 / 20.7 | 1,704 |
| 53 | 2.66 | 18.3 | 1,710 | 198 | 193 / 117 | 283 |
| 70* | 2.17 | 28.3 | 1,393 | 161 | 293 / 169 | 199 |
| 80* | 2.28 | 31.2 | 1,475 | 169 | 294 / 164 | 184 |
| 100 (2k ctx) | 2.69 | 32.5 | 1,757 | 200 | 284 / 134 | 179 |
| 128 (2k ctx, 128 jobs) | 2.84 | 40.3 | 1,858 | 210 | 343 / 192 | 168 |

\*With 105 jobs, 70 and 80 slots leave a half-empty second round (35 or 25 jobs), so their pages/s is understated. Per-slot ms/step mixes in other slots' prefill: the server packs decode tokens and prompt chunks into the same iteration. It is not a clean decode-step time.

Accounting per page **[COMPUTED]** from §3:
- GPU-only cost per page at large B: 655/5,640 = 0.116 s prefill, plus 74 x 0.94 ms = 0.070 s decode, plus a fixed per-step cost of about 0.007 s. Total about **0.19 s**, a ceiling of **about 5.3 pages/s**.
- Measured at 128 slots: 1/2.84 = **0.35 s per page**. About **0.16 s per page (46%) is not batched GPU work.**
- At 1 slot the same gap appears: 0.846 s measured against 0.12 + 74.5 x 7.6 ms = 0.69 s. That is **about 0.16 s per page again**. The overhead is a per-page serial cost that more slots do not hide.
- Breakdown at 1 slot:
  - Server prefill runs at 3,621 against 5,235 tok/s in the bench: +0.055 s. Likely causes: context-checkpoint breaks split the prompt into extra decodes, plus 2 x 19.3 MiB checkpoint copies.
  - Decode costs 8.2 against 7.6 ms per token: +0.045 s per page. This is CPU sampling. Without backend sampling, `common_sampler::set_logits` builds a full 248,320-entry candidate array per slot per token (`common/sampling.cpp:155-161`) on the single server thread.
  - About 0.06 s of per-request work remains: the 62 MiB prompt-cache save per finished request (the np8 log shows "making room for prompt cache entry ... size = 62 MiB" over and over), templating and tokenizing, and HTTP.
- [INFERRED] The split of the 0.16 s at 128 slots is not measured. The total matches; the exact components are a hypothesis to A/B test (§6).

**Answer to "where does adding brains stop helping":**
- The GPU saturates at **about 32 concurrent sequences**.
- The server, with the per-page serial cost, saturates at **about 50 to 64 slots**. 53 slots already gives 94% of the 128-slot rate (2.66 vs 2.84).
- Past about 64 slots, the only effects are more latency and more VRAM. The 128-slot run also spilled about 300 MiB to shared RAM, which risks a sudden slowdown.

## 5. Saturation model fit [COMPUTED]

Model: X(n) = Tm x n / (n + k), least-squares grid fit to pages/s. In a closed loop with n requests in flight, Little's law gives mean latency L = n / X = (n + k) / Tm.

| fit | Tm (pages/s) | k (slots) | rms | X(64) | X(96) | X(128) | X(160) |
|---|---|---|---|---|---|---|---|
| **Clean: n = 1, 8, 53, 100, 128** (drops tail-hit 70/80) | **2.74** | **1.5** | 0.11 | 2.68 | 2.70 | 2.71 | 2.71 |
| All 7 points | 2.55 | 1.3 | 0.22 | 2.51 | 2.52 | 2.53 | 2.53 |
| Physical, from §4 terms: Tm = 1/(0.19 + 0.16 s), k = 74 x 7.6 ms / 0.35 s | 2.86 | 1.6 | n/a | 2.79 | 2.81 | 2.82 | 2.83 |

- Residuals for the clean fit: n=1 +0.10, n=8 **-0.19**, n=53 0.00, n=100 -0.01, n=128 +0.13. Because k is so small, the curve rises too fast at n = 8, where per-step cost is non-linear: MMVQ kernels for batch ≤ 8, MMQ above.
- The physical model reproduces the clean fit, so the small k is real. One slot already runs about 40% of the asymptote, and the curve is flat beyond about 30 slots.
- 160 slots needs 1,024 tokens per slot to fit in VRAM (`limits.md` §8: q8_0/1k gives about 149 slots with other apps open). Every model predicts **no gain** over 64.

## 6. Tuning that can actually raise throughput (b11718)

Ordered by expected effect on this workload. The prefill share, 0.116 s of the 0.35 s per page, cannot be reduced by any slot setting.

1. **Backend (GPU) sampling: `-bs` / `--backend-sampling`** ([CODE] `common/arg.cpp:2310`, "experimental, default disabled"; also per request `"backend_sampling": true`).
   - [PUBLISHED] PR #17004, merged 2026-01-04. Samplers that run on the GPU: temp, logit_bias, top_k, greedy, dist, min_p, top_p, temp_ext. Not compatible with grammar. One output per sequence per batch. At merge time it recommended `--parallel 1` and a CUDA build with `-DGGML_CUDA_CUB_3DOT2=ON`. PR #19833 (multiple outputs per sequence) was still a draft.
   - **Blocker in the user's command [CODE]:** `common/sampling.cpp:428-431` turns backend sampling off when the reasoning-budget sampler is active, and `--reasoning-budget 0` activates it (`reasoning_budget_tokens >= 0`, line 315). Swap `--reasoning-budget 0` for **`-rea off`**, which sets `enable_thinking=false` in the template (`arg.cpp:3711`). Do not use `response_format` / `json_schema`, because that is a grammar.
   - Expected gain [INFERRED]: removes the about 0.6 ms per token of CPU candidate building (about 0.045 s per page, roughly +10 to 15%) and most of the logits PCIe traffic. Check the output is identical at temperature 0.
2. **Cut per-request state copies: `-cram 0`, and test `-ctxcp 0` against 2.**
   - Each finished request saves a 62 MiB prompt-cache entry: 19.3 MiB recurrent state + 2 x 19.3 MiB checkpoints + KV. Bulk single-turn jobs never reuse it across slots.
   - b11718 places a checkpoint at the **start of the last user message** (`server-context.cpp:4095-4101`) and at 4 + n_ubatch and 4 tokens before the end of the prompt (lines 4106-4110, ref. PR #20288). The first one is what lets a slot reuse the 80-token system prompt; the end-of-prompt ones are useless for single-turn jobs.
   - `-ctxcp 0` loses the system-prompt reuse (12% more prefill, about 15 ms per page) but skips the checkpoint copies and the prompt splitting. **A/B both.** [INFERRED]
3. **`-ub 1024` (or 2048).**
   - [MEASURED-HERE] llama-bench pp2048: ub 256 = 5,010 to 5,120; **ub 512 = 5,570 to 5,640; ub 1024 = 5,800 to 5,860 (+4%); ub 2048 = 5,870 to 5,930 (+5%)**.
   - That lowers prefill, about 86% of the FLOPs, by about 4%. The compute buffer grows with ub (activations), so check the `compute buffer size` log line. `-b` (default 2048) must be ≥ ub. -b only sets how many prompt tokens one server iteration takes, not total work.
4. **KV type: keep q8_0.**
   - [MEASURED-HERE] Prefill speed is the same for every q8_0/f16 mix (all within ±2%).
   - The KV read is about 4.6 MB per sequence-token against about 40 MB of recurrent state, so f16 cannot speed up decode much [COMPUTED]. f16 costs +14.5 MiB per slot at 4k (`limits.md` §8).
   - `-fa on` must stay, because a quantized V cache needs it.
5. **Context per slot: 1,024 is enough** (640 + 111 max tokens). That saves VRAM, but adding slots does not add throughput (§5).
6. **Prompt-prefix caching:** the shared prefix is only about 80 of 640 tokens, so it saves at most about 12% of prefill.
   - `--cache-reuse` (KV shifting) does not apply to this hybrid context (the server disables it, `server-context.cpp:1333-1335`). Reuse goes through the per-slot user-start checkpoint above.
   - `-kvu` does not share recurrent state, so it gains nothing here (`limits.md` §4).
   - Moving the long static instructions into the system prompt raises the share that can be reused.
7. **No help expected:**
   - `-t` / `-tb`: the server loop and sampling are single-threaded, and all layers are on the GPU.
   - `--cont-batching`: on by default (`common/common.h:575`).
   - MTP speculative decoding: it multiplies recurrent state per slot (`limits.md` §3b), and at high batch the GPU is not idle between steps.
8. **Benchmark hygiene:** make the job count a multiple of the slot count (105 jobs: 35, 53 or 105 slots) or use a steady stream. Otherwise the tail round distorts the result, as it did at 70 and 80 slots.

## 7. Recommended slot counts [COMPUTED from §5 + MEASURED-USER latencies]

| goal | slots | expected pages/s | median latency |
|---|---|---|---|
| Max throughput (within 2 to 3% of the asymptote) | **48 to 64** (53 is measured) | 2.66 to 2.8 | 18 to 23 s |
| p50 under about 10 s | **about 24 to 26** (Little's law: 10 x Tm - k = 26; between measured n = 8 at 3.7 s and n = 53 at 18.3 s) | about 2.5 to 2.6 (about 92 to 95% of max) | about 9 to 10 s |
| p50 under about 30 s | **about 64 to 70** (measured 70 slots at 28.3 s, 80 at 31.2 s) | about 2.7 to 2.8 | 25 to 28 s |
| Not worth it | 100 to 160 | ≤ +3 to 5% vs 64 | 32 to 60 s, VRAM spill risk |

For a quick "fast answer" mode, 8 slots gives 2.1 pages/s at 3.7 s p50, which is already 75% of the maximum.

---

## Sources (accessed 2026-10-18)
- User's measurements: `bench/brains-np{1,8,53,70,80}.json`, `brains-np100-c2048.json`, `brains-np128-c2048.json`, `bench/server-np*.log`, `bench/brains.py` in this repo.
- My runs on this laptop, 2026-10-18: `llama-batched-bench.exe` and `llama-bench.exe` (b11718) at `C:\Users\Omer laptop\AppData\Local\Temp\errand\llama\`, model `...\errand\dl\Qwen3.5-2B-Q4_K_M.gguf`; `nvidia-smi` queries.
- llama.cpp b11718 source: `common/arg.cpp`, `common/sampling.cpp`, `common/common.h`, `tools/server/server-context.cpp`. https://github.com/ggml-org/llama.cpp/tree/b11718
- PR #17004 "sampling : add support for backend sampling", merged 2026-01-04 by ggerganov: https://github.com/ggml-org/llama.cpp/pull/17004
- PR #19833 "sampling : support multiple outputs per sequence" (draft at time of search): https://github.com/ggml-org/llama.cpp/pull/19833
- llama-server dev notes (server_context is single-threaded; heavy post-processing hurts multi-sequence throughput): https://huggingface.co/OpenTransformer/llama.cpp-prismml/blob/main/tools/server/README-dev.md
- RTX 3060 Laptop variants: LaptopMedia 115 W (336 GB/s): https://laptopmedia.com/video-card/nvidia-geforce-rtx-3060-laptop-115w/ ; 75 W (282 GB/s): https://laptopmedia.com/es/video-card/nvidia-geforce-rtx-3060-laptop-75w/ ; 105 INT8 TOPS: https://laptopmedia.com/it/?p=673174
- Published small-GPU numbers found: single-stream only. Hardware-Corner RTX 3060 12GB: Qwen3 8B Q4_K about 55 t/s. GigaGPU RTX 4060: LLaMA 3 8B Q4_K_M 18 t/s single, 23.4 t/s at bs=8, tool not stated. https://www.hardware-corner.net/gpu-llm-benchmarks/rtx-3060-12gb/ , https://gigagpu.com/?p=11103
- Sibling notes: `limits.md` in this folder (per-slot VRAM, recurrent state size, `-kvu`, checkpoints).

## Summary
- The GPU stops scaling at **about 32 parallel sequences**. In llama-batched-bench, prefill is flat at about 5,500 tok/s, and decode climbs from 132 tok/s (B=1) to 882 (B=32) and 1,006 (B=128). That matches a practical roofline crossover of B* ≈ 18 to 31, using the measured 15.5 TFLOPS. Theoretical INT8 peak would put the crossover at 105 to 120. For this hybrid model, the per-sequence recurrent state (about 40 MB moved per token) keeps decode from ever reaching INT8 compute-bound.
- llama-server stops scaling at **about 50 to 64 slots**, at about 2.7 to 2.8 pages/s. That is half the GPU-only ceiling of about 5.3 pages/s, because of about 0.16 s per page of serial overhead: CPU sampling over a 248k vocabulary, checkpoint and prompt-cache copies over PCIe 3.0, and per-request work.
- Saturation fit (clean points): **Tm = 2.74 pages/s, k = 1.5**. Predictions: 2.68 / 2.70 / 2.71 / 2.71 pages/s at 64 / 96 / 128 / 160 slots.
- Recommended: **about 53 to 64 slots** for maximum throughput, **about 25** for a p50 under 10 s, **about 64 to 70** for a p50 under 30 s.
- The biggest remaining levers are not slot count:
  - `-bs` with `-rea off` instead of `--reasoning-budget 0`.
  - `-cram 0`, and an A/B test of `-ctxcp`.
  - `-ub 1024` (+4% prefill, measured).

## Gaps
- The split of the 0.16 s per page overhead at high slot counts is inferred. Only the total is measured. Settle it by A/B testing the server with `-bs -rea off`, `-cram 0`, `-ctxcp 0`, and `-ub 1024` at 53 slots.
- Backend sampling is experimental in b11718. I have not checked whether it is compatible with this model/template, or whether the release binary was built with `GGML_CUDA_CUB_3DOT2`.
- Decode with f16 KV was not benchmarked, only prefill.
- No published llama-batched-bench data for 2B-class models on 3060/4060 laptops turned up. The batched-bench table above is the only batched reference.
- During one check, `nvidia-smi` showed 41% GPU utilization from another process before my runs. Bench numbers may be a few % low.
