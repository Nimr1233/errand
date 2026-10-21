# Click targeting and verification for small text-only web agents (state as of Oct 2026)

Context: Errand runs 53 parallel Qwen3.5-2B text-only slots (llama.cpp, about 4,096 tokens of context each) and 25 Playwright windows on a 6 GB laptop GPU, at $0. For reading, picking line NUMBERS scored 39%, while copying the value and letting code "snap" it to the page scored 96%. Clicks allowed: navigation only (links, next page, tabs, filters, open product, load more). Never submit, pay, post, log in or solve CAPTCHAs.

Source-quality note: arXiv papers, the Playwright docs, the CDP protocol definition and the browser-use source are primary. Dates are given per item. Anything from 2023-2024 is marked [older]. A few figures came only from search-result snippets and are labelled "(snippet)". Most benchmark numbers come from models other than 1-4B text-only LLMs, because almost nobody publishes click accuracy for that exact class. Items in "Inferences" are my reasoning, not measured results.

## 1. How to show clickable elements to a small text model, and what element accuracy small models reach

### Takeaway
The measured winner for small text models is a short, pruned candidate list: a cheap ranker first cuts the page to about 50 elements, then the model chooses from small groups (5 options plus "None"). Each candidate is shown as `[id] role name` text, not a full DOM and not a screenshot. Measured element accuracy for 0.2-4B models runs 43-57% in-domain and about 32-56% on unseen sites (Mind2Web family). Compact accessibility-tree views beat full HTML for weaker models, mostly because long inputs make weak models hallucinate element IDs.

### Cited Findings
**Mind2Web / MindAct [older, NeurIPS 2023]: two-stage candidate ranking plus multiple choice**
- Raw pages average **1,135 elements**, and cleaning cuts that to **580**. The target element survives cleaning **94.7%** of the time (training data). — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- Stage 1 is a **DeBERTa-base ranker (86M params)**. Its Recall@50 for the target element is **88.9% / 85.3% / 85.7%** (Cross-Task / Cross-Website / Cross-Domain). — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- Stage 2 is a multiple-choice question with "up to 5 candidate elements... together with a None option". The top-k candidates are split into groups of 5. When several groups pick an option, the winners form new groups. This repeats until one element remains or every group answers None. — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- Element accuracy / Step SR for MindAct by model size:

| Model | Cross-Task | Cross-Website | Cross-Domain |
|---|---|---|---|
| Flan-T5-Base (220M) | 43.6 / 41.0 | 32.1 / 29.5 | 33.9 / 31.6 |
| Flan-T5-Large (~780M) | 53.4 / 50.3 | 39.2 / 35.3 | 39.7 / 37.3 |
| Flan-T5-XL (~3B) | 55.1 / 52.0 | 42.0 / 38.9 | 42.1 / 39.6 |
| GPT-3.5 (few-shot) | 20.3 / 17.4 | 19.3 / 16.2 | 21.6 / 18.6 |
| GPT-4 (50 tasks, top-10) | 41.6 / 36.2 | 35.8 / 30.1 | 37.1 / 26.4 |

  Whole-task success stays tiny: Flan-T5-XL gets 5.2 / 5.1 / 2.9%. — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- Fine-tuned small models beat zero-/few-shot GPT-3.5 and GPT-4 at element selection. A 220M fine-tuned Flan-T5 (43.6) beats few-shot GPT-4 (41.6) in Cross-Task. — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)

**Multimodal-Mind2Web (same tasks), via SeeAct [older, Jan/Mar 2024]**
- FLAN-T5-XL fine-tuned, text-only: Ele Acc / Op F1 / Step SR = **57.1/75.7/53.5** (Cross-Task), **43.8/67.7/41.1** (Cross-Website), **41.4/65.9/38.9** (Cross-Domain). BLIP-2-T5-XL (vision added) is no better: 50.1/39.4/41.2 Ele Acc. LLaVA-1.5 zero-shot reaches only **9.7/9.1/10.9** Ele Acc. — [SeeAct HTML](https://arxiv.org/html/2401.01614)

**WebLINX [older, v2 Sep 2024]: small fine-tuned text decoders beat bigger zero-shot and vision models**
- Overall test-OOD scores: Sheared-LLaMA **2.7B 25.0** (element IoU 22.6); Flan-T5 **3B 23.8** (IoU 20.3); MindAct 3B 20.9; Pix2Act 1.3B (pixels) 16.9; Fuyu 8B (vision) 20.0; Llama-2-13B fine-tuned 25.2. Zero-shot: GPT-4V 10.4, GPT-4T 10.7. — [WebLINX HTML](https://arxiv.org/html/2402.05930)
- The ranker is a "Dense Markup Ranker", a fine-tuned MiniLM dual encoder. It is "5 times faster" than the DeBERTa cross-encoder (916 ms per turn), "at the cost of slightly lower recall". Candidates carry full HTML attributes, XPath and bounding boxes. History is capped at 5 actions and 5 utterances. — [WebLINX HTML](https://arxiv.org/html/2402.05930)
- The paper states that fine-tuned multimodal models "remain behind finetuned text-only models", even when larger. — [WebLINX HTML](https://arxiv.org/html/2402.05930)

**Newer small-model results (2025-2026)**
- **InSTA (v2, 22 May 2025):** **Qwen3-1.7B** goes from **11.5%** zero-shot to **56.9%** judged success after fine-tuning on Qwen3-235B trajectories, on 3,000 held-out sites. That is about "94.7% of the performance of Gemini 2.5 Flash". Pages become a compact **Markdown** observation from a custom parser. Actions are Playwright function calls in a fenced JSON block, with a single retry on parse failure, a cap of 30 actions per site, and a `stop` call to end. The paper does not report element accuracy. — [InSTA v2 HTML](https://arxiv.org/html/2502.06776v2)
- **Explorer (v4, May 2025), vision plus a11y:** Explorer-**4B** (Phi-3.5V, 4.2B) on Multimodal-Mind2Web, Ele Acc / Step SR: **53.4/50.7** (Cross-Task), **55.6/51.4** (Cross-Website), **49.8/47.2** (Cross-Domain). Explorer-7B: 56.5/53.2, 60.5/56.7, 55.7/53.0. Mind2Web-Live full task SR: 18.1% (4B) vs 19.3% (7B). Zero-shot MiniWoB++: 46.74% (4B). Input is a SoM-tagged screenshot plus an a11y tree as `[element_idx] [role] [name]`, built from the top 50 DeBERTa candidates. Synthesis cost: **$0.28 per successful trajectory** (GPT-4o pricing). — [Explorer HTML](https://arxiv.org/html/2502.11357)
- **WebAgent-R1 (EMNLP 2025):** **Qwen2.5-3B** on WebArena-Lite rises from **6.1% to 33.9%** with end-to-end multi-turn RL, from text-only HTML. Behaviour cloning alone gives about 20%. — [WebAgent-R1 PDF (snippet)](https://arxiv.org/pdf/2505.16421)
- **WebRL (ICLR 2025):** Llama-3.1-8B on WebArena-Lite rises from **4.8% to 42.4%**. — [WebRL (snippet)](https://proceedings.iclr.cc/paper_files/paper/2025/file/c66e1fcc9691aae706250638f36f681b-Paper-Conference.pdf)
- **BrowserForge (25 Aug 2026):** a "compact multimodal model" that acts from screenshots only goes from 25.66% to 33.33% on Online-Mind2Web. Model size is not given in the abstract. — [BrowserForge abstract](https://arxiv.org/abs/2608.24848)

**Representation choice by model strength (Apr 2026)**
- On WorkArena L1 (330 tasks), weaker models do better with the a11y tree than with HTML: gpt-oss-20b (high) **46.4 a11y vs 27.6 HTML**, Llama-3.1-70B **18.2 vs 3.6**, Llama-3.1-8B **0.0 vs 1.2**. Strong models gain from HTML (gpt-5.1 high 55.8 to 73.3). The abstract says "compact observations (accessibility trees) are preferable for lower-capability models". — [Read More, Think More](https://arxiv.org/html/2604.01535)
- Average input is **6,720 tokens/step for a11y** and **56,653 for HTML**. Weaker models "suffer from increased hallucination under longer inputs", mainly "not-found" errors (an ID that is not in the DOM). A larger thinking budget suppresses the increase. — [Read More, Think More](https://arxiv.org/html/2604.01535)
- Models with short context (LLaMA 4K) "are often unable to fit the full accessibility tree". — [Filtering paper 2609.27770 (snippet)](https://arxiv.org/pdf/2609.27770)
- **Set-of-Mark (screenshot labels) was the weakest automatic method in SeeAct**, even for GPT-4V. See Q2 for the numbers. — [SeeAct HTML](https://arxiv.org/html/2401.01614)

**DOM distillation in practice**
- Agent-E [older, Jul 2024] has three distillation modes: `text_only`, `input_fields`, `all_fields`. It keeps parent-child structure and injects an `mmid` attribute as the element ID. With GPT-4-Turbo it scores **73.1-73.2%** on WebVoyager. The paper has no ablation isolating distillation. — [Agent-E HTML](https://arxiv.org/html/2407.13032)

### Inferences
- With 4,096 tokens per slot, Errand cannot show a full a11y tree (about 6.7K tokens/step on enterprise pages) or a cleaned DOM (about 580 elements). A pre-filter is required. The cheapest one is code-only: keep visible, in-viewport, navigation-allowed elements, then rank them lexically against the goal. That stands in for MindAct's 86M DeBERTa ranker, which should be added only if recall@k measures too low.
- The best-measured small-model format is groups of about 5 candidates plus None (MindAct). This keeps each choice short, which suits a 2B model's weak long-context attention. It costs 1 model call per group per round instead of 1 call total. With 53 slots, the extra calls are cheap in time.
- Every published 1-4B number above comes from a **fine-tuned** model. Errand's zero-shot Qwen3.5-2B should be expected to sit well below 40-55% element accuracy until the harness compensates (candidate pruning, constrained output, snap-to-element, verification). InSTA's 1.7B baseline of 11.5% zero-shot vs 56.9% fine-tuned shows the size of that gap.
- A small vision model is not clearly worth it for these sites. In SeeAct, set-of-mark screenshots lost to text choices even for GPT-4V. In WebLINX and SeeAct's FLAN-T5 vs BLIP-2, adding vision did not help small models. Explorer-4B (vision) does generalize better cross-website (55.6 vs 43.8 Ele Acc), but it also had synthetic training data, so the comparison is confounded. VRAM for a 4B VLM was not measured in any source. My estimate is several GB with the vision encoder, which would compete directly with the 53 text slots on a 6 GB card.

### Gaps
- I found no published element-accuracy number for a zero-shot 1-4B text-only LLM (Qwen3 or Qwen3.5 class) on Mind2Web-style element selection. InSTA reports only task success.
- A snippet said "Qwen3.5-4B scored 24.1% on full WebArena", but it was not tied to a source I could verify, so it is excluded.
- WebLINX's DMR Recall@k is in an appendix I did not read.

## 2. "Describe the target in words, code matches it" vs "pick an element number"

### Takeaway
Free-form description plus a weak heuristic matcher lost badly to numbered choices in SeeAct (16% vs 39% step SR). But the human-matched description (the "oracle") scored 62%, so the descriptions were good and the matcher was the bottleneck. Free-form action generation also hallucinates far more than choosing from a list (34% vs 2% invalid). The evidence points to a hybrid that fits Errand's "copy, don't count" finding. Show a list, have the model copy the target's visible text (constrained by grammar to listed strings), and let code snap that text to the element, using an ID only as a tie-break.

### Cited Findings
- **SeeAct grounding comparison [older, 2024]** (GPT-4V, Step SR %, 30-task subsets, Cross-Task / Cross-Website / Cross-Domain):
  - **Element attributes** (model describes type and text, heuristic DOM search finds it): **16.1 / 12.1 / 19.0**
  - **Image annotation / Set-of-Mark**: **20.3 / 13.9 / 23.7**
  - **Textual choices** (top-50 DeBERTa candidates as multiple choice): **39.1 / 32.7 / 42.0**
  - **Oracle** (a human finds the element from the model's description): **61.9 / 65.0 / 62.1**
  - Online whole-task success: textual choice **37.8%** vs oracle **51.1%**. — [SeeAct HTML](https://arxiv.org/html/2401.01614)
- SeeAct failure modes:
  - Attribute matching fails because "many elements have no text" and the relevant text often sits in a neighbouring element.
  - Textual choices fail on identical or near-identical elements, where the model "tends to pick the first matching choice".
  - SoM failures are about 54% hallucinated boxes or labels and about 46% wrong label on the right box (an adjacent element's number).
  - — [SeeAct HTML](https://arxiv.org/html/2401.01614)
- **Mind2Web [older]:** at the same 220M size, multiple choice beats direct generation by about 2x. Ele Acc is **43.6 vs 20.2** (Cross-Task), **32.1 vs 13.9**, **33.9 vs 14.2**. Generation "even underperforms the classification baseline" (DeBERTa-B: 26.8). — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- **Action format vs hallucination (Apr 2026, gpt-5-nano, Mind2Web-Live):** invalid or hallucinated action rate is **34.0%** for free-form "action object" prediction, **2.0%** for choosing an action ID, and **3.0%** for an expanded ID space. Mis-grounding (hallucinated or visually similar elements) is named a primary failure. — [Why Do LLM Web Agents Fail?](https://arxiv.org/html/2603.14248v2)
- **Option-ID bias:** LLMs favour certain option-ID tokens (e.g., "A") because of "token bias" in the prior over IDs (20 LLMs tested). PriDe debiases by permuting option order on a few samples to estimate that prior. — [PriDe, ICLR 2024 [older]](https://arxiv.org/abs/2309.03882)
- **ID hallucination grows with input length for weak models.** Not-found IDs rise sharply for gpt-oss-20b on HTML and for gemini-2.5-flash at a 128-token thinking budget. — [Read More, Think More](https://arxiv.org/html/2604.01535)
- **Errand's own reading result:** line-number answers scored 39%, while copy-then-snap scored 96%. On the related extraction work, the AXE ablation shows grounding ("exact algorithm") is worth about 4.4 F1 (88.37 vs 83.95). — internal note `research_notes/Smarter small model web agents/extraction_accuracy.md`; [AXE HTML](https://arxiv.org/html/2602.01838)
- **A ready-made text matcher:** Playwright recommends `getByRole` (with accessible name) and `getByText`, and calls CSS/XPath a last resort. `getByText` takes substring, exact or regex, and "always normalizes whitespace". Locators are "strict": they throw if more than one element matches. `filter({ hasText })` matches case-insensitively inside descendants. — [Playwright locators](https://playwright.dev/docs/locators)
- **Constrained output in llama.cpp:** GBNF grammars restrict output to a pattern. Alternation of literal strings works (`a | b | c`), so the output can be forced to one of N candidate strings or IDs. llama-server accepts `grammar`, `json_schema`, or `response_format` on `/chat/completions`. The schema is "not injected into the prompt". Grammars have "performance gotchas" (issue #4218), and unsupported schema features are "skipped silently". — [llama.cpp grammars README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

### Inferences
- "Pick element number" in MindAct and SeeAct is not the same as Errand's failed line-number task. There the ID sits right next to the element text, so the model copies a token rather than counting lines. The risk for a 2B model is copying the wrong adjacent ID (SoM's 46% wrong-label errors) and position bias (PriDe).
- Recommended format for the tuner to A/B test against plain IDs:
  1. Show each candidate as `[17] link "Next" -> /catalogue/page-2.html`.
  2. Ask for `{"text": <copied visible text>, "id": <id>}`.
  3. Constrain `text` with a GBNF alternation of the exact candidate strings, so no invented text is possible.
  4. Code snaps `text` to the element. If `id` disagrees with the snapped element, trust the text match (Errand's "copy" finding) and log the disagreement as a signal.
- Duplicate labels need a disambiguator that the model can also copy. Examples are many "Add to basket" or "Read more" buttons, or the same link text in nav and body. Append the nearest heading or product title, e.g. `"Read more" (in: "A Light in the Attic")`, so the model copies the pair instead of picking the first match (SeeAct's failure).
- SeeAct's oracle row is the ceiling for describe-then-match: about +20-25 points over choices if matching were perfect. On text-rich practice sites (books/quotes/Wikipedia), almost every navigation target has its own visible text or href. Playwright's role, name and text matching should therefore come much closer to the oracle than SeeAct's 2024 heuristic did. This needs measuring in Errand.
- Randomizing candidate order across retries (cheap PriDe) and majority-voting across 2-3 slots both use the spare parallel capacity.

### Gaps
- No paper directly compares, for a 1-4B text model, "copy the link text, code snaps it" against "output the element ID". Errand's click task set would be the first measurement.
- SeeAct's comparisons used GPT-4V only. Small-model behaviour under each grounding method is unmeasured.

## 3. Which elements are truly clickable, how agents detect them, and click failure modes

### Takeaway
No single signal finds every clickable element. Browser Use stacks about 15 checks: JS click listeners via CDP, tags, ARIA and a11y properties, `onclick`/`tabindex`, icon-size heuristics, and `cursor:pointer` as a last fallback. It then removes hidden and occluded nodes. Playwright's click already refuses elements that are invisible, moving, disabled or covered by an overlay, and its locators re-resolve each time, which avoids stale elements. Blind spots remain: closed shadow roots, XPath inside shadow DOM, cross-origin iframes (off by default in Browser Use), and dropdowns exposed badly in the a11y tree.

### Cited Findings
**Browser Use's `ClickableElementDetector.is_interactive`** returns on the first match, in this order:
1. Non-element nodes, `html` and `body` are never clickable.
2. **JS click listener** detected through CDP.
3. `IFRAME`/`FRAME` larger than 100x100 px.
4. A label without `for` that contains a form control.
5. A span that contains a form control.
6. Class, id or `data-*` containing search terms (`search`, `magnify`, `glass`, `lookup`, `find`, `query`, `searchbox`).
7. A11y properties: `disabled`/`hidden` rule it out; `focusable`/`editable`/`settable`/`checked`/`expanded`/`pressed`/`selected`/`required`/`autocomplete`/`keyshortcuts` rule it in.
8. Tags `button`, `input`, `select`, `textarea`, `a`, `details`, `summary`, `option`, `optgroup`.
9. Attributes `onclick`, `onmousedown`, `onmouseup`, `onkeydown`, `onkeyup`, `tabindex`.
10. ARIA `role` (button, link, checkbox, tab, row, cell, ...), then a11y-tree role (listbox, gridcell, ...).
11. Icon-sized elements (10-50 px) with a class, role, onclick, `data-action` or `aria-label`.
12. Computed **`cursor: pointer`** as the final fallback.

Quirk: the search-pattern check runs before the disabled veto, so a disabled search element still counts as clickable. — [browser-use clickable_elements.py](https://github.com/browser-use/browser-use/blob/main/browser_use/dom/serializer/clickable_elements.py)

**How Browser Use finds JS listeners**
- It runs `Runtime.evaluate` with `includeCommandLineAPI: True` to get DevTools' `getEventListeners()`. It flags elements with `click`, `mousedown`, `mouseup`, `pointerdown` or `pointerup` listeners, then maps them to `backendNodeId` with batched `DOM.describeNode` calls (20 per batch).
- The scan is skipped on pages with **more than 10,000 elements**, and gives up if **more than 100** elements have listeners. Failures are swallowed silently. It uses `querySelectorAll('*')`, so it does **not** enter shadow roots.
- Cross-origin iframes are processed only when `cross_origin_iframes` is enabled (default **False**). Other limits: max 100 iframes, depth 5, and a 1000 px `viewport_threshold`. Visibility checks cover `display:none`, `visibility:hidden`, `opacity<=0` and empty bounds. Paint-order (occlusion) filtering is on by default.
- — [browser-use dom/service.py](https://github.com/browser-use/browser-use/blob/main/browser_use/dom/service.py)

**CDP's native API**
- `DOMDebugger.getEventListeners(objectId, depth?, pierce?)` returns `EventListener{type, useCapture, passive, once, scriptId, lineNumber, columnNumber, handler?, originalHandler?, backendNodeId?}`. `depth` -1 covers the whole subtree. `pierce` traverses iframes and shadow roots (default false). It needs a `Runtime.RemoteObjectId`, so it runs one object per call. — [CDP DOMDebugger.pdl](https://github.com/ChromeDevTools/devtools-protocol/blob/master/pdl/domains/DOMDebugger.pdl)

**`cursor: pointer` is only a hint**
- The W3C CSS WG resolution: "Authors should use pointer on links and may use on other interactive elements". — [W3C CSS archive (snippet)](https://lists.w3.org/Archives/Public/public-css-archive/2018Sep/0181.html)

**Playwright actionability before `click()`**
- Four checks: **Visible** (non-empty bounding box, not `visibility:hidden`; `opacity:0` still counts as visible), **Stable** (same bounding box for 2 consecutive animation frames), **Enabled**, and **Receives Events** (the element is the hit target at the click point, i.e. no overlay intercepts it).
- Playwright retries until timeout, then throws `TimeoutError`. `force` skips these checks.
- — [Playwright actionability](https://playwright.dev/docs/actionability)

**Playwright locators: stale elements, shadow DOM, frames**
- "Every time a locator is used for an action, an up-to-date DOM element is located in the page", so there are no stale handles.
- Locators pierce **open** Shadow DOM by default. XPath does not pierce shadow roots, and closed shadow roots are unsupported.
- iframes need `frameLocator(...)`.
- — [Playwright locators](https://playwright.dev/docs/locators)

**Field failures**
- Agent-E lists failures with "Iframes, canvas or images" and an "inability to operate a button". Clicks that open popups or dropdowns need a follow-up selection, which its change observation surfaces. — [Agent-E HTML](https://arxiv.org/html/2407.13032)
- In WebArena, the a11y tree interface could not select dropdown options, which produced repeated wrong IDs. The fix was a dedicated select action. — [Invariant Labs trace analysis (snippet)](https://invariantlabs.ai/blog/what-we-learned-from-analyzing-web-agents)

### Inferences
- For Errand's navigation-only scope, most targets on the practice sites are plain `<a href>` links. Static pagination "next", categories, product titles, quote tags, author links and Wikipedia article links and tabs all fall here. Start with `a[href]`, `[role=link|tab|button]`, `button` outside forms, and `summary`. Add the JS-listener and `cursor:pointer` signals only for load-more buttons and JS tabs. The listener scan has a real cost and silent limits (10K elements, 100 listeners).
- Safety filter in code, never left to the model: drop `type=submit`, any button inside a `<form>` whose action is not GET, and anything whose text or aria-label matches login, sign-in, checkout, pay, post, send, subscribe or captcha. Drop `href` values that are `javascript:` or point to logout, cart or checkout paths. Pure navigation is idempotent, which also makes retries safe (see Q4).
- Run Playwright with the default actionability checks and never with `force`. A `TimeoutError` with "intercepts pointer events" is a cheap, exact overlay or cookie-banner detector. Handle it with a code-level "dismiss/decline banner" step (decline non-essential), not a model step.
- Hold element references as Playwright locators (role+name, or text plus href), not ElementHandles or backend node IDs. A re-render after "load more" or AJAX tabs then cannot leave stale targets.
- React 17+ and similar frameworks attach many handlers at the root container, not on the element. A per-element listener scan can therefore miss them, and `cursor:pointer` then does the work. This is my inference, not tested here.

### Gaps
- I found no measured precision or recall for any clickable detector (listener-based, cursor-based or a11y-based) on real pages.
- Browser Use's occlusion (paint-order) algorithm lives in a file I did not read.

## 4. Verifying a click worked: checks, act-verify-retry loops, measured gains

### Takeaway
Cheap, environment-grounded checks after each click (URL change, DOM mutation, expected text appears) catch a large, measured failure class: in one 2026 study, 34% of agent actions changed nothing in the DOM. Learned verification ("predict the effect, then check it") gives a 3B model +16 points recovery and fewer loops on mobile. Web-specific ablations that isolate verify-then-retry are scarce. Retries are safe for navigation, but blind repetition is a known failure loop.

### Cited Findings
- **Size of the problem (Mind2Web-Live, Apr 2026):** **34.2% of all actions produce no DOM change**, **10.4%** of failures are repetitions (the same action more than 3 times), **32.0%** of `goto` actions go to non-existent (hallucinated) links, and **16.7%** of actions leave the required domain. — [Why Do LLM Web Agents Fail?](https://arxiv.org/html/2603.14248v2)
- **Agent-E change observation [older, Jul 2024]:** after each action, a Mutation Observer and tracked attributes (e.g. `aria-expanded`) feed back text like "Clicked the element with mmid 25. As a consequence, a popup has appeared with following elements". No ablation isolates its effect. — [Agent-E HTML](https://arxiv.org/html/2407.13032)
- **VeriGUI (7 Apr 2026, ACL 2026):** at step t the model predicts an "expected effect". At t+1 it compares the screen and outputs SUCCESS or NO_CHANGE, then diagnoses and corrects on NO_CHANGE. **3B (Qwen2.5-VL-3B) ablation on AndroidControl-High** (Sim-TSR / Loop Rate / Recovery SR):

| Configuration | Sim-TSR | Loop Rate | Recovery SR |
|---|---|---|---|
| Base | 0 | 30.0 | 35.0 |
| + Standard SFT | 10.0 | 30.4 | 29.7 |
| + Robust SFT (with injected failures) | 13.3 | 26.5 | 45.5 |
| + GRPO | 16.7 | 24.3 | 51.1 |

  Training only on successes made recovery *worse* (29.7 vs 35.0). This is a vision model on mobile. MiniWoB++ was among the online benchmarks. — [VeriGUI HTML](https://arxiv.org/html/2604.05477v1)
- **ReUseIt (IUI '26):** workflows with "execution guards" built from successful and failed traces raised success from **24.2% to 70.1%** on 15 tasks. Unguided retries (up to 3) were less effective than guided fallbacks (snippet). — [ReUseIt abstract](https://arxiv.org/abs/2510.14308); [ReUseIt PDF (snippet)](https://arxiv.org/pdf/2510.14308)
- **Retry hazards:** blind retry can duplicate side effects when the first action actually succeeded. Verify-before-retry is the safer pattern (tool calls, not browsers; snippet). — [Verified Tool Calls 2608.02645 (snippet)](https://arxiv.org/pdf/2608.02645)
- **Audit guidance (1 Oct 2026, WebArena-Lite):** monitor agents with "environment-grounded progress, repeated-action detection, and an explicit completion check". Treat self-reported progress as unverified. — [Auditing WebArena-Lite](https://arxiv.org/html/2610.01491)
- **History as a verifier input:** adding 4 steps of observation history raised gemini-2.5-flash (budget 128) from **28.5 to 39.4** on WorkArena L1. Diff-based history used about **1/3 the tokens** of full history. — [Read More, Think More](https://arxiv.org/html/2604.01535)
- **Playwright's built-in pre-click checks** (visible, stable, receives events, enabled) with retry until timeout cover the "click never landed" class before any post-click check runs. — [Playwright actionability](https://playwright.dev/docs/actionability)

### Inferences
- Verification should be code, not model. Before clicking, the harness already knows the target's `href` and kind. Suggested expected effect per click type:
  - `a[href]`: the URL changes to the resolved href (normalized).
  - Same-page anchor: the fragment changes.
  - Tab or filter: `aria-selected`/`aria-expanded` flips, or the list content changes.
  - Load more: the item count rises.
  - AJAX pagination: the first item's text changes.

  Each needs only a URL compare, a count, or a MutationObserver flag. Cost is about 0 tokens and milliseconds.
- Retry policy for navigation-only clicks (idempotent):
  1. On NO_CHANGE, try the same element again once after waiting for network idle.
  2. If it fails again, offer the model the remaining candidates with the failed one removed (and say so in the prompt).
  3. Stop after N failures and escalate to the huddle or the owner.
  4. Never repeat an identical action more than twice. Repetition loops are a measured 10-30% failure class.
- A "predict the expected effect" field is cheap to add to the 2B output, e.g. `"expect": "page 2 of results"`. VeriGUI suggests the benefit comes from training on failures, so zero-shot the field is mainly useful as a log for the tuner, not as a guaranteed gain.

### Gaps
- I found no web-browser ablation that isolates verify-then-retry for a small text model with clean before/after numbers. VeriGUI is mobile and vision. ReUseIt's 24.2 to 70.1 mixes workflows, guards and fallbacks.
- The exact unguided-retry numbers in ReUseIt were not readable from the snippet.

## 5. Turning a successful click path into a replayable script (record and replay, skills, workflow memory)

### Takeaway
Two kinds of reuse are measured. Memory, meaning workflows fed back into the prompt, gives +12 points on WebArena and +9 Step SR on Mind2Web for GPT-4-class models. But a token-matched 2026 study (EMNLP 2026) found a plain agent given the same budget "matches or surpasses" AWM, ASI and ReasoningBank. Deterministic replay, meaning no model at run time, is where the $0 win lies (Browser Use's workflow-use, SkillWeaver's APIs), but its self-healing is still immature. For Errand, the best fit is: record verified clicks as role+name/href locators, replay in code, and call the 2B only when a replayed step fails verification.

### Cited Findings
- **Agent Workflow Memory [older, Sep 2024], GPT-4:**
  - WebArena: **35.5%** vs BrowserGym 23.5% (+12.0 points, +51.1% relative), and beats SteP's 14 human-written workflows (33.0%). Steps per task drop to 5.9 vs 7.9.
  - Mind2Web Cross-Task, GPT-4: Ele Acc **41.6 to 50.6**, Step SR **36.2 to 45.1**.
  - Mind2Web Cross-Task, GPT-3.5: MindAct 20.3/17.4 → Synapse 34.0/30.6 → AWM **39.0/34.6**.
  - A workflow is a natural-language sub-task plus steps (state, reasoning, action), with placeholders like `{product-name}`.
  - No small models were tested.
  - Caution: the extracted AWM table lists MindAct GPT-4 Cross-Domain as 21.6/18.6/1.0. Those equal the *GPT-3.5* row in the Mind2Web paper (GPT-4 there is 37.1/26.4/2.0). Verify before citing the cross-domain gain.
  - — [AWM HTML](https://arxiv.org/html/2409.07429); [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- **SkillWeaver (Apr 2025):** self-synthesized skills as APIs give **+31.8%** relative success on WebArena and **+39.8%** on real sites. APIs made by strong agents give weaker agents "up to 54.3%" improvement on WebArena. — [SkillWeaver abstract](https://arxiv.org/abs/2504.07079)
- **Budget-matched check (v2 Aug 2026, EMNLP 2026):** tested Gemini 3 Flash, GPT-5.4-mini and Qwen3.6-27B on WebArena (4 domains) and WorkArena-L1. A vanilla agent given the same tokens as extra steps "matches or surpasses all three augmentation methods" (AWM, ASI, ReasoningBank) in aggregate, often with fewer tokens. Run-to-run variance "significantly affects results". — [Budget-constrained study](https://arxiv.org/abs/2606.15017)
- **workflow-use (Browser Use):** you "show the recorder the workflow", it generates deterministic workflows with variables, and later runs need no LLM. On failure it is meant to fall back to Browser Use. The roadmap itself says the LLM fallback is "really bad" and self-healing is planned. It is "very early development", not recommended for production, and AGPL-3.0. — [workflow-use README](https://cdn.jsdelivr.net/gh/browser-use/workflow-use@main/README.md); [AlphaSignal](https://alphasignal.ai/news/browser-use-ships-workflow-use-to-run-automations-a-million-times-without-ai)
- **ReUseIt (IUI '26):** reusable workflows with execution guards, built from successful *and failed* traces: **24.2% to 70.1%** on 15 tasks, with 9 users. — [ReUseIt abstract](https://arxiv.org/abs/2510.14308)
- **Replay robustness:** Playwright says CSS/XPath "can break when the DOM structure changes" and recommends user-facing locators (`getByRole` + name, `getByText`). — [Playwright locators](https://playwright.dev/docs/locators)
- **Errand's own prior result:** the recipe path (LLM writes CSS selectors once, code replays them) got 3/5 fields right. — internal note `research_notes/Smarter small model web agents/extraction_accuracy.md`

### Inferences
- Errand already logs each click with its verified effect. A path becomes a script once every step has a locator in user-facing terms (role, name, href pattern) plus its expected-effect check. Replay then costs 0 model tokens. When a step's check fails, the harness calls the 2B on that one step, re-verifies, and patches the script. That is workflow-use's intended loop, but with Errand's verification doing the "healing" judgment that workflow-use says is weak.
- Parameterize paths the way AWM does: `page-{n}`, category name, product title. One recording then covers many errands, e.g. "open category X then paginate to page N" on books.toscrape.
- Score replay separately in the tuner: replay success rate, the share of steps needing the model, and tokens saved. The budget study warns that gains from memory are easy to overstate without token matching and repeated runs.

### Gaps
- I found no measured replay success rate for no-LLM record/replay on changing live sites (workflow-use publishes no numbers).
- No study tests workflow memory with 1-4B models.

## 6. Benchmarks and simple click test designs usable offline or on practice sites; how others score click accuracy

### Takeaway
Standard click metrics are element accuracy (right element chosen), operation F1, step success (right element and right action), and task success (all steps right). WebLINX adds element IoU. Live benchmarks score the end state (URL or page content) and are known to miss real successes: human audits recover 5-8 points on WebArena-Lite. For Errand, a URL-reached / DOM-state check per click on books, quotes, webscraper.io and Wikipedia gives an exact, offline-repeatable score. Element accuracy and invalid-ID rate should be logged alongside it.

### Cited Findings
- **Mind2Web metrics [older]:** Ele Acc (correct element selected), Op F1 (operation plus value), Step SR (element and operation both correct), Task SR (every step correct). Step and task numbers diverge sharply: Flan-T5-XL gets 52.0 Step SR but 5.2 Task SR. — [Mind2Web HTML v3](https://arxiv.org/html/2306.06070v3)
- **SeeAct [older]** adds offline "Offline0" (no errors allowed) and "Offline1" (one error allowed) whole-task metrics, plus online live-site success. Offline and online disagree because tasks have multiple valid plans: GPT-4V choice scores 3.3% Offline0 but 37.8% online. — [SeeAct HTML](https://arxiv.org/html/2401.01614)
- **WebLINX [older]** scores element-targeting turns by IoU against the target element, alongside intent match (IM) and text F1. — [WebLINX HTML](https://arxiv.org/html/2402.05930)
- **MiniWoB++ (offline, synthetic):** a Base-size WebGUM (~310M) reached **55.7%** with 2.8K demos. The scaled model reached **94.2%** (2023) [older]. Flan-T5-XL HTML-only per task: click-button **0.98**, click-checkboxes 1.00, click-dialog 1.00, click-link **1.00**, but click-color **0.27** and click-dialog-2 **0.34** (snippet). Explorer-4B scores 46.74% zero-shot. — [WebGUM PDF (snippet)](https://arxiv.org/pdf/2305.11854); [WebAgent/HTML-T5 PDF (snippet)](https://arxiv.org/pdf/2307.12856); [Explorer HTML](https://arxiv.org/html/2502.11357)
- **WebArena-Lite** is a 165-task subset, so 1 task is about 0.6 points. The 3B and 8B numbers are in Q1. — [WebAgent-R1 (snippet)](https://arxiv.org/pdf/2505.16421)
- **Evaluator error (1 Oct 2026):** human review recovers **5.45-8.49 points** of success missed by the automatic evaluator (47 tasks, GPT 5.5 settings), e.g. 29.70% raw to 36.97% corrected. Causes: strict formatting rejecting correct answers, successful state changes the final rule missed, and valid results followed by a bad stop action. Recommendation: report raw plus corrected scores and paired per-task gains/regressions, not just net accuracy. — [Auditing WebArena-Lite](https://arxiv.org/html/2610.01491)
- **LLM judges:** InSTA's judges agree with 100 human-labelled trajectories 82.6% (GPT-4o), 81.7% (Llama 3.1 70B) and 78.0% (Gemini 1.5 Pro), rising to 93.1% when the judge is most confident. — [InSTA v2 HTML](https://arxiv.org/html/2502.06776v2)
- **Variance:** run-to-run variance "significantly affects results" and should be a core evaluation criterion. — [Budget-constrained study](https://arxiv.org/abs/2606.15017)
- **webscraper.io's current test-site index** lists: Pagination links (`/test-sites/pagination`, "Standard links are used for pagination"), Load more button (`/test-sites/load-more`), Infinite scroll (`/test-sites/scroll`), and a Log-in site (`/test-sites/website-state-setup-login`). The index does not show the older e-commerce "allinone/ajax" variants. — [webscraper.io test sites](https://webscraper.io/test-sites)

### Inferences
- **Proposed click test item** (one row per item): `{start_url, goal, allowed: navigation, expect: {kind: url|url_prefix|dom_count_increase|aria_selected|text_present, value}, target_locator (ground truth), max_clicks}`. Score each item four ways:
  - Element accuracy: the snapped element equals the ground-truth locator.
  - Step success: the expected effect is observed.
  - Invalid rate: output not in the candidate list, or no element matched.
  - Redundant rate: no DOM change.

  Also log tokens and wall time per click. All checks are code and need no judge, which avoids the 18% judge error and the evaluator false negatives above.
- **Coverage per site:**
  - books.toscrape: category link, "next" pagination, open a product by title, breadcrumb back.
  - quotes.toscrape: tag link, "Next →", author "(about)" link. The "Login" link may be *clicked*, but the form must never be submitted.
  - webscraper.io: category and subcategory, pagination links (URL changes), "load more" (URL does not change, so check item count), and infinite scroll as a scroll-not-click control.
  - Wikipedia: in-article links, "Talk" / "View history" tabs, section TOC anchors (fragment change), and disambiguation pages (a duplicate-text stress test).
- **Hard cases for a 2B model, worth a dedicated slice:** duplicate link text (SeeAct's "first match" failure); many similar products; a target below the fold; a target behind an overlay (expect an actionability timeout); text changes (cart counts); and MiniWoB's colour and dialog-2 tasks, which show the low end even for a fine-tuned 3B.
- **Tuner method:** run each config at least 3 times over the full set with shuffled candidate order. Compare configs per task (paired wins and losses), not only by mean. Keep a fixed held-out slice, e.g. one site never tuned on, to catch overfitting to practice-site layouts.
- **Knobs worth sweeping, cheapest first:**
  - candidate pruning rule and k (10/20/50)
  - group size (all at once vs 5 + None rounds)
  - output = ID vs copied text vs both, with GBNF on or off
  - candidate line format (with or without href, context heading)
  - order randomization and 3-slot voting
  - verification and retry count
  - thinking on or off (Read More, Think More shows a thinking budget cuts ID hallucination)

### Gaps
- I found no public click-only benchmark built on books.toscrape, quotes.toscrape or webscraper.io. Errand's set would be custom.
- WebArena-Lite's per-evaluator-type error rates (url_match vs string match) were not reported in the audit abstract or the text I read.
- I did not confirm whether the older webscraper.io e-commerce "allinone/ajax" URLs still resolve.
