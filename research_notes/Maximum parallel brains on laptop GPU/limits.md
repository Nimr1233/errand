# Parallel slot ("brain") limits for llama-server on a 6 GB laptop GPU

Scope: llama.cpp tag **b11718** (source read directly from `raw.githubusercontent.com/ggml-org/llama.cpp/b11718/...` on 2026-10-18), model Qwen3.5-2B Q4_K_M, RTX 3060 Laptop (Ampere, cc 8.6, 6,144 MiB), CUDA 12.4, Windows 11.
User flags: `-np N -c N*4096 -ngl 99 -fa on -ctk q8_0 -ctv q8_0 -ctxcp 2 -cram 2048 --reasoning-budget 0`.

Labels used below: **[CODE]** = read in b11718 source, **[DOC]** = README/PR page, **[MEASURED]** = user's numbers, **[COMPUTED]** = my arithmetic from code + config, **[INFERRED]** = my reasoning, not verified on hardware.

---

## 1. Hard cap on `-np` / `n_seq_max`

- **[CODE]** `src/llama-cparams.h:8`: `#define LLAMA_MAX_SEQ 256`. Exposed as `llama_max_parallel_sequences()` (`src/llama-cparams.cpp:3-5`).
- **[CODE]** `src/llama-context.cpp:186-189`: `cparams.n_seq_max = std::max(1u, params.n_seq_max); if (cparams.n_seq_max > LLAMA_MAX_SEQ) throw std::runtime_error("n_seq_max must be <= " + std::to_string(LLAMA_MAX_SEQ));`
- **[CODE]** The exception is caught in `llama_init_from_model` (`src/llama-context.cpp:4122`) and logged, so `-np 257` should print
  `llama_init_from_model: failed to initialize the context: n_seq_max must be <= 256`
  then `failed to create context with model '...'` (`common/common.cpp:1374/1433`), then the server's `failed to load model` / `exiting due to model loading error` (`tools/server/server-context.cpp:1223`, `tools/server/server.cpp:491`). I did not run this; the `-fit` pre-pass (on by default) may print extra lines first.
- **[CODE]** `-np` server mapping: `common_context_params_to_llama` sets `cparams.n_seq_max = params.n_parallel` (`common/common.cpp:1715`). `-np 0` is rejected at parse time ("invalid value for n_parallel", `common/arg.cpp:2548-2556`).
- **[CODE]** With unified KV, `llama_decode` checks seq ids against `LLAMA_MAX_SEQ` instead of `n_seq_max` (`src/llama-context.cpp:1849`).
- **[DOC] History:** PR #14188 renamed `LLAMA_MAX_PARALLEL_SEQUENCES` to `LLAMA_MAX_SEQ`. PR #15916 "llama : bump max seq limit from 64 to 256" (ggerganov, merged 2025-09-18) raised it from 64 to 256. In that PR's discussion the maintainers floated making the limit dynamic, but at b11718 it is still a compile-time 256.
- **[CODE] Server defaults:** `-np` defaults to `-1` (auto) for the server (`common/arg.cpp:1406`). Auto means `n_parallel = 4` plus `kv_unified = true` (`tools/server/server.cpp:168-173`). Any explicit `-np N` keeps `kv_unified = false` unless `-kvu` is passed (`common/common.h:580`). The user's run passed `-np` without `-kvu`, so it was **non-unified**.

**Answer:** the hard maximum is 256 slots. On this GPU memory runs out well before that (see section 7).

---

## 2. Qwen3.5-2B shape (from config.json)

Source: `https://huggingface.co/Qwen/Qwen3.5-2B/resolve/main/config.json` (fetched 2026-10-18), `text_config`:
- `num_hidden_layers` 24, `full_attention_interval` 4. `layer_types` has 18 `linear_attention` (Gated DeltaNet) and 6 `full_attention` layers (layers 4, 8, ..., 24, 1-based).
- Full attention: `num_attention_heads` 8, `num_key_value_heads` 2, `head_dim` 256, `attn_output_gate` true.
- Linear attention: `linear_num_key_heads` 16, `linear_num_value_heads` 16, `linear_key_head_dim` 128, `linear_value_head_dim` 128, `linear_conv_kernel_dim` 4, `mamba_ssm_dtype` float32.
- `hidden_size` 2048, `vocab_size` 248320, `max_position_embeddings` 262144, `mtp_num_hidden_layers` 1.

**[CODE] GGUF mapping** (`conversion/qwen.py:378-382`): `ssm.conv_kernel = 4`, `ssm.state_size = linear_key_head_dim = 128`, `ssm.group_count = linear_num_key_heads = 16`, `ssm.time_step_rank = linear_num_value_heads = 16`, `ssm.inner_size = 128*16 = 2048`.
**[CODE]** Recurrent layer flags (`src/models/qwen35.cpp:17-21`): `is_recr[i] = (i < n_layer) && ((i+1) % 4 != 0)`, so 18 recurrent and 6 attention layers. The MTP layer sits past `n_layer()` and is excluded from the main context's memory (filters at `src/llama-model.cpp:3124-3130`).

GGUF file size [DOC, HF API `unsloth/Qwen3.5-2B-GGUF`]: Q4_K_M = 1,280,835,840 B (1,221.5 MiB). Q4_0 = 1,214,873,856 B.

---

## 3. How llama.cpp allocates per-sequence memory for this hybrid model

**[CODE]** `src/llama-model.cpp:3191-3209` (default branch, `llm_arch_is_hybrid`, no SWA) creates a `llama_memory_hybrid` with:
- attention KV: `attn_kv_size = cparams.n_ctx_seq`, types from `-ctk/-ctv`, `unified = cparams.kv_unified`;
- recurrent: `recurrent_kv_size = max(1, n_seq_max)`, types **F32/F32 (fixed, not affected by -ctk/-ctv)**, `n_rs_seq = cparams.n_rs_seq`, `offload = offload_kqv` (on GPU with `-ngl 99`).

### 3a. KV cache (6 full-attention layers only)
- **[CODE]** `src/llama-kv-cache.cpp:84`: `n_stream = unified ? 1 : n_seq_max`. Lines 233-234: K and V tensors are `[n_embd_k_gqa, kv_size, n_stream]`.
- **[CODE]** `src/llama-context.cpp:377-393`: `n_ctx` is padded to 256. Non-unified: `n_ctx_seq = PAD(n_ctx / n_seq_max, 256)`. Unified: `n_ctx_seq = n_ctx`.
- So **total KV cells = n_ctx in both modes**: either n_seq_max streams of n_ctx/n_seq_max cells, or one stream of n_ctx cells. Unified mode does not change KV memory for a given `-c`; it only changes who can use which cells.
- **[COMPUTED]** Per token, all 6 layers: K+V = 6 x 2 x (2 heads x 256) = **6,144 elements/token**.
  - f16: 12,288 B = **12.0 KiB/token**
  - q8_0 (34 B per 32 elements): 6,528 B = **6.375 KiB/token**, i.e. 25.50 MiB per 4,096-token slot
  - q4_0 (18 B per 32 elements): 3,456 B = **3.375 KiB/token**, i.e. 13.50 MiB per 4,096-token slot

### 3b. Recurrent ("RS") state (18 Gated DeltaNet layers)
- **[CODE]** `src/llama-memory-recurrent.cpp:101-104`: `n_rows = mem_size * (1 + n_rs_seq)`; `r = [n_embd_r, n_rows]`, `s = [n_embd_s, n_rows]`. The log line is `... RS buffer size = X MiB` (line 125).
- **[CODE]** `src/llama-hparams.cpp:208-258`: `n_embd_r = (d_conv-1) * (d_inner + 2*n_group*d_state)` and `n_embd_s = d_state * d_inner`.
- **[COMPUTED]** `n_embd_r = 3 x (2048 + 2*16*128) = 18,432` f32 (72 KiB); `n_embd_s = 128 x 2048 = 262,144` f32 (1 MiB). Per layer per sequence: 1,122,304 B. x 18 layers = 20,201,472 B = **19.27 MiB per sequence**.
- **The recurrent state scales only with `-np`, regardless of context size.** `mem_size = max(1, n_seq_max)` and nothing in the formula depends on `n_ctx`. It is also always F32, so `-ctk/-ctv q4_0` does not shrink it.
- **[CODE]** `n_rs_seq` (rollback snapshots) multiplies the RS buffer by `(1 + n_rs_seq)`. Only MTP/EAGLE3/DFLASH/DSPARK speculative decoding sets it, to `draft.n_max` (`common/common.h:401-407`, `common/common.cpp:1716`). The default is no speculative decoding (`common/common.h:378`), so it is **0** for the user's flags. Enabling MTP speculative decoding with e.g. `--draft-max 4` would make RS **5x** (about 96 MiB per slot).

---

## 4. Unified KV (`-kvu`) and hybrid models

- **[DOC]** PR #14363 "llama : add high-throughput mode" (merged 2025-07-16) added `kv_unified` and the per-sequence multi-stream KV (default non-unified). PR #16736 "server : support unified cache across slots" (merged 2025-11-02) lets the server share one `-c` pool across all `-np` slots. Each slot can grow to the full pool. When the pool fills, idle slots are purged one at a time, then the decode is retried with half the batch.
- **[CODE] b11718 behavior:**
  - `tools/server/server-context.cpp:1810-1830` `try_clear_idle_slots()` runs only when `kv_unified` is set and purges one idle slot per retry. Lines 4330-4336: if nothing can be purged, `n_batch` is halved and the decode retried.
  - New flag `--kv-unified-per-slot N` (`common/arg.cpp:1652-1659`, `tools/server/server.cpp:178-186`, `server-context.cpp:4652-4660`) caps each slot's context. Without `-c`, it sizes the pool to `n_parallel * N`.
  - `--cache-idle-slots` (default on, needs `-cram`): with unified KV, idle slots are saved to the RAM prompt cache and then cleared from VRAM (`server-context.cpp:2884-2898`).
- **Interaction with the recurrent state [CODE]:** `kv_unified` goes only to the attention `llama_kv_cache`. `llama_memory_recurrent` always allocates `n_seq_max` state rows (`src/llama-memory-hybrid.cpp:33-63`). With `-kvu`, KV memory follows the pool size you choose (tokens actually needed), but **the 19.27 MiB per slot of recurrent state is still paid for every `-np` slot**, used or idle. For Qwen3.5-2B the recurrent state is the larger term at 4,096 tokens/slot with q4_0, and at 2,048 or fewer with q8_0. So `-kvu` helps much less here than on a pure-attention model.
- **Compute cost of unified mode [CODE + COMPUTED]:** the KQ mask is `[n_kv, n_tokens/n_stream, 1, n_stream]`, f16 with FA (`src/llama-graph.cpp:30-46`). In the worst-case reserve, `n_kv` is the whole stream (`src/llama-kv-cache.cpp:2819`).
  - Non-unified: `kv_size_per_slot x n_ubatch x 2 B`, about 4 MiB at 4,096 x 512, flat in `-np`.
  - Unified: `n_ctx(pool) x n_ubatch x 2 B`, about **1 KiB per pool token at `-ub 512`**. For example, a 217,088-token pool (53 x 4,096) gives a 530 x 217,088 x 2 B = 219 MiB mask in the compute buffer.
  - Decode attention in unified mode also scans the whole used part of the pool for every slot. PR #14363 gives this as the reason non-unified mode is faster when sequences do not share a prefix.
- **Takeaway [INFERRED]:** use `-kvu` only with a pool smaller than `np x per-slot-max`, e.g. `-np 80 -kvu -c 131072 --kv-unified-per-slot 4096`, and when most brains are short or idle at any moment. With `-c = np x 4096`, unified mode costs about 1 KiB/token more than non-unified and saves nothing.

---

## 5. Compute buffers: what grows with `-np`, `-b`, `-ub`

**[CODE]** `llama_context::sched_reserve` (`src/llama-context.cpp:728-770`) reserves the worst-case graph with:
- `n_seqs = n_seq_max` (**every slot in one ubatch**), `n_tokens = min(n_ctx, n_ubatch)`, rounded up to a multiple of `n_seqs` (`graph_reserve`, lines 2626-2628, e.g. 512 becomes 530 at np=53);
- `init_full()`: all KV streams at full size (`src/llama-kv-cache.cpp:2819-2831`);
- `n_outputs = min(n_tokens, n_outputs_max)`. The server sets `n_outputs_max = min(n_batch, n_parallel * (1 + n_draft))` (`server-context.cpp:42-53`, `common/speculative.cpp:2719-2728`), which is **= n_parallel** without speculative decoding.

What scales with `-np` in the CUDA compute buffer:
1. **FA f16 scratch for quantized KV (largest term) [CODE]:** on Ampere with q8_0/q4_0 K/V, the vector FA kernel is chosen only when `Q->ne[1] == 1` (`ggml/src/ggml-cuda/fattn.cu:636-662`). The prefill reserve has more than one token per stream, so it takes the MMA kernel, which needs K and V converted to f16. In b11718 this scratch is part of the FA node's allocation size (`fattn.cu:721-755`, `fattn-common.cuh:53-84`), so it is reserved in the compute buffer: `ggml_nelements(K) x 2 B` for K and again for V, over all cells in the ubatch's streams. At the full reserve this is **n_ctx x 512 x 2 B x 2 = 2 KiB per context token**, i.e. **8 MiB per 4,096-token slot**. It is only one layer's worth, because the allocator reuses it across layers. With f16 KV this term is 0.
2. Logits for `n_outputs = np`: 248,320 x 4 B = 0.95 MiB per slot. This sits at the end of the graph, so it probably overlaps rather than adds [INFERRED].
3. Gated DeltaNet temporaries: state gathers and new states, about 1 to 2 MiB per sequence per live layer (`src/llama-graph.cpp:3804-3840`). These are transient and likely below item 1 at 4,096 tokens/slot [INFERRED].
4. Unified mode only: the KQ mask, about 1 KiB per pool token at `-ub 512` (section 4).

- **`-b` (n_batch, default 2048):** does not enter the GPU reserve except through the `n_outputs_max` cap, which is `np` anyway. It is a logical/host-side batch size [CODE].
- **`-ub` (n_ubatch, default 512):** activations and the non-unified mask scale linearly with it, but these do not grow with `-np` (apart from the rounding above). In unified mode the mask is `pool x ub x 2 B`, so lowering `-ub` (e.g. 256) halves it. The FA f16 scratch does **not** depend on `-ub`.
- The host output buffer (logits copy) is pinned system RAM, not VRAM (`src/llama-context.cpp:2305-2310`, uses the device *host* buffer type): about 0.95 MiB per slot.
- Runtime caveat [INFERRED]: CUDA also has a lazily grown memory pool for some ops. VRAM read after real traffic can exceed VRAM read right after load by tens of MiB. Measure both.

---

## 6. Context checkpoints (`-ctxcp`) and prompt cache (`-cram`): system RAM, not VRAM

- **[CODE]** Checkpoints are `common_prompt_checkpoint { std::vector<uint8_t> data_tgt; ... }` (`common/common.h:1277-1291`), filled by `llama_state_seq_get_data_ext(..., LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY)` (`common/common.cpp:2385-2401`, `server-context.cpp:2598`). That is a device-to-host copy into ordinary heap memory.
- **[CODE]** With `PARTIAL_ONLY`, the attention KV cache writes nothing for non-SWA models (`src/llama-kv-cache.cpp:2079-2081`). The recurrent memory ignores flags and writes the sequence's full r+s state (`src/llama-memory-recurrent.cpp:788-789`). So **each checkpoint is about 19.3 MiB** for Qwen3.5-2B. [DOC] PR #16382 (merged 2025-10-03) added checkpointing for hybrid/recurrent models.
- **[COMPUTED]** Live checkpoints, worst case: `np x ctxcp x 19.3 MiB` = 53 x 2 x 19.3 = **about 2.0 GiB system RAM**. The default `-ctxcp 32` (`common/common.h:639`) would be up to about 32 GiB at 53 slots, so lowering it to 2 was the right call. `-cms` (min spacing, default 8192 tokens) also limits how many checkpoints get created.
- **[CODE/DOC]** `-cram N` caps the host-RAM prompt cache (`server_prompt_cache`, `tools/server/server-task.h:650-690`). Each cached entry counts its full state plus its checkpoints. Default 8192 MiB (`common/common.h:642`). PR #16391 (2025-10-09) says the cache lives in regular RAM.
- **Host RAM budget [COMPUTED]** for the 53-slot run: about 2.0 GiB of checkpoints + up to 2.0 GiB of prompt cache + about 50 MiB pinned logits + the mmapped model (about 1.2 GiB file, mostly paged in for the CPU-side token embedding). Roughly 5 to 5.5 GiB of system RAM in the worst case.

---

## 7. Check against the measurement

**[MEASURED]** total GPU used: 1 slot = 1,710 MiB, 8 slots = 2,069 MiB, 53 slots = 4,426 MiB (about 495 MiB of that is other apps).
- Slopes: 1 to 8 slots = 51.3 MiB/slot; 8 to 53 = 52.4 MiB/slot. A least-squares fit gives **52.3 MiB/slot**, intercept 1,654.5 MiB (about 1,160 MiB of llama-server fixed cost after removing the 495 MiB of other apps).

**[COMPUTED]** per slot at 4,096 tokens, q8_0:

| term | MiB/slot |
|---|---|
| KV q8_0, 6 layers x 4,096 tokens | 25.50 |
| Recurrent state, 18 layers, F32 | 19.27 |
| FA f16 conversion scratch (compute buffer) | 8.00 |
| **Total** | **52.77** |

52.77 predicted vs 52.3 measured is within 1%, so the model explains the measurement. The lower 1-to-8 slope fits the compute buffer peak being set by slot-independent prefill activations at small `np`, with the FA scratch only becoming the peak as `np` grows [INFERRED]. Measured costs not in my model: Windows/WDDM accounting and the ~495 MiB of other apps, which I treated as constant.
Check exact values in the server's startup log: `llama_kv_cache: CUDA0 KV buffer size`, `llama_memory_recurrent: CUDA0 RS buffer size` (should read 19.27 x np MiB), `sched_reserve: CUDA0 compute buffer size`, `CUDA_Host output buffer size`, `CUDA0 model buffer size`.

The fixed ~1,160 MiB is slightly below the 1,221.5 MiB GGUF file. My guess is that the MTP layer tensors are skipped when MTP is off (`mparams.load_mtp`, `common/common.cpp:1706`) and the CPU-side `token_embd` copy is not counted. I have not verified this [INFERRED].

---

## 8. Expected per-slot memory and maximum slots in ~5,800 MiB [COMPUTED]

Per slot = `ctx x (KV bytes/token + FA scratch 2 KiB/token if KV is quantized) + 19.27 MiB RS`. Non-unified, `-ub 512`, no speculative decoding.
Fixed base = 1,654.5 MiB measured intercept, which includes the ~495 MiB of other apps.
- Case A: 5,800 MiB is the ceiling for total GPU use **with** the other apps still open. That leaves 4,145 MiB for slots.
- Case B: other apps closed, so llama-server alone gets 5,800 MiB. That leaves 4,640 MiB for slots.

| KV type | tokens/slot | KV | FA scratch | RS | **MiB/slot** | max slots, A | max slots, B |
|---|---|---|---|---|---|---|---|
| q8_0 | 4,096 | 25.50 | 8.00 | 19.27 | **52.77** | **78** | 87 |
| q8_0 | 2,048 | 12.75 | 4.00 | 19.27 | **36.02** | **115** | 128 |
| q8_0 | 1,024 | 6.38 | 2.00 | 19.27 | **27.64** | **149** | 167 |
| q4_0 | 4,096 | 13.50 | 8.00 | 19.27 | **40.77** | **101** | 113 |
| q4_0 | 2,048 | 6.75 | 4.00 | 19.27 | **30.02** | **138** | 154 |
| q4_0 | 1,024 | 3.38 | 2.00 | 19.27 | **24.64** | **168** | 188 |
| f16 (reference) | 4,096 | 48.00 | 0 | 19.27 | 67.27 | 61 | 68 |
| f16 (reference) | 2,048 | 24.00 | 0 | 19.27 | 43.27 | 95 | 107 |

- **Floor:** the recurrent state alone (19.27 MiB/slot) caps this model at about **215 slots (A) or 240 slots (B)** even with near-zero context. So on 6 GB, **the 256 hard cap is never the binding limit for Qwen3.5-2B**. VRAM, dominated by recurrent state at short contexts, is.
- Keep 100 to 200 MiB of headroom below these maxima for the CUDA runtime pool and fragmentation. A realistic target is about 75 slots at q8_0/4,096 (Case A).
- At 1,024 tokens/slot the FA scratch (2 MiB) is about the size of the Gated DeltaNet temporaries (about 2 MiB/seq), so the real compute growth may be slightly higher than the table [INFERRED]. Treat the 1,024 rows as plus or minus 3%.
- `-kvu` with a shared pool smaller than `np x ctx` cuts the KV and FA-scratch terms in proportion to the pool size, but adds about 1 KiB per pool token of mask (at `-ub 512`) and leaves the 19.27 MiB/slot RS term unchanged.
- MTP/EAGLE speculative decoding multiplies the RS term by `(1 + draft_n_max)` and adds a draft context. Avoid it if you want many slots.

---

## Sources (accessed 2026-10-18)
- llama.cpp b11718 source: `src/llama-cparams.h`, `src/llama-cparams.cpp`, `src/llama-context.cpp`, `src/llama-model.cpp`, `src/llama-memory-recurrent.cpp`, `src/llama-memory-hybrid.cpp`, `src/llama-kv-cache.cpp`, `src/llama-hparams.cpp`, `src/llama-graph.cpp`, `src/models/qwen35.cpp`, `common/common.{h,cpp}`, `common/arg.cpp`, `common/speculative.cpp`, `tools/server/{server.cpp,server-context.cpp,server-task.h,README.md}`, `ggml/src/ggml-cuda/{fattn.cu,fattn-common.cuh}`, `conversion/qwen.py`. https://github.com/ggml-org/llama.cpp/tree/b11718
- Qwen3.5-2B config.json: https://huggingface.co/Qwen/Qwen3.5-2B/blob/main/config.json
- GGUF sizes: https://huggingface.co/unsloth/Qwen3.5-2B-GGUF
- PR #15916 "llama : bump max seq limit from 64 to 256" (merged 2025-09-18): https://github.com/ggml-org/llama.cpp/pull/15916
- PR #14188 (LLAMA_MAX_PARALLEL_SEQUENCES renamed to LLAMA_MAX_SEQ): https://github.com/ggml-org/llama.cpp/pull/14188
- PR #14363 "llama : add high-throughput mode" (kv_unified, merged 2025-07-16): https://github.com/ggml-org/llama.cpp/pull/14363
- PR #16736 "server : support unified cache across slots" (merged 2025-11-02): https://github.com/ggml-org/llama.cpp/pull/16736
- PR #16391 "server : host-memory prompt caching" (2025-10-09): https://github.com/ggml-org/llama.cpp/pull/16391
- PR #15293 "server : add SWA checkpoints" (merged 2025-08-14): https://github.com/ggml-org/llama.cpp/pull/15293
- PR #16382 "implement context checkpointing for hybrid and recurrent models" (merged 2025-10-03): https://github.com/ggml-org/llama.cpp/pull/16382
- Issue #17989 (auto np=4 + kvu surprises): https://github.com/ggml-org/llama.cpp/issues/17989

## Summary
- Hard cap: `LLAMA_MAX_SEQ = 256` at b11718. Beyond it, context creation throws `n_seq_max must be <= 256` and the server fails to load.
- Per slot for Qwen3.5-2B: KV is 6.375 KiB/token (q8_0) or 3.375 KiB/token (q4_0), over 6 layers. Recurrent state is a fixed **19.27 MiB per slot**, F32, independent of context. With quantized KV on CUDA/Ampere, the compute buffer also adds about **2 KiB/token** of f16 FA scratch.
- That gives a predicted 52.77 MiB/slot at q8_0/4,096 tokens, against 52.3 MiB measured (within 1%).
- In about 5,800 MiB total with ~495 MiB of other apps open: about 78 slots at q8_0/4k, 115 at q8_0/2k, 149 at q8_0/1k; 101 at q4_0/4k, 138 at q4_0/2k, 168 at q4_0/1k. The recurrent state alone limits the model to about 215 slots.
- `-ctxcp` checkpoints (about 19.3 MiB each) and `-cram` live in system RAM. `-kvu` shares only the KV pool, not the recurrent state, and adds a pool-sized mask to the compute buffer.

## Gaps
- Not run on hardware: the exact `-np 257` console output, the per-buffer log lines, and the 1,024-token rows.
- Compute-buffer growth per slot (FA scratch vs Gated DeltaNet temporaries vs logits overlap) is inferred from the allocator logic, not read from a log. Confirm with the `compute buffer size` line at several `-np` values.
- Why the fixed base (~1,160 MiB) is below the GGUF size is not verified.
- The Windows/WDDM usable-VRAM ceiling (assumed ~5,800 MiB) is not verified.
