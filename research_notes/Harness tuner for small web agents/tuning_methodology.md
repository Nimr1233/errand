# Tuning an agent harness on small ground-truth test sets without fooling yourself (as of October 2026)

Scope: Errand's harness tuner scores harness variants around Qwen3.5-2B brains on a 40-page, 4-site reading set (190 answers, 7 deliberately "none") plus a small click set, picks the best harness per site/template, and keeps "lessons". Accuracy is the primary metric and speed only breaks ties. Dozens of variants may be evaluated.

Source-age convention: **[2026]** = 2026 paper or doc; **[older]** = pre-2026 result. A few classic references (Dwork 2015, Recht 2019, Roelofs 2019, AWM 2024, SQuAD 2.0, Thinking Machines 2025) are cited from their canonical URLs. I did not re-fetch them this session and say so where it matters. Numbers labelled "computed" are my own arithmetic (Python, shown in the inferences), not quotes from a source.

---

## 1. Overfitting the evaluation set when selecting among many variants (adaptive data analysis, val/test gaps, how to split)

### Takeaway
Harness and prompt search on a finite set overfits in a measurable way, and the effect is worst with tiny training sets. GEPA with 30 training items lost 28 points against its own seed prompt on held-out data. Four 2026 harness-evolution methods all gained on the set they evolved against, and two of them ended up below the starting harness out of distribution. With 40 pages and 4 sites, Errand needs a locked page-level holdout plus leave-one-site-out evaluation, and must treat every additional look at the holdout as spending it.

### Cited Findings
- **Harness evolution overfits [2026].** RRSI (Google Cloud AI Research and others, arXiv 2609.24972v3, 4 Oct 2026) says recursive harness evolution "may overfit by memorizing the training tasks, showing large in-distribution gains that shrink or even vanish on out-of-distribution benchmarks". It frames repeated proposal and selection on a finite evolve set as "an adaptive overfitting risk" and cites Dwork et al. 2015. — [RRSI](https://arxiv.org/pdf/2609.24972)
- **Concrete gaps, RRSI Table 1 [2026].** Frozen policy Claude Opus 4.8. Harvey LAB evolve set 120 tasks, pristine in-distribution held-out set 40 tasks, plus 3 OOD benchmarks. Base harness: evolve 89.4, ID held-out 86.9, OOD avg 39.7.
  - Meta-Harness: evolve 93.0 (+3.6), ID held-out 89.2, OOD avg +0.9.
  - AHE: evolve 90.7, OOD below base.
  - TTHE: evolve 91.1, OOD 1.7 points *below* base.
  - HarnessX: evolve 91.8, OOD equal to base.
  - RRSI: smallest evolve gain (90.5, +1.1), OOD avg 43.6 vs 39.7.

  The authors summarize: "Every one of them works well on evolve set… The separation appears out of distribution, and there the ranking inverts." — [RRSI](https://arxiv.org/pdf/2609.24972)
- **In-distribution held-out did not separate methods [2026].** The ID held-out split (same task family) scored "quite similar" across all methods (88.5–89.2). Only OOD exposed the overfit. A same-distribution holdout is necessary but not sufficient. — [RRSI](https://arxiv.org/pdf/2609.24972)
- **Tiny training sets break reflective prompt optimizers [2026].** MAGE (Singh, arXiv 2607.11944, 11 Jul 2026), on GSM8K-Hard with gpt-4o-mini, Ntrain=30, Ntest=50, temperature 0, 5 seeds:
  - GEPA-optimized prompts scored 34.0% on test vs 62.4%±2.7 for the unoptimized seed, "a -28.4% regression". The stated reason: "With Ntrain=30, each example represents 3.3% of the signal; clustered failures dominate the reflection trace, pushing the prompt toward a narrow strategy that fails on the held-out 50."
  - OPRO (score-only) never left the seed (62.4).
  - MIPROv2+CoT went from 71.1±8.3 before to 68.9±11.3 after optimization. The gain came from the CoT scaffold, not the optimizer.
  - A fixed CoT-math prompt (68.0±2.5) beat all reflective optimizers: "scaffold choice dominates optimizer choice in low-data regimes."

  — [MAGE](https://arxiv.org/pdf/2607.11944)
- **More candidates raise mean and variance together [2026].** In MAGE, growing the candidate pool from 3 to 5 raised mean accuracy +21.6% and variance 3.7x. The authors recommend evaluating optimizers on "both performance and stability—not just peak accuracy". — [MAGE](https://arxiv.org/pdf/2607.11944)
- **GEPA's own split sizes and gap [2025 preprint; ICLR 2026].**
  - Splits (train/val/test): HotpotQA 150/300/300, IFBench 150/300/294, HoVer 150/300/300, PUPA 111/111/221. The validation set doubles as the per-instance Pareto selection set (D_pareto).
  - The paper reports that reflectively evolved instructions "demonstrate a lower generalization gap" than prior instruction optimizers (Appendix H, Fig. 16). I could not extract the per-benchmark numbers.
  - "The majority of GEPA's rollout budget is spent on validation."

  — [GEPA](https://arxiv.org/html/2507.19457)
- **Practitioner reports of GEPA overfitting [2026, secondary].** Rich textual feedback can lead the reflection LM to encode specific training examples in the prompt (orq.ai). Decagon reports that going from 50 to 500 samples made GEPA prompts ~75% longer while performance dropped, and suggests length regularization. — [orq.ai](https://orq.ai/blog/prompt-optimization-to-improve-model-performance); [Decagon](https://decagon.ai/blog/optimizing-gepa-for-production) (snippet-level only, not verified in full)
- **Reusable holdout [older, 2015].** Dwork et al. (Science 2015) show that reusing a holdout adaptively leaks information, and give "Thresholdout", which answers holdout queries only through a noisy threshold so the holdout can be reused. — [Dwork et al., arXiv 1506.02629](https://arxiv.org/abs/1506.02629) (canonical; not re-fetched)
- **Leaderboard mechanism [older, 2015].** Blum & Hardt's "Ladder" reports a new best score only when it beats the previous best by a margin. This limits leaderboard overfitting. — [Blum & Hardt, arXiv 1502.04585](https://arxiv.org/abs/1502.04585) (canonical; not re-fetched)
- **Re-test evidence [older, 2019].** Recht et al. rebuilt CIFAR-10 and ImageNet test sets. Accuracy dropped 3–15% (CIFAR-10) and 11–14% (ImageNet), while model *rankings* were largely preserved. They attribute the drop mainly to distribution shift, not adaptive overfitting. — [Recht et al., arXiv 1902.10811](https://arxiv.org/abs/1902.10811) (canonical; not re-fetched)
- **Kaggle meta-analysis [older, 2019].** Roelofs et al. (NeurIPS 2019) looked at 100+ Kaggle competitions and found little evidence of substantial adaptive overfitting on large holdouts. That result relies on test sets of thousands of items, which Errand does not have. — [Roelofs et al., NeurIPS 2019](https://papers.nips.cc/paper/9117-a-meta-analysis-of-overfitting-in-machine-learning) (canonical; not re-fetched)

### Inferences
- **Errand's scale is the dangerous regime.** 190 answers in 40 pages is close to MAGE's Ntrain=30 / Ntest=50 and far below GEPA's 300-item validation sets. One page is 2.5% of pages and carries ~4.75 answers, so a single template quirk can dominate a reflection trace, exactly as MAGE describes.
- **Recommended split (page-level, never answer-level, because answers on one page are correlated):**
  1. **Vault, locked held-out:** 1 page per template per site, about 3 pages per site, 12 pages and ~55 answers in total. It is scored only on the final candidate of a tuning cycle, and the score is logged. If a cycle's winner fails the vault, do not re-tune against the vault. Rotate in new pages next cycle; this is a reusable-holdout discipline in the spirit of Thresholdout and Ladder.
  2. **Tune pool:** the remaining ~28 pages. Run selection with repeated page-grouped k-fold inside it (for example 4-fold by page, 2–3 repeats), so proposals are judged on pages the proposer did not inspect.
  3. **Leave-one-site-out (LOSO):** for any *global* harness change, train and select on 3 sites and score on the 4th, rotating through all 4. This is Errand's analog of RRSI's OOD check. RRSI showed in-distribution holdouts cannot tell methods apart, and only the OOD split did.
- **Budget the looks.** Count how many times a candidate list has been scored on the tune pool. After about 30–50 variants on 190 answers, expect the best-of-m winner to be inflated by roughly SE_diff·√(2 ln m), which is about 4–6 points (see section 2). Report the vault score, not the tune-pool score, as the harness's accuracy.
- **Cheap first baseline.** MAGE and RRSI both found that strong fixed scaffolds or conservative edits beat aggressive optimization in low-data settings. A hand-written, well-structured harness is the bar every tuned variant must clear on the vault.

### Gaps
- GEPA Appendix H per-benchmark validation-to-test gap values were not extractable from the HTML (figure only).
- I did not find DSPy MIPROv2 or OPRO papers reporting explicit validation-vs-test gaps at Errand's scale. MAGE is the closest small-N evidence and is a single-author preprint.
- No published study of adaptive overfitting on web-reading test sets of ~40 pages specifically.

---

## 2. Statistics for small sets: confidence intervals, paired tests, sample size, nondeterminism

### Takeaway
On 190 answers in 40 pages, use Wilson or Clopper-Pearson intervals and page-clustered resampling, never the plain CLT. Compare variants paired on the same items. Expect a minimum detectable effect of about 4.5–6.5 points at 80% power, which makes 2–3 point differences undetectable. Measure the run-to-run noise band by re-running the unchanged harness under different batch compositions, and repeat runs (K≥2–3) on unstable items.

### Cited Findings
- **Do not use the CLT on small evals [2025, ICML].** Bowyer, Aitchison & Ivanova argue that CLT intervals are adequate for thousands of items but "usually dramatically underestimating uncertainty" below a few hundred. If every answer is right, or every answer wrong, the CLT standard error collapses to 0. They recommend Wilson score or exact Clopper-Pearson intervals (and Bayesian Beta posteriors) for Bernoulli scores and ship a Python library. — [Bowyer et al., arXiv 2503.01747](https://arxiv.org/pdf/2503.01747); [PMLR v267](https://proceedings.mlr.press/v267/bowyer25a.html)
- **Miller, "Adding Error Bars to Evals" [older, Nov 2024; Anthropic].** Five recommendations:
  1. Report standard errors of the mean.
  2. Use clustered standard errors when questions come in related groups.
  3. Reduce variance by resampling answers or using next-token probabilities.
  4. Run inference on "question-level paired differences" when comparing two models.
  5. Use power analysis to check whether an eval can test the hypothesis.

  — [Miller, arXiv 2411.00640](https://arxiv.org/pdf/2411.00640)
- **Clustering matters (Miller) [older].** On reading-comprehension evals with several questions per passage (DROP, QuAC, RACE, SQuAD), clustered SEs were "far from trivial (up to 3X)" the naive SE. Cluster-adjusted SE equals the CLT SE² plus within-cluster cross-products. — [Miller](https://arxiv.org/pdf/2411.00640)
- **Paired SE (Miller) [older].** SE_paired = sqrt(SE_A² + SE_B² − 2·SE_A·SE_B·Corr(s_A, s_B)). Var_paired = Var_unpaired − 2·Cov/n. Pairing is described as a "free" variance reduction. A paired *and* clustered version exists (Eq. 8). — [Miller](https://arxiv.org/pdf/2411.00640)
- **Sample size (Miller Eq. 9) [older].** n = (z_{α/2} + z_β)²·(ω² + σ_A²/K_A + σ_B²/K_B)/δ².
  - ω² is the variance of the paired difference of conditional means; σ² is within-question (sampling) variance; K is repeats per question.
  - Worked example: δ=3 points, 80% power, α=0.05, ω²=1/9 gives n≈969 questions, so "new evals should contain at least 1,000 questions".
  - Inverted (Eq. 10) with n=198: raising K from 1 to 10 cut the MDE from 13.2% to 7.5% when σ²=1/6, ω²=1/9, Corr=0.5.

  — [Miller](https://arxiv.org/pdf/2411.00640)
- **How many repeats (Miller) [older].** Resampling K times reduces within-question variance to σ_i²/K. Little is gained once E[σ²]/K is well below Var(x). In his uniform-difficulty example, K=2 cuts total variance by 1/3, K=4 by 1/2, and K=6 by 5/9, with an asymptotic ceiling of 2/3. A pooled SE over all K·N answers is inconsistent; average per question first. — [Miller](https://arxiv.org/pdf/2411.00640)
- **Temperature 0 is not deterministic under batching [older, Sep 2025].** Thinking Machines Lab (Horace He) attributes most inference nondeterminism to kernels that are not batch-invariant (RMSNorm, matmul, attention reductions change with batch size or composition). Results as reported in secondary coverage:
  - Qwen3-235B at temperature 0: 80 unique completions out of 1,000 by default; 1,000 identical with batch-invariant kernels.
  - Overhead: about 61.5% in the original prototype, and a reported ~34% throughput cost for SGLang's deterministic mode.
  - vLLM reportedly exposes `VLLM_BATCH_INVARIANT=1`. I did not confirm this in vLLM's docs.

  — [Thinking Machines blog](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) (canonical; not re-fetched); [Spheron summary](https://www.spheron.network/blog/vllm-batch-invariance-why-temperature-0-isnt-deterministic/)
- **Measure the noise band empirically [2026].** RRSI repeatedly evaluates the *unchanged* base harness to estimate a noise band ε before evolution: 3 passes on Terminal-Bench, 5 on EngDesign. On EngDesign, ε was read off a null distribution built by half-splitting the base evaluation's own trials. RRSI calls ε "the one value that must not be tuned, since lowering it buys evolve-set score on noise alone." — [RRSI](https://arxiv.org/pdf/2609.24972)
- **Low statistical power is common [older, 2020].** Card et al., "With Little Power Comes Great Responsibility" (cited by Miller), documents that many NLP comparisons are underpowered. — [Card et al., arXiv 2010.06595](https://arxiv.org/abs/2010.06595) (canonical; not re-fetched)

### Inferences (computed numbers; formulas shown)
- **Wilson 95% intervals at Errand's sizes (computed):**
  - 171/190 (90%): [84.9, 93.5]
  - 180/190 (94.7%): [90.6, 97.1]
  - 186/190: [94.7, 99.2]
  - 190/190: [98.0, 100]
  - 36/40 pages fully correct: [76.9, 96.0]
  - 40/40: [91.2, 100]
  - 7/7 "none" correct: [64.6, 100]
  - 6/7: [48.7, 97.4]

  Rule of three: zero errors on n items still allows a true error rate up to 3/n, which is 1.6% at n=190 and 7.5% at n=40. These intervals are still too narrow, because 190 answers sit in 40 page clusters. Use a page-cluster bootstrap (resample pages with replacement, recompute accuracy, 2,000–10,000 draws) or Miller's clustered SE, and expect up to ~3x widening (Miller's observed range).
- **Paired comparison of two variants on the same 190 answers:**
  - Test: exact McNemar on discordant pairs. b = items A gets right and B gets wrong; c = the reverse. p = 2·Σ_{i≤min(b,c)} C(b+c, i)/2^(b+c).
  - Exact two-sided p<0.05 is reached at 6–0 (p=0.031). 7–1 (p=0.070) and 9–2 (p=0.065) are *not* significant (computed). In practice, a variant needs a net gain of about **6–8 answers (3–4 points) with almost no new errors** to be significant once.
  - Better: run McNemar or a paired bootstrap at the *page* level, resampling pages and summing per-page differences, to respect clustering.
- **Minimum detectable effect, paired, 80% power, α=0.05 (computed).** MDE ≈ (z_{α/2}+z_β)·sqrt(d/n), where d is the discordance rate (share of items where the two variants disagree). At n=190: d=5% gives MDE ≈ 4.5 points; d=10% gives ≈ 6.4 points. At n=40 pages: 9.9–14.0 points. Items needed for δ=2 points at d=5%: ~970. For δ=5 points: ~150. **Conclusion: the 190-answer set can reliably detect ≥5-point improvements, not 2-point ones.** Smaller differences must be treated as ties, or the item count must grow.
- **Winner's curse over m variants (computed approximation).** The expected inflation of the best null variant is ≈ SE_diff·√(2 ln m), with SE_diff ≈ sqrt(d/n). At n=190, d=5%, m=30 that is ~4.2 points; d=10% gives ~6.0 points. Under independence (an upper bound) it is ~5.7 points at n=190 and ~12.4 points at n=40. Bonferroni for m=30 comparisons puts the per-test α at 0.0017 (z=3.14). So a variant that tops a 30-way scoreboard by 3–4 points is consistent with pure noise.
- **Nondeterminism protocol:**
  1. Before tuning, run the incumbent 3–5 times, varying the parallel batch mix (1 brain vs 53 brains). Record each item's flip rate, and set the noise band ε = the max pairwise accuracy spread (or the 95th percentile of half-split differences, as RRSI does).
  2. Tag items that flip in any run as "unstable". Score them as the mean over K=3 runs; this is where Miller's K-resampling helps.
  3. Optionally enable batch-invariant kernels for *evaluation runs only*, if the inference server supports it, accepting the ~30–60% throughput cost. Also measure the production-mode noise separately, because production runs batched.

### Gaps
- I did not verify the exact Bayesian procedure in Bowyer et al.'s library (Beta-Binomial posteriors vs. other models) beyond the snippets.
- No source measured batch-induced flip rates for 2B-class Qwen models specifically. Errand needs to measure its own noise band.
- I did not confirm the `VLLM_BATCH_INVARIANT` flag, or whichever runtime Errand uses (llama.cpp, Ollama), against official docs.

---

## 3. Selection rules: lexicographic accuracy-then-speed, Pareto fronts, minimum-improvement thresholds, racing

### Takeaway
"Accuracy first, speed breaks ties" only works if a "tie" is defined statistically, meaning within the noise band or not significantly different. Otherwise noise picks the winner and speed never matters. Use non-compensatory acceptance gates (noise floor, minimum improvement, cost justification), as RRSI does, and use racing (F-Race/irace) to drop clearly worse variants early.

### Cited Findings
- **RRSI's non-compensatory acceptance criteria [2026].** A candidate must pass every gate before its score can replace the incumbent:
  1. **Leakage screen before evaluation.** A critic rejects diffs that encode task names, entity names, task-specific values or answers, or that add inert machinery. Screening comes *before* scoring so a leaking candidate never gets an inflated score that attracts later rounds.
  2. **Stability floor.** The candidate score must be ≥ best-so-far − ε. This stops "walking downhill through a sequence of regressions that are individually small enough to be mistaken for noise."
  3. **Complexity- and cost-aware acceptance (ridge-style).** For a gain Δ > ε, the extra cost must satisfy Δcost ≤ λ0 + λ1·Δ. λ0 and λ1 are set on the evolve set and then fixed.
  4. **Structural pruning (lasso-style).** Components with no strictly positive measured gain over a 4–5-round window become deletion targets.

  Outcome: the regularized harness used 30% fewer policy tokens. — [RRSI](https://arxiv.org/pdf/2609.24972)
- **RRSI proposal-side controls [2026].**
  - Edits per candidate are capped by a cosine-annealed budget from m_max (3–4) down to m_min=1, so late rounds change one attributable thing at a time.
  - Every evaluated candidate's hypothesis, diff, score, cost and accept/reject decision is logged, so falsified ideas are not re-tested. The paper cites Dwork's point that each evaluation is "another adaptive look".
  - The search counts as stalled when progress over 3 rounds stays inside ε.
  - Hyperparameters are "fixed before a run and never re-tuned; we run no sweep and never consult held-out or out-of-distribution benchmarks."

  — [RRSI](https://arxiv.org/pdf/2609.24972)
- **GEPA uses a per-instance Pareto front [2025/ICLR 2026].** For each validation instance it keeps the best score any candidate achieved. Candidates that are best on at least one instance survive, and strictly dominated ones are pruned. Parents are sampled in proportion to how many instances they lead. — [GEPA](https://arxiv.org/html/2507.19457)
- **MAGE on Pareto selection [2026].** Multi-objective Pareto selection "discourages degenerate specialization" and partially mitigated overfitting at Ntrain=30. — [MAGE](https://arxiv.org/pdf/2607.11944)
- **F-Race and irace [older; irace 4.x current].** F-Race (Birattari 2002) evaluates candidates instance by instance and discards them "as soon as statistically sufficient evidence is gathered against them". It uses a Friedman rank test across instances, then pairwise tests against the best. irace iterates the race, sampling new candidates around the elites. Its elimination test defaults to the t-test when capping is enabled and to the F-test (Friedman) otherwise (irace 4.4.0 docs). — [irace docs](https://www.rdocumentation.org/packages/irace/versions/4.4.0/topics/irace_cmdline); [irace package vignette](https://mlopez-ibanez.r-universe.dev/articles/irace/irace-package.pdf); [F-race overview](https://impact.ornl.gov/en/publications/f-race-and-iterated-f-race-an-overview/)
- **Racing test choice and undersampling [older, 2022].** A simulation study of irace found no universal winner between the Friedman and t-test variants. Undersampling instances caused elite performance losses on some functions. — [arXiv 2204.09353](https://arxiv.org/pdf/2204.09353)
- **Ladder-style margin [older].** Only report or accept a new best when it beats the old best by a margin. — [Blum & Hardt](https://arxiv.org/abs/1502.04585) (canonical; not re-fetched)

### Inferences
- **Proposed lexicographic rule with statistical ties.** Accept candidate B over incumbent A only if all of these hold:
  1. B passes a leakage screen: no site-specific literals in a *global* harness, and no answer strings anywhere.
  2. Paired page-cluster bootstrap or exact McNemar on the tune-pool folds gives P(acc_B > acc_A) ≥ 0.95, or a one-sided lower bound of Δacc > 0. With m candidates in one cycle, use a Holm correction or require ≥ ε + about 3 points.
  3. No new errors on the 7 "none" items and no new failures on canary pages (section 5).
  4. On the vault, B is not worse than A by more than ε.

  If |Δacc| ≤ ε and the paired test is not significant, call it an **accuracy tie**. Then prefer the faster variant only if it passes a *non-inferiority* check: the lower bound of Δacc ≥ −1 point, or −ε. Otherwise keep the incumbent; incumbency is the default.
- **Racing for Errand (F-Race style, page = instance):**
  1. Score all candidates on 6–8 tune-pool pages first; this mirrors irace's "first test" idea.
  2. Run a Friedman test on per-page accuracy, then a paired comparison against the current best.
  3. Drop candidates significantly worse at α=0.05, add one page at a time, and stop when one survivor is left or the page budget is used up.

  This cuts brain-time versus a full 30×40-page grid, and it is natural on one laptop.
- **Speed is secondary.** Do not put latency into the Pareto selection pool during the accuracy race. Run a Pareto (accuracy × seconds) view only among candidates statistically tied on accuracy. This keeps the lexicographic rule honest.
- **Use RRSI's annealed edit budget.** One change per candidate late in tuning makes the "lessons" attributable (section 6).

### Gaps
- irace's current default `firstTest` value was not confirmed from docs in this session.
- No source tests lexicographic-with-tolerance rules specifically for LLM harnesses; the rule above is an inference built from the cited components.

---

## 4. Per-template/per-site harness vs one global harness

### Takeaway
Specialization multiplies the number of selections and shrinks the data behind each one: about 10 pages and ~48 answers per site. That puts each per-site choice deep in the overfitting regime where MAGE's GEPA lost 28 points, and RRSI's leakage critic exists to block exactly that kind of benchmark-specific edit. Default to one global harness with per-site overrides that must beat the global harness on that site's held-out pages by a clear margin.

### Cited Findings
- **Benchmark-specific content is the overfitting signature in harness evolution [2026].** RRSI's critic rejects edits that "explicitly encode task names, entity names, task-specific values, answers, or other logic specific to the evolve benchmark". The regularizers "favor reusable agent mechanisms over benchmark-specific ones or even noises". — [RRSI](https://arxiv.org/pdf/2609.24972)
- **Prior harness-evolution methods gained on the evolve split but not out of distribution [2026].** Meta-Harness had the biggest evolve gain (+3.6) and only +0.9 OOD. TTHE lost 1.7 OOD. — [RRSI](https://arxiv.org/pdf/2609.24972)
- **Small-N reflective optimization narrows strategy [2026].** "Clustered failures dominate the reflection trace, pushing the prompt toward a narrow strategy." — [MAGE](https://arxiv.org/pdf/2607.11944)
- **Fixed harnesses can fail to generalize to open-world tasks [2026].** Harness² (arXiv 2610.14224, Oct 2026) argues that a pre-chosen harness often fails to generalize to open-world tasks. It proposes task-level recursive harness refinement and reports up to +11.5 (WorkBuddy-Bench), +4.5 (JobBench), and +11.8 (LAB) over base harnesses. These are preprint results, seen via abstract and search summary only. — [Harness² abstract](https://arxiv.org/abs/2610.14224)

### Inferences
- **Per-site data budget (computed).** About 10 pages and ~48 answers per site gives a Wilson half-width of about ±8–10 points at 85–90% accuracy (before clustering), and a paired MDE of about 9–13 points. A per-site override can therefore only be validated if it is a *large* win.
- **Hierarchical choice rule ("shrink toward global"):**
  1. Tune a global harness with LOSO.
  2. For each site, try at most a few override candidates, using the global harness plus one local edit (RRSI-style m=1).
  3. Accept an override only if, on that site's held-out pages, it beats global by ≥ max(ε, ~8 points), or wins on ≥ 2 more pages with zero new page-level failures.
  4. Otherwise inherit global.

  This mirrors classic shrinkage (empirical Bayes) logic. I found no web-agent paper that tested it directly.
- **Template granularity.** Per *page template* has even less data than per site. Allow template-level overrides only for deterministic, auditable rules (for example "price lives in `[itemprop=price]`"), verified on ≥ 2 held-out pages of that template. Free-form prompt rewrites per template should not be allowed.
- **Leakage screen for overrides.** Any override that mentions literal answer values or a page's specific text is rejected before scoring, as RRSI does.

### Gaps
- I found no 2025–2026 study comparing per-site and global prompts or harnesses for web extraction agents. Classic wrapper-induction literature (site-specific wrappers are precise but brittle under layout change) was not retrieved this session.
- No evidence on how many pages per template make an override trustworthy. The 2-page minimum above is a heuristic.

---

## 5. Regression gates, canaries, rollback, re-tuning triggers, CI for prompts

### Takeaway
Gate every harness change in CI against the incumbent on fixed ground truth. Set thresholds from measured noise, and set them before looking at any failure. Keep canary pages with known answers that run on a schedule. Roll back on canary failures beyond the noise band, and re-tune when a site's template signature or canary results change.

### Cited Findings
- **promptfoo in CI [2026, secondary].**
  - The `promptfoo/promptfoo-action` GitHub Action runs evals on PRs and posts a before/after comparison against the base branch.
  - Pass/fail thresholds sit on individual assertions (for example `threshold: 0.8`). `threshold: 0` on an assert-set effectively disables grouping.

  — [Medium write-up](https://medium.com/@alexrodriguesj/testing-llm-prompts-like-code-regression-evals-in-ci-cd-with-promptfoo-5242b4dcb9be); [tessl promptfoo guide](https://tessl.io/registry/testland/promptfoo-evaluation) (secondary; verify against promptfoo.dev)
- **Noise-aware gating [2026, secondary].**
  - Guides recommend setting regression thresholds below the spread seen when re-running an *unchanged* prompt several times, and fixing them before seeing any failures.
  - llmci runs several samples and fails only when a drop exceeds run-to-run noise.
  - Metrics where higher is worse (hallucination rate) need a ceiling, not a floor.

  — [Comet/Heartbeat](https://heartbeat.comet.ml/how-do-you-set-up-a-regression-gate-for-prompt-changes-in-ci-1612e304f18d); [llmci](https://pypi.org/project/llmci/)
- **evalgate [2026].** An open-source gate that fails the build on a score drop and posts a delta table on PRs. — [evalgate GitHub](https://github.com/AgentPostmortem/Evalgate)
- **Compare against a contemporaneous baseline [2026].** RRSI reports every number against the unevolved base harness "measured in the same window, so no gain can be attributed to drift in the evaluation infrastructure". — [RRSI](https://arxiv.org/pdf/2609.24972)
- **Stability floor stops slow drift [2026].** RRSI's floor is score ≥ best − ε, so a sequence of small regressions cannot accumulate. — [RRSI](https://arxiv.org/pdf/2609.24972)

### Inferences
- **Errand regression gate (CI or pre-promotion):**
  1. Re-run the incumbent and the candidate *in the same session* on the tune pool and vault.
  2. Block the change if any of these hold: a paired accuracy drop > ε; any vault page goes from fully correct to wrong; any "none" item goes from abstained to answered (hallucination ceiling = 0 new); or click-task success drops on any task.
  3. Post a per-site, per-page delta table, like promptfoo and evalgate do.
- **Canary pages:**
  - Keep 1–2 live pages per site with stable, known answers, refreshed when the site legitimately changes.
  - Run them on a schedule (for example daily) and before each big job. Store a template signature per canary, such as a hash of the DOM skeleton or tag paths with text stripped.
  - **Rollback rule:** if canary accuracy for a site drops beyond ε for 2 consecutive runs while the template signature is unchanged, the harness regressed, so revert to the last promoted version. If the signature changed, the site changed, so trigger re-tuning for that site only.
- **Re-tune triggers:** template-signature change on a canary; rising "none" rate or field-missing rate on production pages of a site; a new brain model or quantization; an inference-runtime upgrade (it changes the noise band, so re-measure ε first).
- **Versioning:** every promoted harness gets an ID. Store its vault score, its ε, the git SHA, and the brain model hash. Rollback becomes a pointer change.

### Gaps
- I did not fetch first-party LangSmith or Braintrust docs this session, so their specific practices (experiment comparison views, online evals) are not cited here.
- No source gave canary-frequency or rollback-threshold numbers for LLM web agents. The numbers above are inferences.

---

## 6. Lessons and memory: storing reusable lessons from tuning; when they help or hurt

### Takeaway
Store abstract, procedural insights, not raw trajectories or page-specific facts. Add lessons incrementally, with curation, instead of rewriting the store. Admit a lesson only after an ablation shows it helps on held-out pages. 2026 evidence shows raw-experience memory can cut success on new, hard cases by 13–26 points, and that adding every experience degrades performance.

### Cited Findings
- **ACE, Agentic Context Engineering [2025 preprint; ICLR 2026].**
  - Treats context as an evolving "playbook" grown by incremental generation, reflection and curation. Incremental delta updates replace full rewrites to avoid "brevity bias" and "context collapse".
  - Reports +10.6% on agent benchmarks and +8.6% on finance. It can adapt from natural execution feedback without labels.
  - A secondary write-up cites an AppWorld case where an 18,282-token context was rewritten to 122 tokens and accuracy fell from 66.7% to 57.1%. This was not verified against the paper.

  — [ACE, arXiv 2510.04618](https://arxiv.org/pdf/2510.04618); [Microsoft Research page](https://www.microsoft.com/en-us/research/publication/agentic-context-engineering-evolving-contexts-for-self-improving-language-models/)
- **Raw trajectories hurt, insights help [2026].** Hu, Long & Wang (NTU, arXiv 2604.27003, 29 Apr 2026), Qwen-Plus, BM25 retrieval, 200 train / 100 test per phase, 2 runs:
  - Forward transfer with raw-trajectory memory: −9.5 points (ALFWorld) and −7.5 (BabyAI). With abstract-insight memory: +6.5 and +9.0.
  - On cases the no-memory baseline could *not* solve, raw memory changed success by −26.1 points (ALFWorld) and −12.7 (BabyAI). Insights gave +3.3 and +9.8.
  - Best forward-transfer design (top-3 individual insights) also caused the most forgetting: BWT −10.0.
  - Retrieval collapse: 88.5% of queries hit the same top-1 item, and only 13 of 240 items (5.4%) were ever retrieved.

  — [Hu et al.](https://arxiv.org/html/2604.27003v1)
- **Indiscriminate memory degrades performance [2026, snippet-level].**
  - An ACL 2026 study reports that adding all experiences to memory consistently degrades performance, while selective addition guided by a strict evaluator does best.
  - An ACL 2026 Findings paper reports a 3.13% drop on ALFWorld from a fine-grained low-level memory layer, while higher-level abstractions helped slightly.
  - Coding-agent memory-transfer work flags negative transfer via "blind imitation".

  — [ACL 2026 memory management](https://aclanthology.org/2026.acl-long.27.pdf); [ACL 2026 Findings](https://aclanthology.org/2026.findings-acl.1535.pdf); [Memory Transfer Learning, arXiv 2604.14004](https://arxiv.org/pdf/2604.14004) (snippets only)
- **RRSI keeps a ledger of mechanisms, including failures [2026].** For each candidate it records the component, hypothesis, diff, score and cost deltas, and accept/reject. "Rejected mechanisms remain negative evidence." Components with no measured gain get pruned. — [RRSI](https://arxiv.org/pdf/2609.24972)
- **AWM, Agent Workflow Memory [older, 2024].** It induces reusable workflows from past web-agent trajectories. Reported relative success gains: 24.6% on Mind2Web and 51.1% on WebArena, with benefits holding as train-test gaps widen (cross-website, cross-domain). — [AWM, arXiv 2409.07429](https://arxiv.org/abs/2409.07429) (canonical; not re-fetched, figures from memory of the abstract)
- **Harness² [2026].** Recursive harnessing at task level, with gains that grow with recursion budget. Its lesson-storage specifics were not retrieved. — [Harness²](https://arxiv.org/abs/2610.14224)

### Inferences
- **Lesson schema for Errand:** {scope: global | site | template; mechanism (abstract rule, e.g. "prices on listing pages may include struck-through old price; take the non-struck value"); evidence: pages it fixed (IDs) and pages it broke; ablation Δ on held-out pages with CI; status: active | probation | retired; date; brain model}. This follows RRSI's ledger and the "insights not trajectories" finding.
- **Admission rule:** a lesson enters "active" only if an on/off ablation on held-out pages shows paired gain > ε and zero new failures on "none" items. Global lessons must contain no site literals (leakage screen). Site lessons may contain selectors but no answer values.
- **Hard-case monitoring.** Track lesson effects separately on "previously failing" items vs "previously passing" items. Hu et al. show that aggregate accuracy hides large losses on hard cases.
- **Curation, not rewrite.** Append and merge lessons incrementally, as ACE does. Cap the number of lessons injected per page (for example top-3 by scope match). Monitor retrieval diversity, because Hu et al. saw 88.5% of queries return the same item. Retire lessons with no positive effect over a window, as RRSI prunes.
- **Small brains (2B) have little context to spare,** so ACE-style long playbooks may cost more than they return. Measure lesson-token cost and apply RRSI's cost-justification rule (Δcost ≤ λ0 + λ1·Δacc).

### Gaps
- No study found on lesson memory for ~2B models specifically. The cited results use Qwen-Plus, GPT-class models, or Claude.
- ACE's ablation numbers on harmful or stale playbook entries were not extracted.

---

## 7. An honest scoreboard for "none" answers and partial matches

### Takeaway
Score "none" (abstention) as its own confusion matrix, not folded into accuracy. Count *hallucinated answers on none-items* and *false "none" on answerable items* separately. Normalize fields by type before exact match. With only 7 none-items, the set cannot certify abstention behavior: 7/7 correct still has a 95% CI of [64.6%, 100%].

### Cited Findings
- **Answer correctness and answerability are separate signals [2026].** Two-axis abstention work (arXiv 2607.08456) reports that separating them gives better abstention than thresholding one confidence score. — [arXiv 2607.08456](https://arxiv.org/pdf/2607.08456) (snippet-level)
- **Three-way outcome labelling [2026].** deepeval's AbstentionClassifier labels responses as abstained, answered, or fabricated, depending on whether the context contains the answer. — [deepeval docs](https://deepeval.com/docs/classifiers-abstention)
- **AbstentionBench [2025].** 20 datasets (unknown answers, underspecified questions, false premises, and others). Reasoning fine-tuning hurt abstention by ~24% on average. — [AbstentionBench, arXiv 2506.09038](https://arxiv.org/html/2506.09038)
- **Abstain-QA [older, 2024].** Introduces an abstention-rate metric and compares strict prompting, verbal confidence thresholds, and CoT for eliciting abstention. — [arXiv 2407.16221](https://arxiv.org/html/2407.16221v1)
- **SQuAD 2.0 precedent [older, 2018].** It mixes unanswerable questions into extraction evaluation, so systems must abstain. Its official scorer normalizes answers (lowercase; strip punctuation, articles and extra whitespace) and reports exact match and token-F1, with separate HasAns and NoAns breakdowns. — [SQuAD 2.0, arXiv 1806.03822](https://arxiv.org/abs/1806.03822) (canonical; not re-fetched)
- **Agents raise the stakes of wrong answers [2026].** AgentAbstain notes that wrong answers in tool-using agents can trigger consequences beyond a bad reply. — [AgentAbstain](https://www.alphaxiv.org/abs/2607.10059.md) (snippet-level)

### Inferences
- **Scoreboard columns:**
  - Answerable items (183): exact-correct, normalized-correct, partial (token-F1 ≥ threshold), wrong, false-none.
  - None items (7): correct-none, hallucinated.
  - Headline: **strict accuracy** (normalized exact match, "none" counts only when gold is none).
  - Hard constraints: **hallucination-on-none = 0 new** vs incumbent, and **false-none rate**, reported separately.
  - Report partial credit (token-F1) as a secondary diagnostic. Never use it as the tie-breaker over strict accuracy; it rewards near-misses that are still wrong for an errand.
- **Field normalizers (typed, applied to both gold and prediction):**
  - Strings: Unicode NFKC, casefold, whitespace collapse.
  - Numbers and prices: strip currency symbols and thousands separators, compare as decimals; keep currency code as a separate field if it matters.
  - Dates: parse to ISO.
  - Lists: set or multiset equality.
  - URLs: canonicalize host and path.
  - Booleans: map yes/true/available.
  - "None" synonyms ("not found", "N/A", "", null) map to one NONE token.

  Version the normalizer alongside the harness, because a normalizer change can move scores without any harness change.
- **Grow the none-set.** To estimate a false-answer rate on unanswerables with ±10 points, you need ~35+ none-items (computed Wilson 95% CI at 33/35 = [81.4, 98.4], half-width ≈ ±8.5). Seven only catches gross failures. Cheap fix: for each page, add 1–2 questions about fields that genuinely do not exist on that page.
- **Asymmetric cost.** If a wrong answer is worse than "none" for Errand's users, an optional utility score is (correct − c·wrong) with c > 1, which rewards abstention over guessing. Use it as a reported column, while strict accuracy stays primary per the lexicographic rule.

### Gaps
- I did not retrieve an authoritative penalty-weighted abstention formula (for example from AbstentionBench) in full text.
- No source on partial-match thresholds (token-F1 cutoffs) for structured web-field extraction specifically.
