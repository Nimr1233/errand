# Automatic prompt and harness optimization for small (1-4B) models with small eval sets (state as of Oct 2026)

Context: Errand's harness is the page view, system prompt, JSON-schema answer form, few-shot examples, "snap" rules, recipes and sampling settings around 53 parallel Qwen3.5-2B (Q4_K_M, 4k ctx) brains. The planned tuner searches a fixed knob menu in code, scores variants on ground-truth sets (40 pages, 4 sites, 190 answers; a click set to come), keeps the best per site/template, stores lessons, and asks Claude Code for new ideas only when search stalls. The owner's 39% to 96% jump from changing the answer format comes from the owner, not from a published source.

Source-quality notes: arXiv papers and official repos/docs are primary. Two papers are very new and unreviewed: Harness² (9 Oct 2026) and "Explore More, Validate Less" (19 Oct 2026). Dates are given so older results can be told apart. No published study measures GEPA/MIPRO/ACE with a 2B task model on web extraction. The closest evidence is a Jul 2026 query-routing study that includes Qwen3.5-2B and 0.8B.

## 1. DSPy optimizers (BootstrapFewShot, MIPROv2, SIMBA, GEPA) and standalone GEPA: gains, rollouts, small students with strong proposers

### Takeaway
GEPA is the strongest published prompt optimizer at 8B scale. On Qwen3-8B it beats MIPROv2 and GRPO with about 1.8k-7k rollouts, and its Pareto selection is worth about 6 points over greedy. The only study with Qwen3.5-2B found that neither GEPA nor few-shot beat a good hand-written prompt, even with a GPT-5.4 reflector. Errand's tuner must treat the current hand harness as the bar to beat and accept a change only after a held-out check.

### Cited Findings
**GEPA paper (arXiv 2507.19457; v1 Jul 2025, ICLR 2026 oral)**
- Method: sample trajectories, have a reflection LM diagnose them in natural language, propose a new instruction, test it on a minibatch (size 3), and if it improves, score it on a validation set ("D_pareto"). Parents are drawn from a Pareto frontier of candidates that each win on some validation items. — [GEPA paper](https://arxiv.org/html/2507.19457); [DSPy GEPA docs](https://dspy.ai/current/api/optimizers/GEPA/overview/)
- Qwen3-8B, all modules on the same model (baseline / MIPROv2 / GEPA / GRPO): HotpotQA 42.33/55.33/62.33/43.33; IFBench 36.90/36.22/38.61/35.88; HoVer 35.33/47.33/52.33/38.67; PUPA 80.82/81.55/91.85/86.66; AIME-2025 27.33/20.00/32.00/38.00; LiveBench-Math 48.70/46.60/51.95/51.26. **Aggregate 45.23/47.84/54.85/48.91.** GRPO wins only AIME. — [GEPA paper](https://arxiv.org/html/2507.19457)
- Rollout budgets: GEPA (+Merge) used HotpotQA 6,871, IFBench 3,593, HoVer 7,051, PUPA 2,426, AIME 1,839, LiveBench 1,839. GRPO used 24,000 everywhere. MIPROv2 ran `auto=heavy` (18 instruction candidates, 18 bootstrapped demo sets, TPE search) with 2,270 (PUPA) to 6,926 (HoVer) rollouts, and GEPA's budget was capped to match MIPROv2 within about 10-15%. — [GEPA paper](https://arxiv.org/html/2507.19457)
- Most of GEPA's budget goes to validation, not learning. Rollouts to match GRPO's best validation score were 243-1,179 in total, and some tasks needed only 6-179 train rollouts. IFBench reached 38.61% after 678 rollouts versus GRPO's 35.88% after 24,000. The authors list "smaller or dynamic validation subsets" as future work. — [GEPA paper](https://arxiv.org/html/2507.19457)
- Dataset sizes (train/val/test): HotpotQA, HoVer and IFBench 150/300/~300; PUPA 111/111/221; AIME 45/45/30. These are close to Errand's 190 answers. — [GEPA paper](https://arxiv.org/html/2507.19457)
- Selection ablation (Qwen3-8B, 4 tasks, baseline 48.84): greedy best-candidate 54.89 (+6.05), beam N=4 53.95 (+5.11), **Pareto 61.28 (+12.44)**. — [GEPA paper](https://arxiv.org/html/2507.19457)
- Merge (crossover) is unreliable on the small model. On Qwen3-8B, GEPA+Merge vs GEPA: HotpotQA +2.00, IFBench −10.38 (below baseline), HoVer −0.66, PUPA −5.59, aggregate 52.40 vs 54.85. On GPT-4.1 mini it gained +1.14. — [GEPA paper](https://arxiv.org/html/2507.19457)
- GEPA prompts were "up to 9.2× shorter" than MIPROv2's, which matters under a 4k context. — [GEPA paper](https://arxiv.org/html/2507.19457)
- The text I could read does not say which reflection LM was used for the Qwen3-8B runs. It says each system used the same model for all modules. — [GEPA paper](https://arxiv.org/html/2507.19457)
- The textual feedback function is the main learning signal, for example which constraints failed or which gold documents are still missing. Without feedback, DSPy falls back to "This trajectory got a score of {score}". — [GEPA paper](https://arxiv.org/html/2507.19457); [DSPy GEPA docs](https://dspy.ai/current/api/optimizers/GEPA/overview/)
- The DSPy GEPA metric can return `objective_scores` with `frontier_type` = instance/objective/hybrid/cartesian, but the scalar score still decides acceptance. `track_stats=True` logs candidates, parents and metric-call counts. — [DSPy GEPA docs](https://dspy.ai/current/api/optimizers/GEPA/overview/)
- The standalone `gepa` repo's `optimize_anything` optimizes any text artifact (prompts, code, configs, agent architectures) given a seed, an evaluator and an objective. Evaluators can log diagnostics with `oa.log()` that feed into reflection. Examples use `max_metric_calls` of 100-150 and `reflection_lm="openai/gpt-5"`. The README claims 100-500 evaluations versus 5,000-25,000+ for GRPO, and that it works with "as few as 3 examples". These are repo claims. — [gepa-ai/gepa](https://github.com/gepa-ai/gepa)

**Small-model evidence (strong reflector, small student)**
- Guarded query routing study (arXiv 2607.24801, Jul 2026). GEPA "light" preset with 100 train and 30 val samples and **gpt-5.4 as reflection model**, initialized from the few-shot prompt. GQR-Score (standard / bare DSPy / few-shot / GEPA): **Qwen3.5-2B 90.58 / 80.64 / 70.43 / 81.61**; Qwen3.5-0.8B 60.35 / 20.17 / 67.79 / 48.92; Qwen3.5-4B 92.97 / 92.51 / 92.51 / 91.72; Qwen3.5-9B 94.55 / 93.56 / 95.74 / 95.58; Mistral-7B 81.79 / 77.99 / 90.87 / 82.94. GEPA was not best for any of the 7 models. The hand-written standard prompt was best for Qwen3.5-4B and 2B. — [Guarded routing study](https://arxiv.org/html/2607.24801)
- In that study, optimization mostly repaired in-distribution label choice, for example Granite 4 Tiny ID accuracy 37.29% to 94.88%. Exemplars over-corrected Qwen3.5-2B, whose OOD accuracy fell to 56.40%. The authors suggest LoRA where format-following is the bottleneck but did not test it. — [Guarded routing study](https://arxiv.org/html/2607.24801)
- Infrastructure-as-code study (arXiv 2607.20478, 2026; Qwen2.5-Coder 7B, 186 tasks): GEPA 53.2% pass@1, SIMBA 45.2%, RAG baseline 45.7%; GEPA vs SIMBA p=0.059. One task and one model. — [Search summary of arXiv 2607.20478](https://arxiv.org/pdf/2607.20478)
- "Explore More, Validate Less" (arXiv 2610.27367, 19 Oct 2026; Qwen3.5-9B and Llama-3.1-8B): build a pool of up to 100 candidates using only train-minibatch feedback (minibatch size 3, up to 5 parents per batch), then spend a fixed 20 full validations choosing among them. Random or MLP-guided choice beat a GEPA variant in 8 and 9 of 10 comparisons, and beat MIPROv2 on every Qwen benchmark. Best gain: HotpotQA on Qwen 40.67 to 51.89. Three seeds, no significance claimed. The GEPA baseline is the authors' variant. — [Explore More, Validate Less](https://arxiv.org/html/2610.27367)

**MIPROv2, BootstrapFewShot, SIMBA**
- MIPRO (arXiv 2406.11695, Jun 2024, EMNLP 2024): jointly proposes instructions (data- and program-aware) and bootstrapped demos, fits a surrogate on minibatch scores, and beats baselines on 5 of 7 programs with **Llama3-8B**, by up to 13% accuracy. — [MIPRO paper](https://arxiv.org/abs/2406.11695v1)
- SIMBA: samples minibatches, finds hard examples with high output variability, then writes self-reflective rules or adds successful examples as demos. Defaults: batch size 32, 8 max steps. — [DSPy SIMBA docs](https://dspy.ai/api/optimizers/SIMBA/)
- Tabular fact verification (arXiv 2602.17937, Feb 2026): COPRO, MIPROv2 and SIMBA all improved accuracy. MIPROv2 gave the most stable gains for CoT, and CoT worked best with smaller models. SIMBA helped ReAct most at larger scales. The abstract gives no numbers. — [arXiv 2602.17937](https://arxiv.org/abs/2602.17937)
- In ACE's comparison (DeepSeek-V3.1), offline GEPA added +4.0 on AppWorld and +3.4 on finance, and MIPROv2 added +1.8 on finance. Both are far below ACE (see section 3). — [ACE paper](https://arxiv.org/html/2510.04618)

### Inferences
- The one sub-4B data point is negative. With Qwen3.5-2B, a frontier reflector, 100 train and 30 val samples, GEPA landed 9 points below the hand prompt, and few-shot landed 20 below. A plausible cause is the small-validation trap: 30 validation items cannot separate candidates reliably. Errand's tuner should never auto-adopt a variant without a held-out split that the search did not use.
- GEPA's real budget driver is full validation. With 190 answers, one full validation is one 40-page run. The 2610.27367 recipe fits Errand's cost profile: generate many variants cheaply on 3-5 page minibatches, then fully validate only about 20.
- Strong-model call count (my estimate from the algorithm): GEPA makes about one reflection call per iteration, and an iteration costs about 2×minibatch rollouts plus a full validation when the minibatch improves. A 300-500 metric-call budget therefore means about 30-80 reflection calls. That is too many for a limited Claude Code subscription if every reflection goes to Claude. Run reflection on a cheaper or local proposer and escalate to Claude only on stalls. MIPROv2 needs fewer proposer calls (about 18 instruction proposals plus demo bootstrapping) but more task-model rollouts.
- Do not enable GEPA Merge for small students. It hurt Qwen3-8B on 3 of 4 tasks.
- Errand's grader can produce rich text feedback for free: which field was wrong, the gold string, whether the right piece was pointed at but snapped wrong. GEPA's evidence says this feedback, not the scalar score, drives its sample efficiency.

### Gaps
- Which reflection LM GEPA used for Qwen3-8B (in appendices I did not fully read).
- No published GEPA, MIPROv2 or SIMBA results for 1-4B task models on extraction or web tasks. The routing study is classification.
- Original SIMBA benchmark numbers were not found.
- The DSPy `auto` light/medium/heavy budgets in metric calls were not found on the current docs page.

## 2. OPRO, APE, ProTeGi/TextGrad, PromptBreeder, EvoPrompt: results and sample efficiency vs GEPA/MIPRO

### Takeaway
These first-generation search methods are the weakest choice for Errand. When the small model is its own optimizer, they lower accuracy. On GPT-class models they score about the same as each other. They need many LLM calls and produce long prompts that a 4k-context 2B model cannot afford. Their useful parts are already inside GEPA and MIPRO: candidate pools (APE), score-conditioned proposals (OPRO) and critique-then-edit (ProTeGi).

### Cited Findings
- POaaS (FEVER workshop, Mar 2026). On **Llama-3.2-3B-Instruct**, with the same 3B model as optimizer and task model, average accuracy over BBH/GSM8K/CSQA was: no optimization 63.7, **EvoPrompt 59.8** (20 generations), **OPRO 57.5** (10 iterations), **PromptWizard 48.8** (BBH 42.2 to 10.4). On Llama-3.1-8B: no-opt 70.1, EvoPrompt 66.1, OPRO 63.5, PromptWizard 54.9. All three also lowered factuality. — [POaaS paper](https://aclanthology.org/2026.fever-1.2.pdf)
- POaaS's account of the failure: the APO baselines made "hundreds of internal LLM calls", had no length cap, and produced instructions that add "thousands of extra prompt tokens". Long, structured prompts raise verbosity and hallucination risk in small models. POaaS's minimal-edit approach (strict drift and length caps, skip well-formed prompts) gained +2.3 on 3B and +1.4 on 8B. — [POaaS paper](https://aclanthology.org/2026.fever-1.2.pdf)
- POaaS ran every optimizer call on the same small model on purpose, so it does not test the strong-proposer setup Errand plans. — [POaaS paper](https://aclanthology.org/2026.fever-1.2.pdf)
- On GPT-3.5-Turbo and GPT-4o-mini, APE, OPRO and EvoPrompt averaged about 0.76-0.77 across five tasks in a 2026 segment-level APO paper. They are hard to tell apart on capable models. — [Segment-level APO (arXiv 2608.11219), via search summary](https://arxiv.org/html/2608.11219v1)
- EvoPrompt needs many LLM calls and depends on a good task-specific starting population. OPRO repeatedly generates and evaluates over full datasets. — [CAPO paper (arXiv 2504.16005), via search summary](https://arxiv.org/pdf/2504.16005)
- Mechanics: APE generates a candidate pool and selects by score. ProTeGi uses LLM feedback as "pseudo-gradients" with beam search. PromptBreeder evolves both task prompts and mutation prompts. — [Survey, arXiv 2502.11560](https://arxiv.org/html/2502.11560v1)
- In the GEPA paper, MIPROv2 (TPE over instructions and demos) gained only +2.61 aggregate on Qwen3-8B, against +9.62 for GEPA. — [GEPA paper](https://arxiv.org/html/2507.19457)

### Inferences
- The "small model proposes its own prompt" setup is clearly harmful. Errand's brains should never write their own harness edits. Proposals should come from code (the knob menu) or from a stronger model.
- Any free-text instruction proposal must pass a hard token cap in the tuner (for example, system prompt plus demos within a fixed share of the 4k window). Without one, search drifts to long prompts, as POaaS observed.

### Gaps
- No head-to-head study of sample efficiency for all six methods on small models was found.
- TextGrad and PromptBreeder have no small-model numbers in the sources I read. I did not retrieve TextGrad results, so it is unassessed here.

## 3. Context/playbook methods: ACE, Dynamic Cheatsheet, Harness²

### Takeaway
ACE and Harness² beat prompt-only optimizers on agent tasks by storing many small, evidence-backed lessons and editing them incrementally instead of rewriting. ACE's best design rules are itemized bullets with IDs and helpful/harmful counters, delta updates and embedding de-dup. Harness² adds a library of whole harnesses, each with an EXPERIENCE.md, behind an index. Every published result uses large executors and strong editors (DeepSeek-V3.1, Gemini 3.5 Flash, GLM-5, Claude Opus 4.8). Without reliable feedback, gains shrink or reverse. Errand has exact ground truth, which removes ACE's biggest risk, but its 4k context means lessons should guide the tuner and the proposer, not be pasted into the brain's prompt.

### Cited Findings
**ACE (arXiv 2510.04618, Oct 2025, ICLR 2026)**
- Roles: a Generator produces trajectories and marks which playbook bullets helped or misled. A Reflector extracts lessons, optionally over several rounds. A Curator writes compact "delta" entries that non-LLM code merges in. All three used **DeepSeek-V3.1** (non-thinking). — [ACE paper](https://arxiv.org/html/2510.04618)
- Playbook format: itemized bullets, each with a unique ID, helpful/harmful counters, and content (a strategy, concept or failure mode). "Grow-and-refine" appends new bullets, updates old ones in place, and de-duplicates by semantic embedding, either after each delta or lazily when the context overflows. — [ACE paper](https://arxiv.org/html/2510.04618)
- **Context collapse:** in one AppWorld case, a full LLM rewrite shrank the context from 18,282 tokens (accuracy 66.7) to 122 tokens (accuracy 57.1), below the 63.7 baseline. **Brevity bias:** optimizers drift to short, generic instructions and drop domain detail. — [ACE paper](https://arxiv.org/html/2510.04618)
- AppWorld (base 42.4): ICL +3.6, GEPA +4.0, Dynamic Cheatsheet online without labels +9.5, **ACE offline with labels +17.0**, ACE offline without labels +14.8, ACE online without labels +17.1. Finance (base 69.1): MIPROv2 +1.8, GEPA +3.4, **ACE offline with labels +12.8**, ACE offline without labels +8.0, DC online without labels −3.7. — [ACE paper](https://arxiv.org/html/2510.04618)
- Cost: on AppWorld, offline ACE needed 357 rollouts vs GEPA's 1,434 (−75.1%), and latency fell from 53,898 s to 9,517 s. Average latency reduction was 86.9%. — [ACE paper](https://arxiv.org/html/2510.04618)
- Limits: ACE depends on a reasonably strong Reflector. Without reliable feedback it can fall below base (online ACE without labels on FiNER 67.3 vs 70.7). Tasks that need only short instructions (HotPotQA, Game of 24) gain little. — [ACE paper](https://arxiv.org/html/2510.04618)
- Reflector strength on FiNER: a GPT-OSS-120B reflector reached 76.6 vs a 70.7 base, and GPT-5.1 reached 78.5. Injected harmful reflections degrade accuracy gradually, and it stays above base at moderate noise. — [ACE paper PDF, via search summary](https://arxiv.org/pdf/2510.04618)

**Dynamic Cheatsheet (arXiv 2504.07952, Apr 2025, EACL 2026)**
- A persistent, self-curated memory of short, transferable strategies and code snippets reused at inference time, with no weight updates. GPT-4o on Game of 24 went from about 10% to 99%. Claude 3.5 Sonnet's AIME accuracy more than doubled. Claude gained +9% on GPQA-Diamond. All results use frontier models, and no small-model results were found. — [Dynamic Cheatsheet](https://arxiv.org/html/2504.07952v1)

**Harness² (google-research/harness2; arXiv 2610.14224, 9 Oct 2026)**
- Task-level step, Propose-Probe-Compose: (1) run the current harness once as a reference; (2) an editor proposes two candidates from the harness's component files, one *invariant* edit (planning, tool use, context management) and one *domain* edit; (3) probe each candidate on the same task under matched settings and compare trajectories and outputs to the reference ("behavioral contrast": fixed / unchanged / regressed); (4) a composer merges supported changes, adopts one candidate, or keeps the current harness. **No ground truth is used during refinement.** Contrasts "inform composition rather than verify correctness". — [Harness² paper](https://arxiv.org/html/2610.14224v1); [repo README](https://github.com/google-research/harness2)
- Improvement harness, the lesson store: a library where each entry holds an executable harness plus an **EXPERIENCE.md** (when it applies, lessons, supporting evidence), with an index that later sessions query on demand. A lesson is added only when execution contrasts support it. The library starts empty per benchmark stream and is updated after each task. Reuse is "selective adaptation, not inheritance" during Propose. — [Harness² paper](https://arxiv.org/html/2610.14224v1)
- Models: executors Gemini 3.5 Flash and GLM-5 under OpenCode or Codex. The editor/selector was **Claude Opus 4.8 at high reasoning effort**. In a same-model setting, five models from GLM-5 to Claude Opus 5 each acted as both executor and editor, and all improved. — [Harness² paper](https://arxiv.org/html/2610.14224v1)
- k=1 gains over the base harness: WorkBuddy-Bench +3.0 to +11.5; JobBench +1.2 to +4.5; LAB partial +2.0 to +11.8. The weaker executor (GLM-5) gained most. Parallel k=5 added another +2.9 to +6.7 over k=1 (Code 76.5 to 80.8, Office 79.5 to 83.4). — [Harness² paper](https://arxiv.org/html/2610.14224v1)
- Ablations (Gemini, k=1): without the library −3.1 / −1.8; without scoping −2.9 / −3.7; without composition −1.6 / −1.9. Refining with no references, probes or library dropped Code from 73.4 to 63.2 and Web from 69.9 to 65.0. Naive self-editing hurts. — [Harness² paper](https://arxiv.org/html/2610.14224v1)
- Library quality matters: a library built at k=1 only restored base performance, while one built at k=5 gave +0.9 to +5.1. Cross-benchmark transfer (JobBench library used on WorkBuddy) was small: +0.5 to +2.9. — [Harness² paper](https://arxiv.org/html/2610.14224v1)
- $0 flags: model-backed runs need Vertex AI ("incur API costs"). Codex runs with its sandbox disabled, executor network access is unrestricted, and benchmark rubrics may be online, so answers can leak. The local `harness2-demo` needs no credentials. "Not an officially supported Google product." — [repo README](https://github.com/google-research/harness2)

### Inferences
- Errand already has what Harness² lacks: an exact grader. Probe-and-compose can be replaced by "probe and score". A candidate harness is kept only if it beats the reference on the same pages, which is a stronger check than behavioral contrast.
- Lesson store design to copy: one entry per site/template holding the winning harness config (knob values), plus a short EXPERIENCE file (situation, lesson, evidence = score deltas and run IDs), plus an index. Lessons are added only with measured evidence and edited as deltas with helpful/harmful counts. The store is never fully rewritten, to avoid ACE's context collapse.
- Per-call strong-model cost (estimated from the method descriptions): one Harness² k=1 step is about 2 proposals + 1 composition + 1 reflector update, so about 4 strong-model calls per task. ACE needs Reflector + Curator calls per training sample per epoch. Both are too expensive to call on every page with a limited subscription, which fits the owner's "Claude only when search stalls" plan.
- A 4k-context 2B brain cannot hold an ACE-style playbook of thousands of tokens. ACE also notes that tasks needing short instructions gain little. Lessons should mostly live on the tuner side (which knob to try next, what failed on which template). Only the few bullets that measurably help should go into a brain's prompt, each A/B-tested as a knob.

### Gaps
- No ACE, DC or Harness² results with 1-4B executors.
- Harness² per-step call counts and token costs (in its Figure 6) and its failure-mode appendix were not readable in the fetched text.
- Whether a GPT-OSS-120B-class open reflector, which ACE showed still helps, is affordable at $0 was not researched.

## 4. Few-shot example selection as a knob: retrieved same-site examples vs fixed demos

### Takeaway
Retrieved, similar examples usually beat fixed demos (Synapse, AWM, Dr.ICL), and web-agent memories of past solved tasks give large relative gains. For Qwen3.5-2B, though, demos can overcorrect. In the routing study, few-shot lowered Qwen3.5-2B from 90.58 to 70.43. The number, choice and presence of demos should be searched knobs, scored per site, with "zero demos" always in the menu.

### Cited Findings
- Synapse (arXiv 2306.07863, Jun 2023, ICLR 2024): state abstraction plus full trajectories as exemplars plus an exemplar memory retrieved by embedding similarity. MiniWoB++ 99.2% average success over 64 tasks. Mind2Web step success rate +56% relative over the previous best prompting scheme. Retrieval from memory improved on static exemplars. — [Synapse](https://arxiv.org/abs/2306.07863); [Synapse PDF, via search summary](https://arxiv.org/pdf/2306.07863)
- Agent Workflow Memory (arXiv 2409.07429, Sep 2024, ICML 2025): induces reusable workflows from solved tasks, either offline from annotations or online from evaluator-approved predictions. **+24.6% relative on Mind2Web, +51.1% on WebArena.** Online AWM beat baselines by 8.9-14.0 absolute points as the train-test gap widened (cross-task, cross-website, cross-domain). — [AWM, ICML 2025](https://proceedings.mlr.press/v267/wang25bx.html); [AWM abstract](https://arxiv.org/abs/2409.07429v1)
- Dr.ICL: even simple BM25 retrieval of demos beats random demos. — [Dr.ICL](https://deepai.org/publication/dr-icl-demonstration-retrieved-in-context-learning)
- Whether similarity or diversity is the better selection criterion depends on the task. — [Survey on data selection, arXiv 2402.16827](https://arxiv.org/pdf/2402.16827)
- TRIPLE (arXiv 2402.09723, Feb 2024) treats demo selection as a bandit problem. With 50 candidate examples, budget 100 and 4 shots on GPT-3.5, average ranks were CSAR 1.33, SAR 2.08, uniform 2.83, random 3.75. — [TRIPLE](https://arxiv.org/html/2402.09723v3)
- Small-model caution: in the routing study, BootstrapFewShotWithRandomSearch (6 demos, 4 candidate programs, 30 training samples) was best for 4 of 7 models. It raised Granite 4 Tiny ID accuracy from 37.29% to 94.88% and Mistral-7B from 81.79 to 90.87. It cut Qwen3.5-2B from 90.58 to 70.43, with OOD accuracy down to 56.40%. — [Guarded routing study](https://arxiv.org/html/2607.24801)
- MIPRO's joint search over instructions and bootstrapped demos gave up to +13% on Llama3-8B. — [MIPRO paper](https://arxiv.org/abs/2406.11695v1)

### Inferences
- Errand's same-site solved pages are close to AWM's online setting and Synapse's memory. A "k nearest solved pages from the same template" knob is likely to help pages that resemble training pages. Gains should be measured per template, because the 2B routing result shows demos can bias a small model's outputs.
- Under 4k context, a demo costs about as much as the page view. Cheap variants to try: one demo, demos holding only the answer JSON (no page), and a compressed page plus answer.
- Use code-built demos from ground-truth pages, not demos written by the brain.

### Gaps
- No measured result isolates same-website vs cross-website exemplar retrieval for 1-4B models. Synapse's per-split static vs retrieved numbers were not in the abstract I fetched.

## 5. Search strategies over a discrete knob menu with an expensive evaluator

### Takeaway
For a small categorical menu scored on about 40 pages, the evidence favors simple methods. Random search plus a few-step greedy search on the highest-impact knob first matched grid-search optima in about 10 trials, and TPE did no better than random in that study. Successive halving and racing (TRIPLE-SH/CR) beat uniform allocation by about 15% at low budgets, and the gap closes by about 30 evaluations per candidate. For text candidates, Pareto/per-item frontier selection beats greedy by about 6 points.

### Cited Findings
- RAG hyperparameter study (arXiv 2505.03452, May 2025): a 162-config space (chunk size, overlap, embedder, top-k, generator LLM). TPE (5 random starts), random search and three greedy orders, each run for 10 iterations × 10 seeds. About 10 iterations matched the grid-search best. **TPE performed about the same as random.** Greedy with the model knob first reached a top config in as few as 3 iterations. Gains were up to 20% over an arbitrary config. The generator model was the most important knob. Recommendations: quick random exploration, then greedy on the most important knob first, with dev-set subsampling (10% of the data was about 10× cheaper, with negligible effect on one dataset). — [RAG HPO analysis](https://arxiv.org/html/2505.03452v3)
- TRIPLE (arXiv 2402.09723, Feb 2024; GPT-3.5, Llama2-7B, Gemma-7B, Mistral-7B). With 30 prompts and budget 150 (about 5 evaluations per prompt), Sequential Halving and Continuously Reject beat uniform allocation by about 15% and UCB by 3-7%. Embedding-based CLST/GSE beat BO-EI by 10-56% and NeuralUCB by 17-27%. At 30 evaluations per prompt, all methods tied. When there are more candidates than budget, only embedding-based methods apply. — [TRIPLE](https://arxiv.org/html/2402.09723v3)
- Optuna: TPE is the default sampler. It fits densities to good and bad trials, uses 10 startup trials by default, and offers `multivariate` and `categorical_distance_func` options for categorical spaces. GPSampler (Matern-2.5 GP with per-parameter ARD) also starts with 10 trials. A third-party guide recommends GPSampler for expensive evaluations and GridSampler for small discrete spaces. — [Optuna TPESampler docs](https://optuna.readthedocs.io/en/v4.8.0/reference/samplers/generated/optuna.samplers.TPESampler.html); [Optuna GPSampler docs](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.GPSampler.html); [Hyperactive guide, via search summary](https://github.com/hyperactive-project/Hyperactive/pull/155/files)
- MIPROv2 uses TPE over instruction × demo combinations, scored on minibatches. — [GEPA paper, MIPROv2 setup](https://arxiv.org/html/2507.19457); [MIPRO paper](https://arxiv.org/abs/2406.11695v1)
- GEPA's Pareto (per-validation-item) parent sampling beat greedy best-candidate by about 6.4 points and beam search by about 7.3 on Qwen3-8B. Keeping candidates that win on some items preserves diversity. — [GEPA paper](https://arxiv.org/html/2507.19457)
- Screening on train minibatches, then a capped number of full validations (20 out of a pool of 100), beat full-validation-heavy GEPA in 8-9 of 10 comparisons, with lower runtime in 8 of 10. — [Explore More, Validate Less](https://arxiv.org/html/2610.27367)
- DSPy GEPA supports multi-objective frontiers (`frontier_type="objective"/"hybrid"`) but gates acceptance on one scalar. — [DSPy GEPA docs](https://dspy.ai/current/api/optimizers/GEPA/overview/)

### Inferences
- Suggested tuner loop: (a) one-at-a-time sweep of each knob around the current best (cheap greedy, highest-impact knobs first: page-view format, answer form, demos); (b) a small random or TPE batch over the combination of the top 2-3 knobs; (c) successive halving on 5 pages, then 10, then 20, then all 40 to prune; (d) a final paired comparison of the top few on the full set plus a held-out split; (e) escalate to Claude for new knob values only when (b) and (c) stop improving.
- Noise floor (my calculation): at 90% accuracy on 190 answers, the binomial 95% CI is about ±4.3 points. Answers cluster by page and site, so the effective sample is smaller. Compare variants paired on the same answers (for example, McNemar-style win/loss counts), and require a margin before switching.
- Lexicographic selection to match "accuracy beats speed": maximize accuracy, then among variants within the noise margin of the best, pick the lowest tokens or latency. This is easier to reason about than a weighted Pareto score. Keep per-site/template winners on a per-item frontier, GEPA-style, so a variant that wins on one template is not thrown away for losing the average.
- Hyperband adds little over plain successive halving here. The only "fidelity" axis is the number of pages, which successive halving already uses.

### Gaps
- No study found compares Hyperband, BOHB or Optuna TPE vs random on LLM harness/prompt knobs beyond the RAG study's TPE ≈ random result.
- No direct study of lexicographic vs Pareto selection for prompt or harness tuning.

## 6. Optimizing the input representation (page view) and output format, not just wording

### Takeaway
Representation and format changes are the largest measured effects in this area. Format swings reach 40-76 points on smaller or older models (FormatSpread, He et al.). Observation and action-space cleanup alone gave AgentOccam +26.6 points (+161%) on WebArena with no examples or new prompting tricks. GEPA-style optimizers have been applied to input representation (DD-GEPA). Format effects correlate weakly across models, so formats must be tuned on Qwen3.5-2B itself, not borrowed from results on large models.

### Cited Findings
- FormatSpread (arXiv 2310.11324, Oct 2023, ICLR 2024): small formatting changes in few-shot prompts swung LLaMA-2-13B accuracy by up to **76 points**. The sensitivity persists with larger models, more shots and instruction tuning. Format performance **correlates only weakly between models**. The authors recommend reporting a range over plausible formats. — [FormatSpread](https://arxiv.org/html/2310.11324v2)
- He et al. (arXiv 2411.10541, Nov 2024): the same content as plain text, Markdown, JSON or YAML moved GPT-3.5-turbo by up to 40% on code translation. GPT-4 was more robust. — [Prompt formatting study](https://arxiv.org/abs/2411.10541)
- "Let Me Speak Freely?" (arXiv 2408.02442, Aug 2024, EMNLP 2024 Industry): strict format constraints (JSON mode) hurt reasoning but can help classification. Key order in structured outputs affects reasoning. Parse errors are not the main cause and can be fixed by corrective prompting. — [Let Me Speak Freely](https://arxiv.org/html/2408.02442v1)
- AgentOccam (arXiv 2410.13825, Oct 2024, ICLR 2025): only refining the observation space (remove redundant elements, restructure content blocks) and the action space (drop non-essential actions) took WebArena to 43.1% with GPT-4-Turbo. That is +9.8 points over the previous best and **+26.6 points (+161%) over similar plain web agents**, with no in-context examples or search. — [AgentOccam](https://arxiv.org/html/2410.13825v1)
- Synapse credits part of its gain to state abstraction, which filters task-irrelevant information from raw page states. — [Synapse](https://arxiv.org/abs/2306.07863)
- DD-GEPA (arXiv 2606.07894, 2026) applied GEPA to both the task instruction and the **utterance representation** (how the input is laid out). The gepa README reports Qwen3-30B DD-GEPA F1 rising from 39.40 to 42.52. — [DD-GEPA](https://arxiv.org/pdf/2606.07894); [gepa-ai/gepa](https://github.com/gepa-ai/gepa)
- GEPA `optimize_anything` treats any text artifact (configs, code, agent architecture) as optimizable, so a page-view template or answer schema can be the optimized parameter. — [gepa-ai/gepa](https://github.com/gepa-ai/gepa)
- The RAG study found the choice of components (generator model, retrieval settings) mattered more than fine-grained values. — [RAG HPO analysis](https://arxiv.org/html/2505.03452v3)

### Inferences
- Errand's own 39% to 96% jump (owner-reported) is in line with FormatSpread and AgentOccam: for a 2B model, the page view and answer form are the highest-value knobs. They should get the most search budget and be searched first in a greedy order.
- Because format effects transfer weakly between models, any idea Claude proposes must be scored on Qwen3.5-2B at the real Q4_K_M quantization and sampling settings before adoption. A swap of model or quantization should re-trigger tuning.
- Answer-form knobs worth listing, based on the evidence: key order (evidence field first vs answer first), JSON grammar enforcement vs prompt-only format with a repair pass, and choose-a-piece-number vs copy-text answers (Errand's "point, don't write" result).

### Gaps
- No study measures page-view representation choices (numbered pieces, labels, attributes) for 1-4B models specifically. AgentOccam and Synapse use GPT-4-class models.
- AgentOccam's per-component ablation numbers (its Table 17) were not retrieved.
