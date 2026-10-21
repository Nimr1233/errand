# Raising data-extraction accuracy of small local LLMs (1-4B) on web pages (state as of Oct 2026)

Context: Errand runs 53 parallel Qwen3.5-2B Q4_K_M slots (4,096 ctx each) in llama-server on a 6 GB RTX 3060 laptop GPU, with one free-tier Gemini key. On 105 books.toscrape.com pages: price/availability/UPC 100%, title ~70% (truncated listing titles), rating 0% (rating exists only as `class="star-rating Three"`, which the text snapshot drops), 0 invalid JSON. The recipe path (LLM writes CSS selectors once, code replays them) got 3/5 fields right.

Source-quality note: arXiv papers and model cards are primary. The Stagehand, ScrapingAnt, Firecrawl and Inference.net pages are vendor blogs with small, self-run tests; they are labeled as such below.

## 1. Page representation: which input format helps small models extract best, and how to keep attribute-only facts

### Takeaway
Raw HTML is the worst input and plain markdown/text is cheap but drops attribute-only facts (the cause of Errand's 0% rating). The best-measured setups prune the DOM down to a few hundred tokens while keeping the nodes, attributes and XPaths of what's left. AXE (Feb 2026) gets a 0.6B model to 88.1 F1 on SWDE this way, with a 97.9% token cut.

### Cited Findings
- **AXE (arXiv 2602.01838, Feb 2026, v2 Mar 2026).** Pipeline: clean HTML (drop scripts/CSS, apply HtmlRAG lossless cleaning), chunk it, split chunks into "mini-chunks" that end in atomic structures with full XPaths, have a pruner adaptor pick the XPaths relevant to the query, re-merge into HTML, re-compress. Attributes stay on retained nodes. Base model is **Qwen3-0.6B** with rank-64 rsLoRA adaptors (~40M params) for pruning, QA and schema extraction. — [AXE HTML paper](https://arxiv.org/html/2602.01838)
- AXE token reduction on SWDE: **16,581.9 to 350.6 tokens (97.9%)**. Zero-shot SWDE F1 **88.10**, beating trained baselines with k=1 seed site: MarkupLM-Large 85.71, WebLM-Large 87.57, Render-Full 84.30, SimpDOM 83.06, FreeDOM-Full 82.32. Per domain: Book 92.42, Restaurant 93.13, Auto 80.90. — [AXE HTML paper](https://arxiv.org/html/2602.01838)
- AXE ablation on SWDE (1,000 samples/domain): full 88.37. Without the pruner 87.71. Without the "exact algorithm" (grounding) 83.95. Without the fine-tuned adaptor 83.51. Without AXE extraction 78.17. On WebSRC test it is weaker than trained models: F1 71.1 vs MarkupLM 76.45 and WebLM 78.66 (dev 86.95 is best). Code and adaptors: github.com/abdo-Mansour/axetract. — [AXE HTML paper](https://arxiv.org/html/2602.01838); [AXE abstract](https://arxiv.org/abs/2602.01838)
- **HtmlRAG (arXiv 2411.02959, WWW 2025; older, 2024).** Cleaning removes CSS, comments, JS and "lengthy HTML tag attributes" and shrinks HTML to ~6% of its original length. Plain-text conversion drops 96.71% of tokens; markdown drops 90.32%. — [HtmlRAG paper](https://arxiv.org/html/2411.02959)
- HtmlRAG, Llama-3.1-70B-Instruct at 128K context, ASQA Hit@1: vanilla HTML **44.00**, plain text **59.75**, markdown **56.00**, cleaned HTML without pruning **58.75**. NQ Hit@1: 28.00 / 41.00 / 39.00 / 42.25. With block-tree pruning down to 4K tokens, ASQA Hit@1 is **68.50** (70B) and **71.75** (Llama-3.1-8B). Removing the embedding-pruning step costs up to 11.75 points. The pruners are BGE-Large (~200M) and Phi-3.5-Mini (~3.8B). Caveat: this is QA over retrieved pages, not field extraction. — [HtmlRAG paper](https://arxiv.org/html/2411.02959)
- **NEXT-EVAL (arXiv 2505.17125, May 2025).** Compared input formats that keep DOM semantics: slimmed HTML, hierarchical JSON, and **flat JSON** (text nodes keyed by their position). Flat JSON gave the best record-extraction F1, **0.9567**, with the least positional hallucination. The abstract does not name the models. — [NEXT-EVAL abstract](https://arxiv.org/abs/2505.17125)
- **Stagehand blog (vendor, 2026).** 6 representations on 10 pages including books.toscrape.com, scored with claude-sonnet-5, 3 repeats, 1,440 calls. Raw HTML scored 92% on READ. Markdown scored **6/24 on attribute-only tasks** and 0/9 on placeholder-only login inputs. A hybrid of pruned DOM plus accessibility tree scored best on read and act, at ~1.5x the tokens of markdown. Default `aria_snapshot()`, raw HTML and markdown all missed iframe and closed-shadow-root content (0/21). — [Stagehand blog](https://www.stagehand.dev/blog/html-vs-markdown-vs-accessibility-tree-llm)
- **ScrapingAnt blog (vendor, 2026-10-11, gpt-4.1-mini).** HTML produced correct records in every tested case. Markdown returned `sku: null` where the value existed only as a `data-sku` attribute. The table task returned empty arrays from markdown even though every required value was present. Their advice: use HTML or a deterministic parser when facts live in `data-*` attributes or DOM relationships, and validate records after extraction. — [ScrapingAnt blog](https://scrapingant.com/blog/html-markdown-plain-text-llm-extraction)

### Inferences
- **The rating failure is a representation bug, not a model bug.** The text snapshot drops `class`. Two cheap fixes, both deterministic and costing about 0 GPU:
  - Keep a whitelist of meaningful attributes on retained nodes (`class` tokens such as `star-rating Three`, `data-*`, `title`, `alt`, `aria-label`, `itemprop`, `content`, `href`).
  - Or render attribute-only facts into the text snapshot, e.g. `[class: star-rating Three]`.

  Supported by the AXE design (attributes survive on retained nodes) and the Stagehand and ScrapingAnt attribute results. Note that HtmlRAG-style cleaning, which strips "lengthy attributes", would also drop this, so the whitelist must be explicit.
- **Title truncation (~70%) looks like the same class of problem.** On books.toscrape listing pages the full title is in the `<a title="...">` attribute and in the product page `<h1>`, while the visible text is cut with "...". This is from knowledge of the site, not verified in this pass. Keeping the `title` attribute, plus a rule that rejects values ending in "..." when a longer candidate exists, should fix most of it.
- **The 4,096-token slot budget favors the AXE/HtmlRAG approach.** Prune to the few hundred tokens around the target fields, keeping XPaths and attributes, instead of feeding a whole markdown page. A flat "xpath -> text/attrs" list (NEXT-EVAL's flat JSON) is a simple format that a 2B model can quote from and that code can verify.
- Pruning can run in plain code (drop nav/footer/script, keep nodes near label keywords) with no model. The AXE learned pruner adds only 0.66 F1 over no pruner in its ablation; most of the gain came from the adaptor and grounding.

### Gaps
- No primary-source per-format F1 for 1-4B models specifically (raw vs pruned HTML vs markdown vs a11y tree). NEXT-EVAL's model list and per-format numbers other than flat JSON were not on the abstract page.
- The Stagehand and ScrapingAnt numbers come from frontier/mini API models, not 2B models.
- I did not find the "Dissecting web page representation" paper under that title in this pass.

## 2. Purpose-built small extraction models: numbers, licenses, llama.cpp availability

### Takeaway
Three families matter:

| Model | Size | Input | License | Usable at $0 commercially? |
|---|---|---|---|---|
| Schematron-3B (Inference.net) | 3B, Llama-3.2 base | HTML + JSON Schema | Not confirmed (see Gaps) | Probably, once license is checked |
| NuExtract (NuMind) 2.0-2B / 2.0-8B | 2B / 8B | Documents | MIT | Yes |
| NuExtract-2.0-4B | 4B | Documents | Qwen Research License | No (non-commercial) |
| NuExtract3 | 4B, Qwen3.5 base | Documents | MIT (repo) | Yes, per repo license |
| ReaderLM-v2 (Jina) | 1.54B | HTML to markdown/JSON | CC BY-NC 4.0 | No (non-commercial) |

Schematron-3B is the only one trained on HTML+schema and is the most direct swap-in. NuExtract3 has the strongest measured edge over same-size general models, but on documents, not web pages.

### Cited Findings
- **Schematron-3B.** Base Llama-3.2-3B-Instruct, context up to 128K. Input: cleaned or raw HTML plus a JSON Schema. Recommendation: pre-clean with lxml (matches training data), remove scripts/styles, "avoid over-aggressive removal". HTML-to-JSON LLM-as-judge score (vendor's own benchmark): GPT-4.1 **4.74**, Schematron-8B **4.64**, Schematron-3B **4.41**, base 3B model **2.24**. HF lists 9 quantizations; there is an Ollama build `Inference/Schematron:3B`, which implies GGUF. — [Schematron-3B card](https://huggingface.co/inference-net/Schematron-3B); [Ollama page](https://ollama.com/Inference/Schematron:3B)
- **Schematron V2** was announced 2026-04-16. The blog examples use the paid Inference.net API (`schematron-v2-small`); the scraped page did not show open weights or a license for V2. — [Schematron V2 blog](https://inference.net/blog/schematron-v2/)
- **NuExtract 2.0 family.** 2B = Qwen2-VL-2B-Instruct base, **MIT**. 4B = Qwen2.5-VL-3B base, **Qwen Research License** (non-commercial). 8B = Qwen2.5-VL-7B base, **MIT**. Templates are JSON with typed leaves. In-context examples are supported. Temperature should be at or near 0. — [NuExtract-2.0-2B card](https://huggingface.co/numind/NuExtract-2.0-2B); [ModelScope 4B GGUF note](https://modelscope.cn/models/numind/NuExtract-2.0-4B-GGUF)
- NuExtract 2.0 GGUF repos exist (`numind/NuExtract-2.0-8B-GGUF`; the 4B GGUF has llama.cpp/llama-server instructions). NuExtract 2.0 PRO reportedly beats GPT-4.1 by **+9 F-score** on NuMind's internal benchmark of ~600 documents (invoices etc.). PRO is a hosted product, so not $0. — [NuExtract-2.0-8B-GGUF](https://huggingface.co/numind/NuExtract-2.0-8B-GGUF); [ModelScope 4B GGUF](https://modelscope.cn/models/numind/NuExtract-2.0-4B-GGUF); [Medium summary](https://ritvik19.medium.com/papers-explained-287-nuextract-f722082999b5) (secondary source)
- **NuExtract3 (2026).** Unified 4B VLM on base Qwen/Qwen3.5-4B-Base. The repo is MIT-licensed. Official GGUF sizes: Q4_K_M **2.78 GB**, Q3_K_M 2.32 GB, Q8_0 4.61 GB. Recommended temperature 0.2 for non-reasoning and 0.6 for thinking. Guidance: run non-reasoning by default and enable reasoning only for hard examples. — [NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF); [NuExtract GitHub](https://github.com/numindai/nuextract)
- NuExtract3 structured-extraction average on NuMind's benchmark of documents, not web pages:

  | Model | Score | Failed outputs | Avg thinking tokens |
  |---|---|---|---|
  | NuExtract3.4_4B-RL | **0.651** | 27 | 2,036 |
  | gemma-4-E4B-it | 0.538 | 31 | |
  | Qwen3.5-9B | 0.479 | 170 | |
  | GLM-4.6V-Flash | 0.435 | | |
  | **Qwen3.5-4B** | **0.417** | 229 | **27,177** |
  | Ministral-3-3B | 0.240 | | |

  — [NuExtract GitHub](https://github.com/numindai/nuextract)
- **ReaderLM-v2 (Jina, ICLR 2025; older, early 2025).** 1.54B params, base Qwen2.5-1.5B-Instruct. Converts HTML to markdown/JSON. Schema-guided HTML-to-JSON results:

  | Model | F1 | Pass rate |
  |---|---|---|
  | ReaderLM-v2 | **0.81** | 0.99 |
  | GPT-4o-2024-08-06 | 0.84 | 1.00 |
  | Qwen2.5-32B-Instruct | 0.83 | |
  | Gemini 2.0 Flash | 0.81 | |

  On content extraction it scores ROUGE-L 0.86 vs GPT-4o 0.69. During development it had repetition/degeneration problems, which were fixed with contrastive loss. License **CC BY-NC 4.0 (non-commercial)**. — [ReaderLM-v2 paper](https://arxiv.org/html/2503.01151v1); [Jina model page](https://jina.ai/models/ReaderLM-v2/)
- AXE's Qwen3-0.6B LoRA adaptors (see section 1) are another purpose-built option: released code plus adaptors, SWDE F1 88.1. — [AXE abstract](https://arxiv.org/abs/2602.01838)

### Inferences
- **Turn Qwen3.5 "thinking" off for extraction.** In NuMind's table Qwen3.5-4B averaged 27K thinking tokens and had 229 failed outputs. That would be catastrophic in a 4,096-token slot.
- **VRAM cost.** Moving from a 2B to a 3-4B extractor (Schematron-3B, NuExtract3 Q4_K_M at 2.78 GB) roughly doubles weight memory and per-token KV cost, so 53 parallel slots at 4K context will not fit on 6 GB. Expect something like a dozen slots or fewer. This is an estimate; it was not measured.

  A practical split is to keep Qwen3.5-2B for the easy fields that are already at 100% and send only failing fields or new-site "recipe authoring" to a specialist. Better still, fix representation first (section 1), which may make the swap unnecessary.
- **Licenses.** For a $0 project that might ever be commercial, ReaderLM-v2 and NuExtract-2.0-4B are off-limits. NuExtract-2.0-2B and 8B (MIT) and the NuExtract3 repo (MIT) are fine. Confirm the Schematron weights license before use.
- **Schematron matches Errand's interface.** It is trained on HTML plus a JSON Schema and wants lightly cleaned HTML, so it keeps attributes and would likely see `star-rating Three`. This is not tested.

### Gaps
- Schematron-3B weights license was not readable from the scraped card text. It is probably the Llama 3.2 Community License inherited from the base, but that is unverified.
- No independent (non-vendor) benchmark of Schematron, NuExtract3 or ReaderLM-v2 on SWDE/WebSRC-style web extraction was found.
- NuExtract-2.0-2B GGUF availability was not confirmed, and NuExtract 2.0 is VLM-based, so llama.cpp needs mmproj/multimodal support. Not verified for the 2B model.
- ReaderLM-v2 GGUF availability was not verified in this pass.
- Whether NuExtract3's model weights (as opposed to the repo) carry MIT was not confirmed on the GGUF card.

## 3. Constrained decoding (llama.cpp GBNF / JSON-schema response_format): does it improve accuracy?

### Takeaway
Grammar-constrained decoding guarantees valid structure. On an 8B model it gives small accuracy gains (+0 to +3.6 points) when the prompt is done properly. Errand already has 0 invalid JSON, so the remaining value is semantic: enums and patterns that make wrong values impossible, plus field ordering. llama.cpp's schema coverage is good but not complete.

### Cited Findings
- **JSONSchemaBench (arXiv 2501.10868; early 2025).** 10K real-world schemas, 6 engines. On Llama-3.1-8B-Instruct, constrained decoding "consistently improves" downstream accuracy:

  | Task | LM only | llama.cpp | Guidance | XGrammar |
  |---|---|---|---|---|
  | GSM8K | 80.1 | 82.4 | 83.8 | 83.7 |
  | Last Letters | 50.7 | 52.0 | 54.0 | — |
  | Shuffle Objects | 52.6 | 52.6 | 55.9 | — |

  — [JSONSchemaBench](https://arxiv.org/html/2501.10868)
- llama.cpp schema coverage and compliance in JSONSchemaBench (declared / empirical / compliance):

  | Schema set | llama.cpp | Guidance |
  |---|---|---|
  | GlaiveAI | 0.98 / 0.95 / 0.97 | — |
  | GitHub Easy | 0.85 / 0.75 / 0.88 | 0.90 / 0.86 / 0.96 |
  | GitHub Hard | 0.61 / 0.39 / 0.63 | — |
  | Washington Post | 0.97 / 0.94 / 0.97 | — |

  llama.cpp grammar compile time is ~0.05-0.06 s and time per output token ~27-30 ms on their setup. — [JSONSchemaBench](https://arxiv.org/html/2501.10868)
- **"Let Me Speak Freely?" (EMNLP Industry 2024; older).** Reported a "significant decline" in reasoning under format restrictions, with stricter constraints degrading more. — [ACL Anthology](https://aclanthology.org/2024.emnlp-industry.91.pdf)
- **dottxt rebuttal (late 2024; older).** Re-ran the tests on Llama-3-8B-Instruct with proper prompts. Structured beat or matched unstructured: GSM8K 0.78 vs 0.77, Last Letter 0.77 vs 0.73, Shuffle 0.44 vs 0.41. Their recommendations:
  - Put the reasoning field before the answer.
  - Say in the prompt that the answer must be JSON, and show the schema/example.
  - Use the chat template.
  - Start the assistant turn so the output begins in the right structure.

  — [dottxt blog](https://blog.dottxt.ai/say-what-you-mean.html)
- llama-server accepts a schema as `json_schema` on completion endpoints, or on `/chat/completions` as `response_format: {type: "json_schema", json_schema: {schema: ...}}` (or `{type: "json_object", schema: ...}`). llama-cli takes `-j/--json`. — [llama.cpp grammars README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

### Inferences
- **Use the schema to make wrong answers impossible, not just to get valid JSON.**
  - `rating` as `enum: ["One","Two","Three","Four","Five"]` or integer 1-5.
  - `price` with a `pattern` such as `^£?[0-9]+\.[0-9]{2}$`.
  - `upc` with `^[0-9a-f]{16}$` (books.toscrape UPCs are 16 hex characters; site knowledge, not verified here).
  - `availability` as an enum.

  On a 2B model, enums turn free-text recall into a constrained choice. This is likely the cheapest accuracy lever after representation, at near-zero cost (0.05 s grammar compile).
- **Order schema fields so evidence comes before the value**, e.g. `{"rating_evidence": "...", "rating": "Three"}` or a short `source_xpath` first. This follows the dottxt "reasoning before answer" finding.
- **Keep reasoning fields short.** Long free-text fields inside a 4K slot eat context.
- **Pitfall:** grammars can force a value even when the evidence is missing, which hides "not found" as a plausible fake. Allow `null` (or a sentinel) for every field and check it in code.

### Gaps
- No study found that measures constrained-decoding accuracy specifically on 1-4B models doing web extraction. All numbers above are from 8B models on reasoning tasks.
- The scraped llama.cpp README did not list which JSON Schema features are unsupported. JSONSchemaBench's empirical coverage (0.39-0.95) implies gaps in complex schemas, so keep extraction schemas flat and simple.

## 4. Self-consistency, majority voting and verifier passes for extraction with small models

### Takeaway
I found no measured web-extraction gains from self-consistency on 1-4B models. The strongest evidence for "verify" is grounding: check every extracted value against a real DOM node. AXE's grounding step is worth about 4.4 F1 on SWDE, and it is plain code.

### Cited Findings
- **AXE Grounded XPath Resolution (GXR)** makes every extraction "physically traceable to a source node". The ablation without the exact grounding algorithm drops SWDE F1 from 88.37 to **83.95 (-4.42)**. — [AXE HTML paper](https://arxiv.org/html/2602.01838); [AXE abstract](https://arxiv.org/abs/2602.01838)
- **AutoScraper's synthesis phase** runs the generated scraper over multiple seed pages and keeps the most broadly working one. Its generation step includes the LLM judging whether the value extracted by its XPath matches the value it recognized (a self-check). Numbers are in section 5. — [AutoScraper paper](https://arxiv.org/html/2404.12753v2); [AutoCrawler v1](https://arxiv.org/html/2404.12753v1)
- A clinical extraction study (mobility functional status) applied per-section majority voting over 10 sampled outputs and concluded it is a "practical, model-agnostic mitigation" that improves agreement across models and tasks. It is not web extraction, and exact numbers were not captured in this pass. — [PMC article](https://pmc.ncbi.nlm.nih.gov/articles/PMC13060412/)
- **NuMind** recommends running NuExtract3 non-reasoning by default and turning on reasoning only for hard examples, which is a tiered-escalation pattern. — [NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF)

### Inferences
- **Cheapest "verifier" for Errand: substring/DOM grounding in code.**
  - Reject any extracted value that does not appear verbatim (after normalizing whitespace and currency) in the page text or a whitelisted attribute.
  - Have the model return the source XPath or CSS path, and re-read the value from it.

  Cost is near zero, and it catches hallucinated and truncated values.
- **Voting.** With 53 slots, k=3 voting on only the fields that fail grounding or schema checks costs ~3x on a small share of calls. Use temperature ~0.2-0.7 for diversity, and send disagreements to the free Gemini key. The benefit is plausible but unmeasured for this setting.
- **Voting cannot fix missing input.** If the snapshot lacks the attribute (rating), all k votes are wrong together. Fix representation first.

### Gaps
- No paper or benchmark found with measured self-consistency gains for 1-4B models on SWDE/WebSRC-style extraction.
- No measured numbers for "LLM-as-verifier" second passes on small models for web fields.

## 5. LLM-written scrapers / wrapper induction ("write the selector once, replay")

### Takeaway
Writing the scraper once and replaying it is the right architecture. But the evidence says small models write poor selectors, and the systems that work all validate and repair: run on several sample pages, check the outputs, refine. Errand's 3/5 recipe should get a validation-and-repair loop plus a stronger author (Gemini free tier) for the one-time authoring call.

### Cited Findings
- **AutoScraper (formerly AutoCrawler; arXiv 2404.12753, EMNLP 2024; older).** Two stages:
  1. Progressive generation: top-down (write the XPath to the target node, then check whether the extracted value matches what the model recognized) and step-back (move up to a parent node when that fails).
  2. Synthesis: run the candidate scrapers over multiple seed pages and pick the best.

  Datasets: SWDE, Extended SWDE, DS1. It introduced an "executability" metric. Code: github.com/EZ-hwh/AutoScraper. — [AutoScraper abstract](https://arxiv.org/abs/2404.12753); [AutoScraper paper](https://arxiv.org/html/2404.12753v2)
- AutoScraper SWDE executable evaluation (Correct % / Unexecutable %):

  | Model | CoT | Reflexion | AutoScraper |
  |---|---|---|---|
  | GPT-4-Turbo | 61.88 / 14.37 | 67.50 / 10.94 | **71.56 / 4.06** |
  | GPT-3.5-Turbo | 36.75 / 43.46 | 46.29 / 37.10 | 54.84 / 19.35 |
  | Mixtral 8x7B | 28.75 / 57.81 | 36.25 / 51.25 | 46.88 / 30.31 |
  | Deepseek-coder | 36.56 / 42.50 | — | 38.75 / 39.69 |
  | Gemini Pro | 29.69 / 47.19 | — | 42.81 / 34.38 |

  The authors: "Models with small parameter sizes have significant difficulties in understanding and writing executable paths." — [AutoScraper paper](https://arxiv.org/html/2404.12753v2)
- **Crawl4AI (docs v0.9.x)**, `JsonCssExtractionStrategy.generate_schema(html|url, query, schema_type, llm_config, validate, ...)`:
  - Uses an LLM once to write a CSS/XPath schema.
  - By default it **validates the schema against the HTML and automatically refines the selectors** if they don't produce results (the `validate` parameter).
  - Accepts multiple sample pages "to help the LLM generate stable, non-fragile selectors".
  - Supports `type: "attribute"` (e.g. `"attribute": "href"`) and regex.
  - Works with local Ollama models (no token needed) or OpenAI.
  - Recommended workflow: generate once, cache it, then run LLM-free extraction in production.

  — [Crawl4AI docs](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
- **AXE outputs XPaths** (GXR) for each extracted value, so a per-page LLM extraction also yields selectors that can be checked and reused. — [AXE abstract](https://arxiv.org/abs/2602.01838)
- **"Beyond BeautifulSoup" (arXiv 2601.06301, Jan 2026)** benchmarked LLM-assisted scripting vs end-to-end LLM agents across 35 sites. It notes LLM-written scripts "may be simpler and faster for static sites". No accuracy numbers on the abstract page. — [arXiv 2601.06301](https://arxiv.org/abs/2601.06301)

### Inferences
- **Recipe validation loop for Errand.** This mirrors AutoScraper synthesis and Crawl4AI `validate`, using existing parts:
  1. Run per-page LLM extraction (already ~100% on price/UPC/availability) on 3-5 sample pages to get "silver labels".
  2. Have the recipe author (Gemini free tier preferred, since small models write poor paths per AutoScraper) propose selectors, allowing attribute selectors (e.g. `p.star-rating@class`) and post-processing (regex, class-token-to-number map).
  3. Replay the selectors on the samples in code. Accept a field only if it matches the silver labels on all samples. For each failing field, send the failing HTML snippet, the expected value and the bad selector back for one repair round.
  4. Keep monitoring at replay time: an empty value, a schema/regex failure, or a sudden change in value distribution marks the recipe stale, and the page goes back to the LLM path.

  Cost: a few Gemini calls per site, then $0 per page.
- **Errand's 2 wrong selectors are probably the two weak fields** (rating needs an attribute selector; title needs `@title` or the `h1`). The silver-label check would have caught both automatically. This is an inference; the user's logs were not inspected.

### Gaps
- No accuracy numbers found for ScrapeGraphAI or for Crawl4AI's generate_schema (the docs describe behavior, not benchmarks).
- WebFormer, Klarna product-page dataset and program-synthesis-for-extraction papers were not researched in this pass. They are older (2021-2023) trained-model work.

## 6. Proven "out of the box" tricks

### Takeaway
The best-supported tricks are:
- **Grounding and XPath traceability:** AXE, -4.4 F1 without it.
- **Learning from several pages of the same template and reusing the result:** AutoScraper synthesis; Crawl4AI multi-sample schemas.
- **Exact-record validation after extraction:** ScrapingAnt.

Multiple renderings (text + attributes + a11y) help because each representation has blind spots (Stagehand: a11y misses iframes/shadow roots, markdown misses attributes).

### Cited Findings
- Representation blind spots are complementary. Markdown misses attribute-only state (6/24). Raw HTML, markdown and default a11y snapshots miss iframe/closed-shadow-root content (0/21). The hybrid pruned DOM + a11y tree scored best. — [Stagehand blog](https://www.stagehand.dev/blog/html-vs-markdown-vs-accessibility-tree-llm)
- Template similarity across pages is the basis of AutoScraper ("leverages the hierarchical structure of HTML and similarity across different web pages") and of Crawl4AI's multi-sample schema generation. — [AutoScraper abstract](https://arxiv.org/abs/2404.12753); [Crawl4AI docs](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
- Validate the exact record whichever format is used: fewer tokens do not imply success. — [ScrapingAnt blog](https://scrapingant.com/blog/html-markdown-plain-text-llm-extraction)
- Flat, position-keyed inputs reduce positional hallucination compared with slimmed HTML. — [NEXT-EVAL abstract](https://arxiv.org/abs/2505.17125)

### Inferences
These are reasoned from the cited findings, not separately measured:
- **Cross-page consistency checks.** Within one site, a field's format should be stable: price always `£dd.dd`, rating always one of 5 tokens, UPC always 16 hex characters. Flag outliers for re-extraction. A title that is a prefix of another page's or the h1's title with "..." means truncation.
- **Detail-page preference.** When a listing value looks truncated, follow the link and extract from the detail page.
- **Structured data first.** Before any LLM, parse JSON-LD, microdata and OpenGraph if present; many shop pages carry price, rating and availability there. Not researched in this pass and unsourced here; books.toscrape has none to my knowledge.
- **Template fingerprint cache.** Hash the DOM tag-path skeleton of each page. Pages that match an existing recipe's fingerprint go straight to code replay, and new fingerprints trigger recipe authoring. This is what makes "write once, replay hundreds" safe across sites.
- **Fix order by expected gain per unit of effort for Errand:**
  1. Attribute-preserving pruned snapshot: fixes rating, likely title. ~0 GPU cost.
  2. Schema enums/patterns plus null allowed. ~0 cost.
  3. Code-side grounding check.
  4. Recipe silver-label validation and repair, with Gemini as author.
  5. Only then consider swapping in a specialist model (Schematron-3B / NuExtract3) for hard fields, at the cost of fewer parallel slots.

### Gaps
- No primary measured evidence found for "extract from multiple renderings and vote" as a technique for small models.
- No measurement found of template-fingerprint reuse accuracy.
- JSON-LD/microdata coverage statistics were not researched.
