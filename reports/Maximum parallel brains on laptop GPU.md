# About 80 brains fit on your laptop, but about 35 to 53 is where the speed runs out

Your laptop can hold **about 80 Qwen3.5-2B "brains" (llama-server slots) at once with 4,096 tokens of memory each**, and **about 115 with 2,048 tokens each**. Those numbers come from a memory formula worked out from the llama.cpp source code. It matches all seven of your test runs to within 1%. The software's hard limit is 256 slots ([llama.cpp b11718, `src/llama-cparams.h`](https://github.com/ggml-org/llama.cpp/tree/b11718)), but the 6 GB graphics card runs out long before that. **So yes, 60 to 70 brains is possible.** Your 70-slot run used 5,335 MiB and your 80-slot run used 5,822 MiB, both without overflowing. But they barely get more work done. The total speed levels off at **about 2.7 to 2.8 pages a second**. One brain alone already reaches 40% of that, 16 brains reach about 91%, and 53 brains reach 97%. After that, each extra brain mostly makes every answer wait longer: about a third of a second more per answer for each brain you add. **The best trade-off for real use is about 35 slots** when someone is waiting for the answers (an estimated 96% of top speed at about 13 seconds per answer). Use **53 slots** for big unattended batches (measured: 2.66 pages a second at 18 seconds per answer). Going from 53 to 70 brains bought no measurable speed and made each answer take 55% longer. Accuracy stayed at 92.6–93.2% at every slot count, so the choice only affects speed, not quality.

All figures are as of October 19, 2026. Hardware: RTX 3060 Laptop GPU (6,144 MiB, 75 W, 288 GB/s memory), 16 GB RAM, Windows 11. Software: llama-server b11718, Qwen3.5-2B Q4_K_M, flash attention on, q8_0 compressed memory. "Measured" means a run on your laptop (`bench/brains-*.json`). "Calculated" means worked out from the source code and the model's published design.

## What you measured

| Slots | Memory per slot (tokens) | Pages per second | Median wait per answer | Graphics memory used |
|---|---|---|---|---|
| 1 | 4,096 | 1.18 | 0.84 s | 1,710 MiB |
| 8 | 4,096 | 2.11 | 3.71 s | 2,069 MiB |
| 53 | 4,096 | 2.66 | 18.3 s | 4,426 MiB |
| 70 | 4,096 | 2.17* | 28.3 s | 5,335 MiB |
| 80 | 4,096 | 2.28* | 31.2 s | 5,822 MiB |
| 100 | 2,048 | 2.69 | 32.5 s | 5,205 MiB |
| 128 (128 jobs) | 2,048 | 2.84 | 40.3 s | 5,913 MiB, plus about 300 MiB spilled into system RAM |

\*The 70- and 80-slot speeds are too low because of how the test was set up. 105 jobs on 70 slots means one full round, then a second round with half the brains idle (35 or 25 jobs). The curve fit below puts their true speed at about 2.68.

## How much graphics memory each brain needs

Each brain needs three pieces of graphics memory. The model's file is loaded only once and shared by all of them.

1. **A fixed "running summary": 19.27 MiB per brain.** Qwen3.5-2B is a "hybrid" model. 18 of its 24 layers keep a fixed-size summary of the conversation instead of a growing memory. This summary is the same size however short the page is, and the compression setting (`-ctk/-ctv`) does not shrink it ([Qwen3.5-2B config](https://huggingface.co/Qwen/Qwen3.5-2B/blob/main/config.json); llama.cpp `src/llama-memory-recurrent.cpp`, `src/llama-hparams.cpp`).
2. **Growing memory ("KV cache"): 6.375 KiB per token**, in the 6 layers that do keep a full memory, compressed with q8_0. That is 25.5 MiB for a 4,096-token slot (`src/llama-kv-cache.cpp`).
3. **Working scratch space: 2 KiB per token.** Flash attention has to unpack the compressed memory into a temporary area to do its maths. That is 8 MiB for a 4,096-token slot (`ggml/src/ggml-cuda/fattn.cu`).

Put together, in plain terms:

> **Total graphics memory (MiB) ≈ 1,655 + slots × (19.3 + tokens per slot × 8.4 ÷ 1,024)**

- The **1,655 MiB** starting cost is the model, the fixed buffers, and about 495 MiB used by Windows and your other apps.
- That gives **52.8 MiB per brain at 4,096 tokens** and **36.0 MiB per brain at 2,048 tokens**.

### How well the formula fits your seven runs

| Slots | Tokens per slot | Formula predicts | Measured | Difference |
|---|---|---|---|---|
| 1 | 4,096 | 1,707 MiB | 1,710 MiB | −0.2% |
| 8 | 4,096 | 2,077 MiB | 2,069 MiB | +0.4% |
| 53 | 4,096 | 4,451 MiB | 4,426 MiB | +0.6% |
| 70 | 4,096 | 5,348 MiB | 5,335 MiB | +0.3% |
| 80 | 4,096 | 5,876 MiB | 5,822 MiB | +0.9% |
| 100 | 2,048 | 5,256 MiB | 5,205 MiB | +1.0% |
| 128 | 2,048 | 6,265 MiB | about 6,213 MiB (5,913 + 300 spilled) | +0.8% |

Every prediction is within 1%. The formula leans slightly high, so it is a safe planning tool.

There is a second check. If you ignore the source code and simply fit a straight line through the seven measurements, the data gives **1,655 MiB to start, 8.36 KiB per token and 18.8 MiB per brain**. The source code says 1,655, 8.375 and 19.27. Two independent routes give the same answer. That also confirms that the fixed summary, not the page memory, is the cost that grows fastest when you add brains with short pages.

## The most brains that fit

The notes assume about **5,800 MiB of the 6,144 MiB is usable under Windows** before it starts spilling into much slower system RAM. Your runs agree: 80 slots fit at 5,822 MiB, and the 128-slot run spilled at about 5,913 MiB.

| Memory compression | Tokens per slot | Memory per brain | Max brains, other apps open | Max brains, other apps closed |
|---|---|---|---|---|
| q8_0 (what you use) | 4,096 | 52.8 MiB | **78** (80 fit, just) | 87 |
| q8_0 | 3,072 | 44.4 MiB | 93 | 104 |
| q8_0 | 2,048 | 36.0 MiB | **115** | 128 |
| q8_0 | 1,024 | 27.6 MiB | 149 | 167 |
| q4_0 (stronger compression) | 4,096 | 40.8 MiB | 101 | 113 |
| q4_0 | 2,048 | 30.0 MiB | 138 | 154 |
| q4_0 | 1,024 | 24.6 MiB | 168 | 188 |

How to read it:

- **Leave 100–200 MiB spare** for the driver's own working memory. A comfortable everyday maximum is **about 75 brains at 4,096 tokens** or **about 110 at 2,048** (limits notes, §8).
- Your 128-slot, 2,048-token run asked for more than the 115 that fit. That is why about 300 MiB spilled into system RAM. Spilling can cause sudden slowdowns, so stay under the table's numbers.
- Your jobs use about 640 tokens of prompt plus at most 111 tokens of answer. **1,024 tokens per slot is enough for this job**, but shrinking it only buys more brains, and more brains do not buy speed (next section).
- **Even with almost no page memory, the 19.27 MiB fixed summary limits this model to about 215 brains** on this card. The software's 256 cap never comes into play.
- Two settings would quietly shrink these numbers. Speculative decoding (MTP) multiplies the fixed summary by up to 5×. The shared memory pool (`-kvu`) shares page memory but not the fixed summary, and adds its own overhead (`src/llama-memory-hybrid.cpp`; [PR #16736](https://github.com/ggml-org/llama.cpp/pull/16736)). Leave both off.

**System RAM is fine.** Each saved "checkpoint" is a 19.3 MiB copy of a brain's summary, kept in normal RAM. With `-ctxcp 2` that is about 2.6 GiB at 70 brains, 3.0 GiB at 80 and 4.8 GiB at 128, plus up to 2 GiB of prompt cache (`-cram 2048`). That fits in 16 GB alongside Chrome. Do not go back to the default of 32 checkpoints: at 53 brains that could reach about 32 GB ([PR #16382](https://github.com/ggml-org/llama.cpp/pull/16382); `common/common.h`).

## Speed stops growing long before memory runs out

### The curve

A simple saturation curve fits the five clean runs (1, 8, 53, 100 and 128 slots). The 70 and 80 runs are left out because of their half-empty second round.

> **Pages per second ≈ 2.74 × slots ÷ (slots + 1.5)**

In plain terms, the laptop's top speed is about **2.74 pages a second**. Half of that arrives with just 1.5 brains. The average error is 0.11 pages a second. A model built from the measured costs (GPU work plus the server's per-page overhead) gives almost the same curve: a top speed of 2.86 and a half-way point of 1.6 slots (scaling notes, §5).

| Slots | Measured pages/s | Curve pages/s | Share of top speed |
|---|---|---|---|
| 1 | 1.18 | 1.09 | 40% |
| 8 | 2.11 | 2.30 | 84% |
| 53 | 2.66 | 2.66 | 97% |
| 70 | 2.17 (tail round) | 2.68 | 98% |
| 80 | 2.28 (tail round) | 2.69 | 98% |
| 100 | 2.69 | 2.70 | 99% |
| 128 | 2.84 | 2.70 | 99% |

The curve's milestones:

- **90% of top speed at about 14 slots.**
- **95% at about 29 slots.**
- **97% at about 49 slots.**
- **98% at about 74 slots.**
- **99% only at about 150 slots.**

The curve slightly overshoots at 8 slots and undershoots at 128 slots. The GPU switches calculation methods above 8 at a time, which the simple curve cannot capture.

### Why the ceiling is about 2.8 pages a second

The GPU alone could do more. In llama.cpp's own batch benchmark on your laptop, with no server involved, it peaked at **about 5.5 pages' worth of work a second**, and it was already 97% of the way there at 32 at once. The server adds **about 0.16 seconds of one-at-a-time work per page**. That time goes to picking each next word on the CPU (from a 248,000-word vocabulary), copying saved states back and forth, and handling requests. That cost does not overlap with the GPU, and adding brains does not hide it. It halves the ceiling (scaling notes, §3–4; `common/sampling.cpp`).

### Time per answer grows in a straight line

Speed is flat at the top, so every brain you add just joins the queue. Your seven runs fit a straight line: **wait ≈ 2.0 s + 0.32 s × slots**. 53 slots means about 18 seconds, 70 about 25 to 28, and 128 about 40. Add 17 brains to 53 and the answers take about 10 seconds longer for about 1% more output.

## The best number of brains

| Slots | Pages per second | Median wait per answer | Graphics memory | Verdict |
|---|---|---|---|---|
| 8 | 2.11 (measured) | 3.7 s | 2.1 GB | Quick mode: 75–84% of top speed, fast answers |
| 16 | about 2.50 (curve) | about 7 s | about 2.5 GB | Good if you want answers in under 10 s |
| **35** | **about 2.63 (curve)** | **about 13 s** | **about 3.5 GB** | **Best all-round: 96% of top speed, leaves 2 GB free** |
| **53** | **2.66 (measured)** | **18.3 s** | **4.4 GB** | **Best for big unattended batches** |
| 64–70 | about 2.68 (curve) | 23–28 s | 5.0–5.3 GB | Works, but about 1% faster than 53 for 30–55% longer waits |
| 80 | about 2.69 (curve) | 31 s | 5.8 GB | Memory limit at 4,096 tokens; no speed gain |
| 100–128 (2,048 tokens) | 2.69–2.84 (measured) | 32–40 s | 5.2–6.2 GB | Up to 7% faster than 53 at 2.2× the wait; 128 spills to RAM |

Notes on the table:

- The 35-slot row is calculated from the curve, not measured. 35 also divides 105 jobs evenly (three full rounds), so it is a clean test to run next. 53 was a near-even split of 105 (53 + 52).
- If you measure "useful speed for each second of waiting", the answer always favours fewer brains. The practical knee sits between 16 and 53. Below 16 you lose noticeable speed. Above 53 you only add waiting.
- The 128-slot run's 2.84 is the highest measured. Part of that is because 128 jobs on 128 slots is a single full round. It also used memory the card does not have.

## Faster without more brains

The slot count is no longer the lever. These settings target the 0.16-second-per-page server overhead. None of them has been tested on your laptop yet, so A/B test each one at 53 slots (scaling notes, §6):

1. **Pick the next word on the GPU: `-bs`, and replace `--reasoning-budget 0` with `-rea off`.** The reasoning-budget setting silently turns GPU word-picking off (`common/sampling.cpp`). Expected gain is about +10–15%. This feature is still marked experimental ([PR #17004](https://github.com/ggml-org/llama.cpp/pull/17004)).
2. **`-cram 0`, and try `-ctxcp 0` against 2.** This stops the 62 MiB save after every finished job, which one-off jobs never reuse.
3. **`-ub 1024`.** Measured +4% faster page reading on your laptop.
4. **Shorter pages.** Reading the prompt is about 86% of the work. Trimming pages from about 640 tokens helps more than any slot setting.

## Limitations

- The 5,800 MiB usable-memory ceiling under Windows is an assumption. Your 80-slot (5,822 MiB) and 128-slot (spilled at about 5,913 MiB) runs support it, but it was not measured directly, and it shifts with whatever else uses the GPU.
- The memory formula's pieces are read from the source code and match your totals. The per-buffer lines in the server's start-up log (`KV buffer size`, `RS buffer size`, `compute buffer size`) were not checked one by one. The 1,024-token and q4_0 rows are calculated, not run.
- The 16- and 35-slot speeds and waits are read off the curve. Nothing between 8 and 53 slots was measured.
- Each setting was run once. The 70 and 80 runs were distorted by the half-empty second round. Laptop heat and power limits (it ran at about 57 of 75 W) can move results by a few percent. Another program was using the GPU during one check.
- The curve assumes the workload stays the same: about 640 prompt tokens and 74 answer tokens per job. Longer pages or answers shift both the ceiling and the waits.
- The waits are medians from fixed batches of jobs, not from a steady stream. They come out a little below what the queueing formula predicts (for example, 40 s measured against 47 s predicted at 128 slots).

## Sources

- Your runs: `bench/brains-np{1,8,53,70,80}.json`, `bench/brains-np100-c2048.json`, `bench/brains-np128-c2048.json`, `bench/server-np*.log`. Batch benchmark (`llama-batched-bench`, `llama-bench`, b11718) and `nvidia-smi` on your laptop, October 18, 2026.
- llama.cpp b11718 source, including `src/llama-cparams.h`, `src/llama-context.cpp`, `src/llama-kv-cache.cpp`, `src/llama-memory-recurrent.cpp`, `src/llama-memory-hybrid.cpp`, `src/llama-hparams.cpp`, `ggml/src/ggml-cuda/fattn.cu`, `common/sampling.cpp`, `common/common.h`, `tools/server/server-context.cpp`: https://github.com/ggml-org/llama.cpp/tree/b11718
- Qwen3.5-2B design (config.json): https://huggingface.co/Qwen/Qwen3.5-2B/blob/main/config.json
- llama.cpp PRs: [#15916, max slots raised to 256](https://github.com/ggml-org/llama.cpp/pull/15916); [#16736, shared memory pool](https://github.com/ggml-org/llama.cpp/pull/16736); [#16382, checkpoints for hybrid models](https://github.com/ggml-org/llama.cpp/pull/16382); [#17004, GPU word-picking](https://github.com/ggml-org/llama.cpp/pull/17004)
- RTX 3060 Laptop 75 W memory speed: https://laptopmedia.com/es/video-card/nvidia-geforce-rtx-3060-laptop-75w/
- Research notes behind this report: `research_notes/Maximum parallel brains on laptop GPU/limits.md` and `scaling.md`. Earlier report: `reports/53 simultaneous free AI agents.md`.
