# Small-model web agents: generalising to unseen sites and planning a whole job from one prompt (state as of Oct 2026)

Scope note: research done 2026-10-20. Every number below comes from the cited paper or page. Many are self-reported by the authors, and judge-scored benchmarks (WebVoyager, Online-Mind2Web auto-judge) are not directly comparable with human-scored ones. "Older" marks results from before 2025. Errand context: 53 x Qwen3.5-2B (text, 4k context) on a 6 GB GPU, 25 Playwright windows, a few free Gemini calls a day, $0.

## 1. What benchmarks show about small open models as web agents (2025-2026)

### Takeaway
By mid-2026 the best open 4B models are about as good as 2025 frontier agents on live-web benchmarks: OpenWebRL-4B scores 67.0% on Online-Mind2Web, against 61.3% for OpenAI Operator in the 2025 human-scored study. A trained 1.7B text model reaches 56.9% on 3,000 websites it never saw in training. Untrained small models are weak (11.5% to 32%). The gains come from task-specific SFT plus RL, not from prompting. Older WebVoyager scores near 90% overstate real ability.

### Cited Findings
- **Benchmark inflation.** "An Illusion of Progress?" (COLM 2025) built Online-Mind2Web: 300 tasks on 136 live websites. Results "suggest over-optimism in previously reported results." A simple search agent solves 51% of WebVoyager tasks but only 22% of Online-Mind2Web tasks. — [arXiv 2504.01382](https://arxiv.org/abs/2504.01382); [HTML v4](https://arxiv.org/html/2504.01382v4)
- **Human-scored Online-Mind2Web (2025):** SeeAct (GPT-4o) 30.7%, Agent-E (GPT-4o) 28.0%, Browser Use (GPT-4o) 30.0%, Claude Computer Use 3.5 29.0%, Claude Computer Use 3.7 56.3%, OpenAI Operator 61.3%. Success falls 31.6 points from easy to medium tasks and another 15.4 points from medium to hard. So Browser Use and Agent-E as frameworks add little over the backbone model. — [arXiv 2504.01382 HTML](https://arxiv.org/html/2504.01382v4)
- **Common failures (all agents):** ignoring task requirements, inventing constraints that were not met, little exploration, repeating actions, stopping early when unsure, and leaning too much on keyword search. On failed tasks, Browser Use, Claude CU 3.7 and Operator take nearly twice as many steps as on successful ones. Operator's errors are 57.7% in filtering/sorting and 19.6% in navigation. — [arXiv 2504.01382 HTML](https://arxiv.org/html/2504.01382v4)
- **MolmoWeb (AI2, Apr 2026, ECCV 2026).** Open 4B and 8B screenshot-only agents built on Molmo2 (Qwen3 LLM plus SigLIP2 vision). They use no HTML or accessibility tree. Single-attempt scores on WebVoyager / Online-Mind2Web / DeepShop / WebTailBench: **4B: 75.2 / 31.3 / 35.6 / 43.8**; 8B: 78.2 / 35.3 / 42.3 / 49.5. Trained on 278.5K trajectories, including 36K human ones. — [arXiv 2604.08516](https://arxiv.org/html/2604.08516v1); [ECCV poster](https://eccv.ecva.net/virtual/2026/poster/4684)
- **Other open models, same table** (WebVoyager / Online-Mind2Web / DeepShop / WebTailBench): Fara-7B 73.5 / 34.1 / 26.2 / 38.4; GLM-4.1V-9B-Thinking 66.8 / 33.9 / 32.0 / 22.4; UI-TARS-1.5-7B 66.4 / 31.3 / 11.6 / 19.5; Holo1-7B 55.4 on WebVoyager only. — [arXiv 2604.08516](https://arxiv.org/html/2604.08516v1)
- **OpenWebRL (Jun 2026).** Base model Qwen3-VL-4B-Thinking. Recipe: SFT on only 0.4K teacher trajectories, then online multi-turn GRPO on live websites with about 2.2K RL tasks. **OpenWebRL-4B: WebVoyager 74.1, Online-Mind2Web 67.0, DeepShop 64.0** (average 68.4). For comparison: base Qwen3-VL-4B 52.6 / 32.0 / 33.3; SFT only 60.2 / 47.0 / 48.7; Qwen3-VL-235B 66.4 / 63.7 / 56.7; Gemini computer-use 88.6 / 57.3 / 62.0; OpenAI computer-use 70.9 / 58.3 / 24.7. Its WebVoyager score uses the FARA-curated 595-task subset. — [arXiv 2606.02031](https://arxiv.org/html/2606.02031)
- **OpenWebRL training cost (not $0):** about 300 B200 GPU-hours for the main RL run, about 54K online trajectories, and about $545.5 of GPT-4.1 judge calls per run. A distilled 8B judge matched GPT-4.1, but a plain Qwen3-VL-8B judge was reward-hacked. — [arXiv 2606.02031](https://arxiv.org/html/2606.02031)
- **OpenWebRL ablations relevant to small models:** keeping only the latest screenshot was enough, and extra screenshots added cost with no consistent gain. Removing the model's earlier reasoning from the history cost up to 23.7 points on Online-Mind2Web. A step curriculum (15 steps, then 30) beat a fixed budget. RL from a SFT warm start gained up to 22.3 points on hard tasks, versus 2.3 from the base model. — [arXiv 2606.02031](https://arxiv.org/html/2606.02031)
- **InSTA (CMU/Amazon, 2025, later version).** A **Qwen3-1.7B text agent** trained on about 20K trajectories from 150K LLM-annotated websites. It reads a compact Markdown version of the page and emits Playwright calls as JSON. It reaches **56.9% on 3,000 held-out websites and tasks**, up from 11.5% zero-shot. Training and test websites are entirely separate. That beats the Qwen3-235B policy that collected the data and Llama 4 Maverick, and reaches 94.7% of Gemini 2.5 Flash. Scoring is by a Qwen3-235B judge. It also transfers zero-shot to WebVoyager. Collecting the data cost about 1,200 V100 GPU-hours ($521.55 at AWS spot). — [arXiv 2502.06776v2](https://arxiv.org/html/2502.06776v2)
- **InSTA as extra training data:** mixing 20% InSTA data into human data improves generalisation on a harder 500-site test by +149.0% for WebLINX and +156.3% for Mind2Web, with no change on the original test sets. — [arXiv 2502.06776v2](https://arxiv.org/html/2502.06776v2)
- **WebRL (older, Nov 2024, ICLR 2025):** text agents on WebArena-Lite. Llama-3.1-8B rose from 4.8% to 42.4% and GLM-4-9B from 6.1% to 43%, against GPT-4-Turbo 17.6% and GPT-4o 13.9%. These are the same five sites used in training, so they are not unseen-site results. — [arXiv 2411.02337](https://arxiv.org/html/2411.02337v1)

### Inferences
- The strongest 1-4B evidence for unseen sites is InSTA-1.7B (text, Markdown pages, JSON Playwright actions), which matches Errand's text-only Qwen3.5-2B setup best. Its recipe is SFT on judge-filtered trajectories from many diverse sites. The paper reports 1,200 V100-hours for data collection; a smaller version could be generated slowly with local models, but nobody has shown that at $0.
- The 4B VLMs (MolmoWeb-4B, OpenWebRL-4B) read screenshots. Running them takes a vision encoder and much more context per step. At Q4 quantisation one instance plausibly fits beside others on 6 GB, but 53 parallel copies do not. This is not verified; treat it as an estimate.
- For extraction jobs like "title, price, stock on 1,000 URLs", navigation benchmarks exaggerate the difficulty. Most pages need no multi-step navigation, so a 2B model mainly needs a reliable page-to-fields step, not a full agent loop (see section 4).
- Do not trust WebVoyager-only claims. Use Online-Mind2Web-style human or validated-judge numbers to choose models.

### Gaps
- I found no published web-agent benchmark numbers for Qwen3.5-2B itself or for other 2B models, apart from Qwen3-1.7B in InSTA.
- I did not collect 2025-2026 small-model results for WebArena (full), VisualWebArena, WebLINX, AssistantBench, BrowseComp or WorkArena, nor UI-TARS-2, OpenWebVoyager or the Browser Use leaderboard. There was no time left in the search budget. Check those leaderboards directly.
- I did not confirm whether OpenWebRL-4B weights are public, or MolmoWeb's licence.
- OpenWebRL does not say the evaluation websites were excluded from training, only that overlapping tasks were filtered out.

## 2. Hierarchical "big planner, small workers"

### Takeaway
Splitting planning from execution helps a lot when the executor is trained: Plan-and-Act went from 9.85% to 53.94% on WebArena-Lite. But the best published results replan after every step, which costs a planner call per step, far too many for a ~20-1,500/day Gemini budget. A 2026 study found a single static plan, made once per task, generally beats replanning at every step. Mixed planner/executor model pairs also beat same-model pairs.

### Cited Findings
- **Plan-and-Act (Mar 2025).** The Planner writes the high-level plan; the Executor turns each step into web actions. Both are fine-tuned Llama-3.3-70B. GPT-4o generated the synthetic queries and plans, WebRL-Llama-3.1-70B collected trajectories, and an ORM-Llama-3.1-8B kept only the successful ones. — [arXiv 2503.09572v2](https://arxiv.org/html/2503.09572v2)
- **Plan-and-Act numbers (WebArena-Lite, 165 tasks):** executor alone 9.85% (base) and 36.36% (fine-tuned). Base planner plus base executor 14.21%. Planner trained on expanded synthetic plans plus fine-tuned executor 42.42-43.63%. With replanning after each executor step 53.94%, against 49.1% for WebRL-70B. Base executor with replanning 44.24%. The abstract of a later version reports 57.58% with chain-of-thought, and 45.7% on full WebArena. — [arXiv 2503.09572v2](https://arxiv.org/html/2503.09572v2); [arXiv abs](https://arxiv.org/abs/2503.09572)
- Replanning in Plan-and-Act happens after every executor step, using the current page. That means the number of planner calls equals the number of steps. — [arXiv 2503.09572v2](https://arxiv.org/html/2503.09572v2)
- **"Does the way you plan matter?" (May 2026).** WebArena test set (381 tasks, BrowserGym), focused on 158 hard tasks. Plan formats compared: sequential subgoals, requirement checklist, pseudocode and narrative. Static plans are written once from the goal and the first screenshot. Findings:
  - The best format depends on the model.
  - Mixed planner/executor pairs generally beat same-model pairs: GPT-4.1-mini planning for a Gemini 2.5 Flash executor gave the best AR, 10.7 on hard tasks with sequential plans.
  - "Static planning generally outperforms the dynamic single-agent baseline."
  - Low-level plans sometimes limited exploration on easy tasks.
  - It contains no small-model results.
  — [arXiv 2605.29927](https://arxiv.org/html/2605.29927)
- **Older (2024):** "GPT-4V is a generalist web agent, if grounded" (SeeAct, ICML 2024). GPT-4V completes 51.1% of live-website tasks if its text plans are grounded into actions by hand. The bottleneck is grounding (finding the right element), not planning. — [SeeAct, arXiv 2401.01614](https://arxiv.org/html/2401.01614v2)
- UGround-V1 (OSU) ships grounding-only models at 2B, 7B and 72B (Qwen2-VL based), meant to pair with a planner such as GPT-4o. A secondary copy lists GPT-4o + UGround at about 46-48 element accuracy on Multimodal-Mind2Web across the cross-task, cross-website and cross-domain splits. — [HF UGround-V1-7B](https://huggingface.co/osunlp/UGround-V1-7B); [UI-TARS mirror table](https://gitee.com/tttralf/UI-TARS)
- **Older (2023):** ReWOO plans once with no observations, then workers run tools and a solver combines the results. It reports 5x token efficiency and +4% accuracy on HotpotQA. It distilled the planner from 175B GPT-3.5 into a 7B LLaMA, which is evidence that a fine-tuned small model can hold a planning skill. — [arXiv 2305.18323](https://arxiv.org/pdf/2305.18323v1); [The Decoder summary](https://the-decoder.com/rewoo-new-method-makes-augmented-language-models-more-efficient/)

### Inferences
- For Errand: one Gemini call per job to write a static, structured plan, plus at most one call per unknown site to write an extraction recipe. That matches the "static plan" finding and keeps Gemini use at about 1 + (number of new sites) calls per job. Replanning every step, Plan-and-Act style, is impossible on the free tier.
- The evidence that "big plans, small model executes" beats "small model alone" comes from 70B executors (Plan-and-Act) or frontier pairs (2605.29927). No paper found tests a frontier planner with a 1-4B executor on the web. The ReWOO 7B planner is the closest, and it is older.
- Small workers fail at grounding and at keeping track of constraints (section 1 failure list). A plan for a small model should therefore spell out concrete checks ("price must be a number with a currency symbol") rather than leave reasoning to it.

### Gaps
- I found no controlled study with a frontier planner and a 1-4B web executor, and none counting planner calls per job for batch work like 1,000 URLs.
- Agent-E's own WebVoyager number (often quoted as 73.2%) was not checked against its paper. Only its Online-Mind2Web 28.0% is verified here.

## 3. Memory and skill libraries (AWM, ASI, SkillWeaver, PolySkill, newer)

### Takeaway
Remembering workflows and skills helps a lot on sites the agent has already seen: AWM gives +51% relative on WebArena, ASI +23.5 points, SkillWeaver +31.8% relative. On truly unseen sites the gains shrink to a few points, or reverse. Programmatic skills tied to one site's layout are rarely reused elsewhere (under 9% for ASI and under 3% for SkillWeaver, per a 2025 critique). For Errand, the dependable form of "memory" is a per-site or per-template recipe cache, not a library of cross-site skills.

### Cited Findings
- **Agent Workflow Memory (AWM, Sep 2024, older).** It turns past successes into short reusable workflows: a text description plus action steps, with values replaced by placeholders such as `{product-name}`. Results:
  - WebArena (GPT-4): 35.5% SR against 23.5% for BrowserGym (+51.1% relative) and 33.0% for SteP with hand-written workflows.
  - Learning is quickest over about the first 40 queries; the gain reaches up to 22.5 points after "tens of examples".
  — [arXiv 2409.07429](https://arxiv.org/html/2409.07429)
- **AWM on unseen Mind2Web sites (GPT-4):**

  | Split | Step SR without AWM | Step SR with online AWM | Task SR without | Task SR with |
  |---|---|---|---|---|
  | Cross-website | 30.1 | 33.9 | 2.0 | 1.6 |
  | Cross-domain | 18.6 | 35.5 | 1.0 | 1.7 |

  Step accuracy rises, but whole-task success stays near zero. With GPT-3.5 on cross-task, step SR went from 17.4 to 34.6. — [arXiv 2409.07429](https://arxiv.org/html/2409.07429)
- **ASI, Agent Skill Induction (COLM 2025).** It adds verified Python skills (for example `search_product`) to the action space. On WebArena it beats the static baseline by 23.5 points and AWM's text skills by 11.3 points, and cuts steps by 10.7-15.3%. The authors credit programmatic verification during induction. — [arXiv 2504.06821](https://www.arxiv.org/abs/2504.06821)
- **SkillWeaver (Apr 2025).** The agent explores a site, practises and distils skills into APIs. Reported gains: +31.8% relative on WebArena and +39.8% on real websites. APIs made by strong agents improve weaker agents by up to 54.3% on WebArena. — [arXiv 2504.07079](https://arxiv.org/abs/2504.07079)
- **Critique (PolySkill, Oct 2025).** On unseen websites, ASI skills are reused less than 9% of the time and SkillWeaver skills less than 3%, because skills are tied to one site's design. These are the authors' measurements, seen through a search summary. — [PolySkill arXiv 2510.15863](https://arxiv.org/html/2510.15863)
- **SkillMigrator / "Beyond Domains" (Jun 2026).** Skills are stored without site-specific element references. They are looked up by text similarity combined with accessibility-tree layout similarity (tree edit distance), and only used if the score clears a gate. Mind2Web results with GPT-4.1 (success rate):

  | Method | Cross-website | Cross-domain |
  |---|---|---|
  | ReAct (no skills) | 56.2 | 62.3 |
  | ASI | 54.9 | 57.3 |
  | PolySkill | 57.6 | 60.1 |
  | SkillMigrator | 57.1 | 59.4 |
  | PolySkill +update | 61.3 | 63.4 |
  | SkillMigrator +update | 60.5 | 63.0 |

  Skill reuse rates: ASI 17.4%, PolySkill 22.7%, SkillMigrator 28.1%, rising to 23.6%, 31.0% and 35.4% with updates. SkillMigrator uses about 8-10% fewer LLM actions at matched success. — [arXiv 2606.17645](https://arxiv.org/html/2606.17645v1)
- Related 2026 work on online skill learning with state-grounded retrieval exists, but I did not read it. — [arXiv 2606.04391](https://arxiv.org/pdf/2606.04391)

### Inferences
- On unseen sites, static skill libraries can be slightly worse than none (ASI 54.9 vs ReAct 56.2 cross-website). Gains appear only when the library keeps updating while the agent works on the new site (+5 points for PolySkill). All these results use GPT-4-class models, so expect smaller or no gains with a 2B model.
- The most transferable lesson is to look skills up by page structure, not just task text: SkillMigrator uses layout similarity. Errand could do a cheap version without AI, keyed on DOM-skeleton or template similarity (section 4).
- AWM's text workflows with placeholders are cheap to inject into a 4k-context 2B model. Programmatic skills are better still, because a script runs without the small model reasoning at all.

### Gaps
- I found no skill-library result on 1-4B models, nor on bulk extraction rather than navigation tasks.
- I did not check SkillWeaver's absolute numbers or which models it used, nor PolySkill's full tables.

## 4. Site-structure reuse: templates, URL patterns, pagination, structured data

### Takeaway
The cheapest way to handle 1,000 pages from one site is to generate an extraction script once per template, check it on other pages of the same template, and run it with no LLM per page. SCRIBES (ICLR 2026) builds its RL reward on exactly this cross-page check. Many product pages also already carry machine-readable data (schema.org JSON-LD on about half of sampled pages), which can be read with no AI at all.

### Cited Findings
- **SCRIBES (Meta, ICLR 2026).** A model is trained with RL to write reusable extraction scripts for groups of similar pages on one site, instead of running an LLM on every page. A script is rewarded by running it on other pages in the same group and comparing the output with ground truth (fuzzy F1, GRPO). Reported results: over 13% better script quality than strong baselines, and over 4% better downstream QA accuracy for GPT-4o. It trains iteratively on synthetic annotations from CommonCrawl. — [arXiv 2510.01832](https://arxiv.org/pdf/2510.01832); [OpenReview](https://openreview.net/forum?id=gQSnEIA3Z3); [MLAnthology ICLR 2026](https://mlanthology.org/iclr/2026/liu2026iclr-scribes/)
- SCRIBES' motivation: old wrapper-induction methods generalise poorly, and per-page LLM extraction costs too much. — [OpenReview](https://openreview.net/forum?id=gQSnEIA3Z3)
- **AutoCrawler (2024, older).** An LLM uses the HTML hierarchy to write extraction rules or action sequences that are then reused instead of calling the LLM on every page, refining them through "top-down" and "step-back" operations after failures. — [arXiv 2404.12753](https://arxiv.org/html/2404.12753v1)
- **XPath Agent (Feb 2025).** It shrinks the HTML to about 10-20% of its size, then a stronger LLM writes XPaths meant to stay valid across pages. This comes from a third-party summary. — [arXiv 2502.15688](https://export.arxiv.org/pdf/2502.15688); [summary](https://themoonlight.io/review/xpath-agent-an-efficient-xpath-programming-agent-based-on-llm-for-web-crawler)
- **Structured data on pages (Web Data Commons, 2024 crawl).** 51.25% of sampled pages contain structured data (5.7% in 2010). JSON-LD is used by 70% of sites that annotate (about 11.5M sites) and Microdata by 46% (7.6M). Average JSON-LD triples per page rose from 10 in 2015 to 57 in 2024. — [Uni Mannheim WDC 2024 news](https://www.uni-mannheim.de/dws/news/wdc-json-ld-microdata-rdfa-data-corpus-2024-published)
- Product-specific WDC counts come from a secondary source (unverified): websites with Product annotations grew from 594K (2018) to 3.3M (2024), and Product/sku adoption rose from 21% to 60% over five years. — [Net Solutions](https://www.netsolutions.com/?p=114016)
- AWM's WebArena results include a cross-template subset (33.2% SR), so template-level reuse is a known evaluation axis. — [arXiv 2409.07429](https://arxiv.org/html/2409.07429)

### Inferences
Suggested pipeline for Errand, ordered by cost and not measured end to end:
1. Try JSON-LD, Microdata or OpenGraph first. Schema.org Product/Offer usually holds name, price, priceCurrency and availability, and needs no LLM.
2. Group the URLs by host plus path pattern (for example `/product/{slug}`), then by DOM-skeleton similarity, so there is one recipe per group.
3. For each group, Gemini or a 2B model writes CSS/XPath selectors once. Check them on 3-5 other pages of the group, SCRIBES/AutoCrawler style.
4. Run the selectors with plain code on every remaining page.
5. Send a page to a 2B model only when its selectors fail validation.

Tools that can do steps 1-2 without AI include extruct (JSON-LD/Microdata), sitemap parsers such as ultimate-sitemap-parser or Scrapy's SitemapSpider, and Scrapling's adaptive selectors. These come from general knowledge and were not verified in this session; check versions before use. For pagination, "next" links, `rel=next`, or `?page=N` patterns can usually be found with code (also unverified here).

### Gaps
- I found no paper measuring how often such a script still works across all pages of a template on live e-commerce sites, nor how fast scripts break as sites change.
- I found no benchmark for pagination detection or URL-pattern clustering run without AI. WDC Product coverage of price and availability fields was not verified from the primary WDC stats page.

## 5. Test-time search for web agents (tree search, world models, best-of-N, Agent Q)

### Takeaway
Search and sampling give large gains. MolmoWeb-8B goes from 78.2% to 94.7% on WebVoyager with best-of-4 and a judge; tree search adds +28-40% relative; Agent Q on real bookings goes from 81.7% to 95.4% with search. The cost is many more model calls, page resets and a judge. For Errand, the affordable version is a few parallel short attempts plus a cheap verifier, used only on pages that fail. Full tree search on 1,000 pages is not viable.

### Cited Findings
- **Tree search for LM agents (Koh et al., 2024, older; revised Feb 2026).** Best-first search in the real environment. GPT-4o on VisualWebArena: 26.4% SR (+39.7% relative). WebArena: 19.2% (+28.0% relative). Performance grows with more compute. — [arXiv 2407.01476](https://arxiv.org/abs/2407.01476)
- Tree search cost (secondary summary): a budget of 20 needs about 20x more LLM calls, about 3x the steps and about 10x the wall-clock time of a reactive agent. Backtracking needs page resets, which are hard on live sites. — [Lacuna summary](https://lacuna.tiptreesystems.com/work/tree-search-for-language-model-agents/wrk_b1d5978e7207e55966bedc59524736e5)
- **WebDreamer (TMLR 2025).** The LLM simulates what an action would do before acting. On VisualWebArena (GPT-4o): 23.6% against 17.6% reactive (+34.1% relative), only slightly behind tree search. It is 4-5x more efficient than tree search in wall-clock time. Their fine-tuned Dreamer-7B improved +4.7 points over base Qwen2-VL-7B. — [arXiv 2411.06559](https://arxiv.org/pdf/2411.06559); [GitHub](https://github.com/OSU-NLP-Group/WebDreamer)
- **Agent Q (MultiOn, Aug 2024, older).** MCTS plus off-policy DPO. On real booking tasks, Llama-3 70B rose from 18.6% to 81.7% zero-shot after one day of data collection, and to 95.4% with online search. These are vendor-reported numbers on a small task set. — [arXiv 2408.07199](https://arxiv.org/abs/2408.07199)
- **Parallel attempts plus judge (MolmoWeb, 2026).** Best-of-N chosen by an LLM judge: MolmoWeb-8B pass@4 is 94.7% on WebVoyager and 60.5% on Online-Mind2Web, versus 78.2% and 35.3% for one attempt. Three parallel 30-step runs (86.2%) beat one 100-step run (78.2%). — [arXiv 2604.08516](https://arxiv.org/html/2604.08516v1)
- OpenWebRL: pass@4 above 90% on all three benchmarks, which the authors read as RL making successful strategies more varied. — [arXiv 2606.02031](https://arxiv.org/html/2606.02031)
- **CATTS (Feb/Aug 2026).** Spends extra compute only on uncertain steps, measured from the agent's own vote spread (entropy, top-1/top-2 margin). Up to 11.8% better than majority voting, with fewer tokens than spending extra compute on every step. Spending more on every step "quickly saturates" on long tasks. Tested on WebArena-Lite, Online-Mind2Web and GoBrowse. — [arXiv 2602.12276](https://arxiv.org/abs/2602.12276)
- **Judges that pick or verify attempts.** WebJudge agrees with humans about 85.7% of the time with o4-mini and 83.6% with GPT-4o. WebJudge-7B (Qwen2.5-VL-7B) reaches 87.0% and needs only two calls per trajectory. — [arXiv 2504.01382 HTML](https://arxiv.org/html/2504.01382v4). InSTA's judges were 78.0-82.6% accurate on 100 human-labelled runs, and up to 93.1% when the judge was fully confident. — [arXiv 2502.06776v2](https://arxiv.org/html/2502.06776v2)

### Inferences
- At 53 workers, best-of-N costs N x the worker time and browser windows. The browser pool (25 windows) runs out before the GPU does. So use N=2-3 only on pages that fail a deterministic check (missing price, wrong type), CATTS-style selective spending, not on every page.
- Tree search and MCTS need resettable environments and a value or judge model. On live shop pages, actions like "add to cart" have side effects and must not be explored freely.
- For read-only extraction, "search" can just mean sampling 2-3 extractions from the 2B model at temperature above 0 and voting field by field. That is cheap, needs no reset and uses no Gemini. This is not measured in any paper found.

### Gaps
- I found no test-time-search result at the 1-4B scale apart from MolmoWeb-4B and OpenWebRL-4B pass@k. I found no cost-per-success analysis for small local models.
- I did not get CATTS's model sizes or per-benchmark numbers (abstract only).

## 6. Planning a whole job from one prompt, and checking the plan before 1,000 pages

### Takeaway
"Plan once, then run the plan as a graph" works and saves a lot: ReWOO uses 5x fewer tokens, and LLMCompiler is up to 3.7x faster and 6.7x cheaper than ReAct with about 9% better accuracy. This matches Errand's need: one Gemini call to turn the prompt into a structured plan, then plain code fans the work out to 53 workers. The proven way to check a plan before scale is to run the generated recipe on a few held-out pages of the same template and score it against expected fields (SCRIBES' reward), plus a judge for navigation tasks. I found no paper that studies a "dry run on 3 pages" gate by itself.

### Cited Findings
- **LLMCompiler (ICML 2024, older).** A planner emits a graph of function calls, a task-fetching unit dispatches them, and an executor runs them in parallel. Against ReAct: up to 3.7x faster, up to 6.7x cheaper and up to ~9% more accurate. The speed comparison used a prompt-tuned ReAct. ReAct's failures were redundant repeated calls and stopping early on incomplete results. — [arXiv 2312.04511](https://arxiv.org/pdf/2312.04511); [PMLR](https://proceedings.mlr.press/v235/kim24y.html)
- **ReWOO (2023, older).** Planner, then workers, then solver. 5x token efficiency and +4% on HotpotQA, more robust when tools fail, planner distilled to 7B. — [arXiv 2305.18323](https://arxiv.org/pdf/2305.18323v1)
- **Static versus dynamic plans on the web (2026):** static once-per-task plans generally beat replanning every step. Dynamic agents loop, lose track of progress, or wrongly mark subtasks done. Examples: lowering a price repeatedly instead of saving it, and skipping a "Go" click. — [arXiv 2605.29927](https://arxiv.org/html/2605.29927)
- **Plan-and-Act synthetic plan data:** a planner trained on GPT-4o-expanded synthetic plans went from 14.21% to about 43% on WebArena-Lite. Plan quality, and training on plans, matters more than the plan being present. — [arXiv 2503.09572v2](https://arxiv.org/html/2503.09572v2)
- **Checking generated scripts on sibling pages:** SCRIBES scores each script by running it on other pages of the same group against ground-truth triples. That cross-page check is the training signal behind its +13% script quality. — [OpenReview](https://openreview.net/forum?id=gQSnEIA3Z3)
- **Judge-based checking of navigation results:** WebJudge's average gap from human success rates is 3.8 points with o4-mini and 3.9 with WebJudge-7B, against 7.8 with GPT-4o. — [arXiv 2504.01382 HTML](https://arxiv.org/html/2504.01382v4)
- **Failure signal:** failed runs take about twice as many steps as successful ones for several agents, so an unusually high step count is a cheap early warning. — [arXiv 2504.01382 HTML](https://arxiv.org/html/2504.01382v4)

### Inferences
Suggested planner contract for Errand (synthesis, not measured):
1. One Gemini call turns the prompt into JSON with: the target fields and their types and checks (for example price is a number plus currency, stock is one of in/out/limited); the input URL list or a seed-discovery step (sitemap or search); a graph of steps (fetch, extract, compare); and the output schema.
2. Code groups the URLs by template (section 4).
3. A dry run on 3 pages per template checks that the fields fill and pass the checks. If any fails, make one Gemini repair call for that template, or fall back to the 2B model reading the page.
4. Only then fan out to all pages. Keep checking with code, and re-run the dry run when a template's failure rate rises.

Expected Gemini cost: about 1 call per job plus about 1 per new template. That fits even the low ~20/day end if jobs reuse cached recipes.

- Keep each worker's task to one step. The 2026 failure list (loops, lost progress, constraints marked done when they were not) is worst for small models over long horizons.
- "Compare prices on 3 shops" needs a merge step that matches products across shops. A plan should put this in a final code or LLM step, not ask each worker to do it.

### Gaps
- I found no study measuring how well a small pilot run (for example 3 pages) predicts full-run accuracy, nor the best pilot size.
- Plan-and-solve prompting (Wang et al., 2023) numbers were not retrieved.
- I found no evidence on how well Gemini free-tier models plan web jobs specifically, and the free-tier quotas themselves are outside this note.
- One fetch (Plan-and-Act HTML) came back with the tool reporting an "embedded instruction" in the page. It was ignored and only paper facts were used.
