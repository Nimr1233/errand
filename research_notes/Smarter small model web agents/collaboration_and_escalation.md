# Collaboration and escalation for groups of small LLM agents (as of October 2026)

Scope: how groups of small LLM agents (Errand: 53 parallel Qwen3.5-2B brains on llama.cpp, one free Gemini key, $0) can check each other, work together and decide when to ask the human. Results from 2022-2024 are marked [older]. Dates are the paper's first arXiv or venue date.

Context fact: Qwen3.5-2B came out in March 2026 as part of the Qwen3.5 Small series (Apache 2.0, 262k context). It uses a Gated DeltaNet hybrid design with 3 linear-attention layers for every full-attention layer. Artificial Analysis gives the reasoning variant 16 on its Intelligence Index; another comparison page gives 7, so the index versions probably differ — [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models), [llm-stats](https://llm-stats.com/models/qwen3.5-2b). One aggregator reports MMLU-Pro of 55.3 without thinking and 66.5 with thinking. That is third-party data and was not checked against the official model card — [immers.cloud](https://en.immers.cloud/ai/Qwen/qwen3.5-2b).

---

## 1. Debate, mixture-of-agents, self-consistency, USC and "more agents" voting: gains for small models, where gains flatten, and when debate hurts

### Takeaway
For 7-8B models, plain majority voting over independent answers explains almost all of the gain credited to multi-agent debate. Debate rounds often lower accuracy, because small models switch from right answers to wrong ones under peer pressure. Voting gains are largest in the first roughly 5-15 samples and then flatten. On queries where the model's most common answer is wrong, more votes make results worse. Keep agents independent, vote or test, and treat any exchange of messages as risky.

### Cited Findings

**Self-consistency (SC) [older, 2022]**
- SC samples several chain-of-thought paths and takes the most common final answer. Gains over greedy CoT: GSM8K +17.9 points, SVAMP +11.0, AQuA +12.2, StrategyQA +6.4, ARC-challenge +3.9. Main models were PaLM-540B and similar; UL2 was added in v3 — [Wang et al., arXiv 2203.11171](https://arxiv.org/abs/2203.11171).

**Universal Self-Consistency (USC) [older, 2023]**
- USC puts all sampled responses into one prompt and asks the LLM which response is most consistent. On math it matches standard SC without needing answers in the same format. It also improves open-ended tasks where SC cannot run. On code it matches execution-based voting without running the code — [Chen et al., arXiv 2311.17311](https://arxiv.org/abs/2311.17311). This was shown with large models. No source checked here shows a 2B model can reliably judge which of 9-53 concatenated answers is most consistent.

**"More Agents Is All You Need" / Agent Forest [older, Feb 2024]**
- The method is sampling plus voting: query the same model N times and take the majority, or the answer with the highest similarity for open-ended outputs. Performance scales with the number of agents — [Li et al., arXiv 2402.05120](https://arxiv.org/html/2402.05120v2).
- On GSM8K, an ensemble of about 15 Llama2-13B agents roughly reaches single Llama2-70B accuracy. Coverage quotes 59% for the 13B ensemble against 54% for a single 70B — [the-decoder](https://the-decoder.com/more-agents-is-all-you-need-researchers-improve-llms-through-ensemble-of-agents/), [paper](https://arxiv.org/html/2402.05120v2).
- The gain grows with task difficulty up to a point and then falls. The enhancement is orthogonal to other methods such as CoT or debate — [arXiv 2402.05120](https://arxiv.org/html/2402.05120v2). One secondary review says most of the gain comes by about 10 agents. I could not confirm that against the paper — [themoonlight review](https://www.themoonlight.io/review/more-agents-is-all-you-need).

**Voting can get worse with more calls [older, NeurIPS 2024]**
- For Vote and Filter-Vote systems, accuracy can first rise and then fall as LM calls increase. More calls help on easy queries and hurt on hard ones, so a mixed task set has an interior optimum. The authors fit a scaling model from a small sample that predicts the best number of calls — [Chen et al., "Are More LLM Calls All You Need?", arXiv 2403.02419](https://arxiv.org/html/2403.02419v2).

**Original multi-agent debate (Du et al.) [older, 2023; ICML 2024]**
- Setup: gpt-3.5-turbo-0301, 3 agents, 2 rounds. Arithmetic went from 67.0% (single) to 69.0% (majority vote) to 81.8% (debate). GSM8K went from 77.0% to 81.0% to 85.0%. MMLU went from 63.9% (single) to 71.1% (debate). Biographies factuality went from 66.0 to 73.8 — [Du et al., arXiv 2305.14325](https://arxiv.org/html/2305.14325).
- Arithmetic accuracy rose with more agents and with more rounds. Beyond 4 rounds, accuracy stayed about the same as at 4. The authors call debate computationally expensive — [arXiv 2305.14325](https://arxiv.org/html/2305.14325).

**Debate or Vote (Choi, Zhu, Li; NeurIPS 2025): the key small-model evidence**
- Across 7 benchmarks with N=5 agents and T=2/3/5 rounds, majority voting over the agents' first answers, with no debate, accounts for most of the gain. The authors prove that debate makes each agent's belief a martingale, so debate alone does not raise expected correctness — [arXiv 2508.17536](https://arxiv.org/abs/2508.17536), [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2025/file/934252acd87f254d5d4672fbde283bd2-Paper-Conference.pdf).
- Qwen2.5-7B-Instruct averaged over 7 benchmarks: single 72.05%, majority vote 76.91%, vanilla debate 65.5-73.8% depending on topology and rounds. On Arithmetic: single 81.4%, vote 99.0%, debate 43-84%. On GSM8K: single 87.1%, vote 94.0%, debate 72-90% — [arXiv 2508.17536 HTML](https://arxiv.org/html/2508.17536v1).
- Llama3.1-8B-Instruct average: single 62.0%, vote 72.4%, debate 56.7-69.9%. Centralized debate was worst at 56.7-60.9%, and more rounds generally lowered accuracy — [arXiv 2508.17536 HTML](https://arxiv.org/html/2508.17536v1).
- Debate beat voting on a few knowledge benchmarks. For Qwen2.5-7B: MMLU Professional Medicine 80.5-81.6% vs 79.4% for voting, and CommonsenseQA 83.3-85.7% vs 83.0% — [same](https://arxiv.org/html/2508.17536v1).
- Two variants that bias agents toward the earlier majority reached 74.4-76.3% average, which still did not clearly beat plain voting at 76.9%. They are "MAD-Conformist" (keep your answer if it matches last round's majority) and "MAD-Follower" (30% chance of adopting the majority). An oracle that locks in correct answers reached 82-84%, which shows the upper bound needs a correctness signal — [same](https://arxiv.org/html/2508.17536v1).

**Debate failure modes: conformity and error amplification (2025-2026)**
- Debate can lower accuracy over time, even when stronger models outnumber weaker ones. Models move from correct to incorrect answers after seeing peer reasoning, consistent with sycophancy and social conformity — [Wynn, Satija, Hadfield, "Talk Isn't Always Cheap", arXiv 2509.05396 (ICML MAS workshop 2025)](https://arxiv.org/abs/2509.05396).
- SLMJury tested 16 small judges from 0.6B to 14B across 4 families. Multi-agent debate under a Reflect-Critique-Refine protocol lowered accuracy in every configuration tested — [SLMJury, arXiv 2606.07810](https://arxiv.org/abs/2606.07810). A search snippet adds that when agents first disagree, the correct agent is swayed by wrong peer reasoning in 35-40% of cases. That number is not in the abstract and was not verified in the full text — [search summary of arXiv 2606.07810](https://arxiv.org/pdf/2606.07810).
- Free-MAD names conformity as the main way errors spread: correct agents get pulled toward incorrect ones — [arXiv 2509.11035 listing](https://papers.cool/arxiv/2509.11035).
- Two 2026 items, known only from search snippets and not checked in full text: (a) homogeneous debate amplifies errors through sycophancy and consensus collapse, often doing worse than a single model on hard benchmarks — [Bertalanič & Fortuna, CAIS 2026](https://www.caisconf.org/program/2026/papers/decomposing-sycophancy-fragility-consensus-collapse-and-cost-in-homogeneous-mult/); (b) strict conformity is about 29%, and 57-77% of conformity events flip a correct answer to a wrong one — [Hao et al., June 2026, via chatpaper](https://chatpaper.com/chatpaper/paper/289928).

**Mixture-of-Agents (MoA) and Self-MoA (2024-2026)**
- MoA is sensitive to member quality, and mixing different LLMs often lowers average quality. Self-MoA aggregates many samples of one top model instead. It beats mixed MoA by 6.6% on AlpacaEval 2.0 and by 3.8% on average across MMLU, CRUX and MATH. A sequential version aggregates outputs over rounds about as well as aggregating them all at once — [Li, Lin, Xia, Jin, arXiv 2502.00674 (TMLR 2026)](https://arxiv.org/abs/2502.00674). MoA's aggregator is a strong LLM writing a synthesis. A 2B aggregator has no evidence behind it here.

**Early stopping: spend fewer votes**
- Adaptive-Consistency draws samples one at a time and stops once a Dirichlet or Beta criterion says the current leader will very likely stay the majority. Example: 9 of the first 10 samples agree. It cut sample budget by up to 7.9x (3.3x on average) with an average accuracy drop under 0.1% across 17 datasets. A `pip install AdaptiveConsistency` package exists — [Aggarwal et al., EMNLP 2023, arXiv 2305.11860](https://arxiv.org/pdf/2305.11860), [PyPI](https://pypi.org/project/AdaptiveConsistency) [older].
- Early-stopping SC (ESC) samples in small windows and stops when every answer in a window agrees. ConSol (2025) argues these heuristics lack statistical guarantees and uses a sequential probability ratio test instead — [ConSol, arXiv 2503.17587](https://arxiv.org/html/2503.17587v1), [DSC, arXiv 2408.13457](https://arxiv.org/html/2408.13457v3).

### Inferences
- Errand's huddle (3, then 9, then all 53 agents, each proposing a fix independently and testing it on pages) already matches what the evidence supports: independent proposals plus selection by test, with no rounds where agents read each other's arguments. Do not add debate rounds. If agents must see each other's work, show only test results (pass/fail per page), never another agent's reasoning. This avoids the conformity flips seen at 7-8B, which are likely worse at 2B.
- Escalating 3, then 9, then 53 is a hand-built version of Adaptive-Consistency or agreement-based cascading (section 5). Evidence says most voting gains come within about 5-15 samples. A round of all 53 mostly helps through more diverse candidate fixes that a tester can check (coverage, section 2), not through more voting.
- For plain answers with no tester (e.g. "which field is the price?"), the Condorcet logic behind "Are More LLM Calls" says: if the 2B model's most common answer is wrong, more voters lock in the wrong answer. A large but non-unanimous vote among 53 is still no proof of correctness.

### Gaps
- I found no controlled debate-vs-vote study at 1-3B (Qwen3.5-2B class); the smallest controlled models were Qwen2.5-7B and Llama3.1-8B. SLMJury covers 0.6B-14B judges but its per-size debate numbers were not checked.
- The exact point where gains flatten for Agent Forest (about 10-15 agents) comes from figures and secondary summaries, not a verified table.
- USC and MoA aggregation have no evidence at 2B.

---

## 2. Verifiers vs voting: is "generate many, verify by execution" better than majority vote?

### Takeaway
Yes, by a wide margin, whenever an automatic check exists. With an execution-based verifier, coverage (whether any sample is right) keeps rising roughly log-linearly with samples. Majority voting and reward models plateau after about 100 to a few hundred samples. Small models judging other small models is weak, and self-verification at 13B and below is a known bottleneck. For CSS-selector or scraper recipes, running the recipe on saved and held-out pages is the verifier to trust. LLM-judge checks should be at most a tie-breaker.

### Cited Findings
- Large Language Monkeys [older, 2024]: coverage grows roughly log-linearly with samples (an exponentiated power law). On SWE-bench Lite, DeepSeek-Coder-V2-Instruct went from 15.9% solved with 1 sample to 56% with 250 samples when unit tests pick the winner. Without automatic verifiers, majority voting and reward models plateau beyond several hundred samples (about 100 in the intro text) — [Brown et al., arXiv 2407.21787](https://arxiv.org/abs/2407.21787v3).
- Theory (2025): self-consistency needs about Θ(1/Δ²) samples to output the right answer, while best-of-n with a verifier needs about Θ(1/Δ). Δ is the probability gap between the top correct answer and the runner-up — [arXiv 2506.05295](https://export.arxiv.org/pdf/2506.05295).
- CodeT [older, 2022]: the same model writes test cases, then runs every candidate and scores agreement on both tests and outputs. HumanEval pass@1 reached 65.8% with code-davinci-002, +18.8 points over the baseline — [Chen et al., arXiv 2207.10397](https://arxiv.org/abs/2207.10397v2).
- Weaver (NeurIPS 2025) combines many weak verifiers (small judges and reward models) through weak supervision. Weighted combinations clearly beat unweighted ones. Llama 3.3 70B with a Weaver ensemble reached about o3-mini accuracy (86.2% average in the NeurIPS abstract, 87.7% in another listing) — [Weaver, arXiv 2506.18203](https://arxiv.org/abs/2506.18203v2), [Stanford page](https://scalingintelligence.stanford.edu/pubs/weaver).
- Small models (13B and below) self-correct reasoning much better with a strong GPT-4 verifier. A weak self-verifier, where the model decides on its own when to correct, was the stated limitation — [Zhang et al., Findings ACL 2024, arXiv 2404.17140](https://arxiv.org/abs/2404.17140) [older].
- T1 (2025): verification by a tool (code interpreter) let Llama-3.2-1B beat Llama-3.1-8B on MATH under test-time scaling. Prior work had mostly used a larger model as verifier — [arXiv 2504.04718](https://arxiv.org/html/2504.04718v1).
- In Hugging Face's test-time scaling study (Dec 2024; secondary coverage only), a 3B Llama beat the 70B model on hard math by searching with a process reward model. Majority voting plateaued quickly when errors were consistent across generations — [getcoai coverage](https://getcoai.com/news/how-small-language-models-punch-above-their-weight-with-test-time-scaling) [older, secondary].
- Small-model judges (2026): across 16 judges from 0.6B to 14B, no single small judge dominated. The math-to-general accuracy gap ranged from under 10% to nearly 40% by family. Short 10-token verdicts matched or beat long reasoning on math. Phi-4, the best binary judge, fell to rank 9 on MT-Bench — [SLMJury, arXiv 2606.07810](https://arxiv.org/abs/2606.07810).
- Execution-based scraper generation, AutoScraper (EMNLP 2024), is the closest published analogue to Errand's selector huddle. The LLM walks the DOM top-down, steps back on failure, then synthesizes a rule across 3 seed pages. It is scored by "executability" on held-out pages from the same site. On SWDE (80 sites, 32,000 pages), the share of fully correct scrapers was 71.56% for GPT-4-Turbo, 54.84% for GPT-3.5, 46.88% for Mixtral-8x7B, 38.75% for DeepSeek-Coder-33B, and 24.06% for Phi-3-medium (14B). Without cross-page synthesis, GPT-4-Turbo fell to 65.31% and GPT-3.5 to 44.52% — [Huang et al., arXiv 2404.12753](https://arxiv.org/html/2404.12753v2) [older].

### Inferences
- Testing each fix on 5 saved pages is the strongest component of Errand's huddle and is backed by the evidence. Two cheap upgrades follow from it: (1) use some saved pages to generate or choose the fix and others only to verify it (held-out pages), so a fix that fits 5 pages by luck is caught; (2) score by agreement of outputs across candidates (CodeT-style): if several different selectors pull the same values from the held-out pages, trust rises.
- AutoScraper's numbers suggest a 2B model rarely writes a fully correct selector in one shot; a 14B model managed about 24%. So the many-candidates-plus-tester approach is needed, not optional. Coverage with 53 diverse attempts is the lever, and the tester's quality sets the ceiling.
- Use the LLM judge, whether 2B or Gemini, only where no tester exists (e.g. "is this the main product price or a related item?"). Keep its verdict short; SLMJury suggests about 10 tokens is enough.

### Gaps
- I found no published study of selector or recipe repair by voting vs testing at 2B. The AutoScraper numbers start at 14B (Phi-3-medium).
- How many held-out pages are needed for a given false-accept rate was not found. This would need Errand's own logs.

---

## 3. Confidence and escalation: knowing when a small model's answer is unreliable, and setting thresholds

### Takeaway
The best measured signals are those built on sampling and agreement (semantic entropy, how much the samples agree). Next come token log-probability signals (sequence probability, perplexity, and the bottom 10% of token confidence in DeepConf). Asking the model how confident it is was not supported for small models in anything I found. To ask the human as little as possible at a target error rate, conformal prediction or risk control gives a threshold with a statistical guarantee from a small labeled calibration set. KnowNo cut human help by 10-24% at the same success rate.

### Cited Findings
- Semantic entropy (Nature 2024) clusters samples by meaning (bidirectional entailment) and takes the entropy over the clusters. AUROC for detecting confabulations was stable at about 0.78-0.81 across model families — [Farquhar et al., Nature 2024](https://www.nature.com/articles/s41586-024-07421-0) [older]. Semantic entropy probes predict it from hidden states in one pass — [ResearchGate summary](https://www.researchgate.net/publication/381550138_Detecting_hallucinations_in_large_language_models_using_semantic_entropy).
- The LM-Polygraph benchmark (2024) uses mean PRR (higher is better) for uncertainty-based rejection. Semantic entropy 0.23 had the best mean rank (7.58). Monte Carlo sequence entropy 0.21, maximum sequence probability 0.18 and perplexity 0.13 are both single-pass, logprob-only signals — [Vashurin et al., arXiv 2406.15627](https://arxiv.org/pdf/2406.15627) [older]. A breakdown by model size was not checked.
- DeepConf (Meta, ICLR 2026) computes token confidence from top-k log-probs and summarizes it per trace using the lowest 10% of tokens, the tail, or the lowest group. Low-confidence traces are filtered, and confidence-weighted voting runs on the rest. An online mode stops weak traces early. Reported gains, from secondary summaries: up to +5.5 points accuracy (Qwen3-32B, AIME24) and up to 84.7% fewer tokens than plain SC. Bottom-10% and tail confidence separated right from wrong traces better than the mean — [Meta AI](https://ai.meta.com/research/publications/deep-think-with-confidence/), [summary](https://www.themoonlight.io/review/deep-think-with-confidence).
- llama.cpp exposes token probabilities. The native `/completion` endpoint takes `n_probs` and returns `probs` with `prob` / `top_probs`, as plain probabilities rather than log-probs, when `post_sampling_probs` is set. In 2024 the OpenAI-style `logprobs`/`top_logprobs` on `/v1/chat/completions` were reported as not working in llamafile. That report was not re-checked for 2026 builds — [llama.cpp server docs Q&A dataset](https://huggingface.co/datasets/ping98k/llama-cpp-server-doc-qa/viewer/default/train?p=12), [llamafile issue #409](https://redirect.github.com/Mozilla-Ocho/llamafile/issues/409), [old README b1393](https://git.peisongxiao.com/CS348Project/llama.cpp/raw/tag/b1393/examples/server/README.md).
- KnowNo (CoRL 2023) takes the LLM's probabilities over multiple-choice next actions and builds a conformal prediction set. If the set has more than one option, the robot asks the human. It hit user-specified success levels while cutting human help by 10-24% compared with baselines, with up to 24% less help on ambiguous scenarios — [Ren et al., arXiv 2307.01928](https://arxiv.org/html/2307.01928v2), [project page](https://robot-help.github.io/) [older].
- Conformal abstention (DeepMind 2024) has the LLM score agreement among its own samples, then calibrates an abstention threshold with conformal methods, including Learn-then-Test. This bounds the hallucination rate. It abstained much less than log-prob baselines on long answers (Temporal Sequences) and about the same on short ones (TriviaQA). It also calibrates the threshold for "these two answers match" — [Abbasi-Yadkori et al., arXiv 2405.01563](https://arxiv.org/abs/2405.01563v1) [older].
- Static conformal thresholds fail to adapt as task difficulty and data drift. A 2025 paper learns abstention thresholds with RL instead — [arXiv 2502.06884](https://www.arxiv.org/abs/2502.06884).
- How much cheap samples agree measures difficulty. In LLM cascades, prompts tend to give consistent answers on easy questions and divided ones on hard questions — [Yue et al., ICLR 2024, arXiv 2310.03094](https://arxiv.org/pdf/2310.03094) [older].

### Inferences
- A cheap escalation score Errand can compute from what it already runs, roughly in order of evidence strength: (1) whether the fix passes the page tests, and on how many held-out pages; (2) the agreement rate among independent agents' extracted values (agreement-based cascading, section 5); (3) the minimum or bottom-10% token probability of the extracted value tokens from llama.cpp `n_probs`. The value tokens matter here (price digits, selector string), not the whole response.
- A threshold recipe in the KnowNo / Learn-then-Test style: log about 100-300 past decisions where the human gave the true answer. Each record holds the score and whether the agents were right. Pick the lowest threshold where the upper confidence bound on the error rate among auto-accepted answers stays at or below the target (e.g. 2%). Everything below the threshold goes to the human. Recalibrate when a site changes (the drift warning above).
- Hard-coded human gates (send, pay, post, login, CAPTCHA) should stay outside any confidence logic. These are policy, not uncertainty.

### Gaps
- No calibration or AUROC numbers for Qwen3.5-2B or other ≤3B models specifically were found. The LM-Polygraph size breakdown was not checked.
- Whether llama.cpp's OpenAI-compatible endpoint returns `logprobs` in 2026 builds was not verified. The native `n_probs` path is documented.
- Confidence-informed SC (CISC) did not show up in search; its numbers are unverified.
- How well semantic entropy and agreement work for structured outputs (selectors, prices) rather than QA was not found.

---

## 4. Learning from the human's answers so the same question is never asked twice

### Takeaway
The proven simple design is a retrieval memory. Store each human correction keyed by the situation, and retrieve similar past corrections into the prompt (MemPrompt). Better still, turn repeated fixes into reusable workflows or rules (Agent Workflow Memory: +51.1% relative success on WebArena). For web extraction, a learned rule (selector plus validator) is the natural form of memory. Before reuse, check it against stored patterns (wrapper verification).

### Cited Findings
- MemPrompt (EMNLP 2022) keeps a growing memory of cases where the model misread the user, together with the user's clarification. For a new query it retrieves similar past feedback and adds it to the prompt, so the same mistake is not repeated. No retraining is needed. Code: madaan/memprompt — [Madaan et al., arXiv 2201.06009](https://arxiv.org/pdf/2201.06009) [older].
- Agent Workflow Memory (ICML 2025) extracts reusable workflows from past successful runs and adds them to the agent's prompt. Results: +51.1% relative success on WebArena over the best published autonomous method, +7.9% over methods using human-written workflows, and +24.6% relative step-wise success on Mind2Web cross-task. Online AWM generalized across tasks, websites and domains, with gains of 8.9-14.0 absolute points as train-test gaps widened — [Wang et al., arXiv 2409.07429](https://arxiv.org/html/2409.07429v1).
- Wrapper maintenance [older, 1999-2003]: RAPTURE checks whether a wrapper is still correct by comparing its output against expected output statistics. On 27 real sites it clearly beat standard regression testing — [Kushmerick, AAAI 1999](https://mlanthology.org/aaai/1999/kushmerick1999aaai-regression). Follow-up work learned structural patterns of good extractions and found 35 of 37 wrapper changes (precision 0.73, recall 0.95) — [Lerman, Minton, Knoblock, "Wrapper Maintenance", arXiv 1106.4872](https://arxiv.org/pdf/1106.4872).
- Small models self-correct much better when trained on refinements guided by correct solutions — [arXiv 2404.17140](https://arxiv.org/abs/2404.17140). Human answers could become such training data. No fine-tuning budget was assumed here.

### Inferences
- Simple design for Errand ("decision memory"): when a problem goes to the human, store a record of (site domain, page-type fingerprint, field name, problem kind, the human's answer or fix, date). Before any huddle, look up an exact match on domain and field, then a fuzzy match on fingerprint. On a hit, apply the stored fix and test it on saved pages, as any huddle candidate would be tested, before trusting it. When the human answers the same kind of question on two or more sites, ask the human once to approve a general rule (e.g. "price lives in an element with itemprop=price"). Store it as a rule, not as one-off examples.
- Every human answer also becomes a labeled point for the threshold calibration in section 3, so each ask makes later asks rarer.
- Expire or re-check memories when RAPTURE-style output statistics drift. Old answers about a changed layout are a source of silent errors.

### Gaps
- No study was found that measures the reduction in human asks over time from decision memory in web scraping specifically. The AWM and MemPrompt metrics are task success, not ask rate.
- Formal active-learning results for picking which question to ask the human first (e.g. most informative problem) were not searched in depth.

---

## 5. One stronger model (free Gemini) as an occasional judge or tie-breaker

### Takeaway
"Cheap models first, escalate on disagreement" is well proven. In LLM cascades, using the weak model's answer consistency as the signal matched the strong model's accuracy at about 40% of its cost (GPT-3.5 to GPT-4). Agreement-based cascading cut cost 2-25x against other LLM cascades. FrugalGPT reported matching GPT-4 with up to 98% cost reduction. How often Errand would need Gemini depends on how often its 2B agents disagree, which must be measured.

### Cited Findings
- Mixture-of-thought cascades (ICLR 2024): sample from GPT-3.5 with CoT and Program-of-Thought prompts, and send a question to GPT-4 only when the answers disagree. Across 6 reasoning benchmarks this matched full GPT-4 accuracy at about 40% of GPT-4's cost, i.e. about 60% savings. Code: github.com/MurongYue/LLM_MoT_cascade — [Yue et al., arXiv 2310.03094](https://arxiv.org/pdf/2310.03094) [older].
- Agreement-Based Cascading (TMLR 2025): ensembles of increasing size at each tier. If enough models in a tier agree, return the answer; otherwise defer to the next tier. No deferral network needs training. It cut average price per token or request 2-25x against modern LLM cascades for API services, 3x for cloud serving, and up to 14x for edge-to-cloud communication — [Kolawole et al., arXiv 2407.02348](https://arxiv.org/html/2407.02348v4).
- FrugalGPT [older, 2023]: a learned cascade with a scorer that decides whether to accept the cheap answer. It matched the best single LLM (GPT-4) with up to 98% cost reduction, or gained 4% accuracy at equal cost — [Chen, Zaharia, Zou, arXiv 2305.05176](https://arxiv.org/abs/2305.05176).
- Weak judges plus a strong generator: a Weaver ensemble of small judges lifted Llama-3.3-70B to about o3-mini accuracy — [arXiv 2506.18203](https://arxiv.org/abs/2506.18203v2). Strong verifiers (GPT-4) were what made small-model self-correction work — [arXiv 2404.17140](https://arxiv.org/abs/2404.17140).
- When stronger and weaker models debate, the weak can drag the strong down: accuracy falls even when strong models outnumber weak ones — [arXiv 2509.05396](https://arxiv.org/abs/2509.05396). A strong model should therefore judge the candidates, not join the discussion.

### Inferences
- Errand pattern: 2B agents propose candidates, and testing on pages filters them. Gemini is called only when (a) no candidate passes, or two or more candidates pass but give different values on held-out pages, and (b) the problem is not on the always-human list. Gemini gets only the surviving candidates and their test outputs, and is asked to choose one or say none (a short verdict). If Gemini chooses, the pick still has to pass the tests. If Gemini says none, escalate to the human. This uses Gemini as a tie-breaker inside a cascade (MoT, ABC) rather than as a debater.
- Rough budget: the human-ask rate before Gemini equals the share of problems where round 3 fails. Gemini calls are limited to the subset where agents disagree or none pass. Both rates are unknown until logged. Under the MoT cascade, about 40% of queries reached the strong model on reasoning benchmarks. The rate on Errand's mostly routine pages is likely lower, but that is unmeasured.

### Gaps
- No study was found with a 2B-class small-model swarm and a Gemini judge. The cascade evidence uses GPT-3.5/GPT-4 or mid-size open models.
- Free Gemini key rate limits and their October 2026 values are not in scope here, so they were not checked.

---

## 6. Out-of-the-box but proven ideas: invariants, cross-page consistency, schema validators, canary pages

### Takeaway
The cheapest high-value checks are not LLM calls. They are: (1) type and format invariants (price parses as a number with a currency, a date parses, a required field is non-empty); (2) cross-page consistency (a selector that works on all of a site's pages and returns values with stable statistics); (3) known-answer canary pages that run before trusting a recipe. These are old, proven ideas from wrapper verification, and modern scraper agents rely on cross-page synthesis.

### Cited Findings
- Cross-page synthesis is measurably better: building the rule from 3 seed pages raised fully-correct scrapers from 65.31% to 71.56% (GPT-4-Turbo) and from 44.52% to 54.84% (GPT-3.5) on SWDE. AutoScraper also checks that the value its XPath extracts matches the value the LLM recognized — [AutoScraper, arXiv 2404.12753](https://arxiv.org/html/2404.12753v2) [older].
- Output statistics as a health check: RAPTURE compares the features of extracted values (length, character types, counts) against expected distributions and beat regression testing on 27 sites. A learned-pattern verifier caught 35 of 37 real wrapper breaks (recall 0.95, precision 0.73) — [Kushmerick 1999](https://mlanthology.org/aaai/1999/kushmerick1999aaai-regression), [arXiv 1106.4872](https://arxiv.org/pdf/1106.4872) [older].
- Model-written tests plus checking that candidates agree on outputs (CodeT) gave +18.8 points on HumanEval. Agreement of outputs across independent candidates is a verifier in its own right — [arXiv 2207.10397](https://arxiv.org/abs/2207.10397v2) [older].
- Weighted ensembles of several weak verifiers (validators, judges, reward models) beat any single one, and their accuracies can be estimated without labels — [Weaver](https://arxiv.org/abs/2506.18203v2).

### Inferences
- Concrete stack for Errand, all at $0, ordered cheapest first:
  1. Schema and type check on every extraction (e.g. price matches a number with currency, in a sane range for the site; URLs absolute; required fields non-empty). Reject before any LLM checker runs.
  2. Cross-page check: a recipe must extract from N of N saved pages for that site, and the value distribution must match history (RAPTURE-style). A sudden all-same value, all-empty result, or 10x jump flags a break.
  3. Canary pages: keep 1-2 saved pages per site with human-confirmed answers. Every new or repaired recipe must reproduce them exactly. This is the held-out test from section 2 with an extra known answer.
  4. Agreement across independent candidates' outputs on held-out pages (CodeT-style). Only then come checker brains, votes or Gemini.
- These checks feed the escalation score in section 3 and the decision memory in section 4. Failing an invariant is a reliable "don't trust" signal that needs no calibration.

### Gaps
- No recent (2025-2026) paper measuring invariant or canary checks inside LLM web agents specifically was found. The evidence is from classic wrapper maintenance and code generation.
- Precision and recall of schema validators for catching small-model extraction errors were not found. Errand's logs would provide them.
