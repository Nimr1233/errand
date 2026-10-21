# Phase 1 benchmark results (spec section 15)

Measured on 2026-10-18 on the user's laptop: Windows 11, Intel i5-10500H, 16 GB RAM, NVIDIA RTX 3060 Laptop GPU with 6,144 MiB (confirmed by `nvidia-smi`), driver 566.14. Everything is free software. Total cost: $0.

## Software

- llama.cpp `llama-server`, build b11718 (`llama-b11718-bin-win-cuda-12.4-x64.zip`, SHA-256 matches GitHub's published digest)
- Model: `Qwen3.5-2B-Q4_K_M.gguf` from unsloth/Qwen3.5-2B-GGUF (Apache-2.0; SHA-256 `aaf42c8b…9223` matches Hugging Face)
- Scrapling 0.4.12, Python 3.11

## 1. Fetching

**Set A, books.toscrape.com:** a practice site built for scraping, with no robots.txt.

| Measure | Result |
|---|---|
| Pages fetched | 105 of 105 (HTTP 200) |
| Total time | 102.2 s, with at most 2 requests at once and a 1 s pause after each |
| Path used | plain download (Scrapling `Fetcher`) for every page; no stealth needed |

**Set B, scrapingcourse.com challenge pages:** a site of practice pages, whose robots.txt allows these two. Product Hunt was dropped because its Terms of Use forbid scraping.

| Page | Plain download | Stealth browser (CAPTCHA solving off, 10 s wait) |
|---|---|---|
| `/cloudflare-challenge` | 403 on 10 of 10 tries | still "Just a moment..." on 10 of 10 tries, about 12.9 s each |
| `/antibot-challenge` | 403 on 10 of 10 tries | still "Just a moment..." on 10 of 10 tries, about 12.6 s each |

Both pages need Cloudflare's Turnstile challenge solved, and the stealth browser alone doesn't get past it. Under the spec's rules (section 14: `solve_cloudflare=False`, no CAPTCHA solving), the engine marks such pages `blocked: challenge` and stops.

A first run with no wait returned too early. Its 403 status belonged to the challenge page itself, and the fix was to judge by the final page content. Only the corrected run is reported above.

## 2. Brains (llama-server, cached Set A pages, 4,096 tokens per slot)

The task was to fill a 5-field form (title, price, availability, UPC, star rating) from each page's text. The ground truth is a hand-written recipe; three samples were checked by eye against the live site.

| Slots at once | Total time, 105 pages | Pages/s | Time per answer (median / 90th percentile) | Output speed per slot | Peak VRAM |
|---|---|---|---|---|---|
| 1 | 88.8 s | 1.18 | 0.84 s / 0.97 s | 118.2 tok/s | 1,710 MiB |
| 8 | 49.7 s | 2.11 | 3.71 s / 4.75 s | 23.8 tok/s | 2,069 MiB |
| **53** | **39.4 s** | **2.66** | **18.3 s / 25.9 s** | **5.3 tok/s** | **4,426 MiB** |

- **53 slots fit entirely in VRAM:** 4,426 of 6,144 MiB. Windows' shared GPU memory rose by about the same amount (98–180 MiB) in every run, including the 1-slot and 8-slot runs that used little VRAM. That rise comes from other programs, not from the model spilling over.
- **53 brains give 2.25 times the total speed of 1 brain** (2.66 vs 1.18 pages per second). The research had estimated 1.5–2.5 times. Each brain gets much slower: 18.3 s per answer at 53, against 0.84 s alone.
- **The prompts were small:** about 630 tokens on average. Real pages trimmed to 4k tokens would make every run slower, the 53-slot run most of all.

**Accuracy** was the same at every slot count, since all runs used the same model and prompt:

| Field | Correct |
|---|---|
| price, availability, UPC | 100% |
| title | about 70% (examples below) |
| rating | 0%. The star rating exists only as a CSS class (`star-rating Three`), never as page text, so a brain reading text can't see it. |
| All 5 fields | 74% |
| Excluding rating | 92.6% |
| Answers that were not valid JSON | 0 |

How the title errors break down:
- **Mostly series tags dropped:** "Starving Hearts" instead of "Starving Hearts (Triangular Trade Trilogy, #1)".
- **Small case or spacing changes.**
- **Two real mistakes:** a sentence from the book description returned as the title, on "Soumission" and "The Requiem Red". These are the errors a checker brain is meant to catch.

## 3. Recipe path

One brain call wrote a recipe from a sample page in 0.83 s:

`{"title": "h1", "price": "p.price_color", "availability": "p.instock", "upc": "td.UPC", "rating": "i.icon-star"}`

| Measure | Result |
|---|---|
| Time to replay it on all 105 pages | **0.42 s**, with zero AI calls |
| title, price, availability | 100% correct |
| UPC | 0%. `td.UPC` doesn't exist; the model invented it. |
| rating | 0%. It selected the star icon, not the element whose class holds the count. |
| Overall | 60% |

The fields the recipe gets right, it gets right on every page, for almost no time. The fields it gets wrong, it gets wrong on every page. That pattern fits the design: validation flags an empty or invalid field once, and a fixer brain rewrites that selector once. A fixer was not built or measured in this benchmark.

## 4. Point, don't write (2026-10-21, `--point`)

**What changed:**
- Brains read a numbered list of page pieces with their labels kept (`[10] p class=star-rating Three:`), not plain text.
- They fill a fixed form: llama.cpp `json_schema`, with rating limited to 1–5.
- Code then snaps each written value to the page piece holding it and copies that piece exactly.
- Code also turns the pieces the brains used on 5 sample pages into CSS selectors (Scrapling's `generate_css_selector`). The brain never writes CSS.

**Answer formats tried first** (35 pages, 35 brains):

| Format | All fields right |
|---|---|
| Brain answers line numbers, "null" allowed | 39% |
| Line numbers, "null" not allowed | 64% |
| **Brain writes the value, code snaps it to its line** | **96%** |

A 2B brain copies well and counts badly. With "null" allowed, it answered null for every field on 69 of 105 pages.

**All 105 pages, 53 brains** (same model and server settings as section 2):

| Field | Before (section 2) | Brains on every page | Recipe from 5 pointed pages, replayed on all 105 |
|---|---|---|---|
| title | 70% | 98% | **100%** |
| price | 100% | 100% | **100%** |
| availability | 100% | 100% | **100%** |
| UPC | 100% | 100% | **100%** |
| rating | **0%** | 78% | **100%** |
| All fields | 74% | 95% | **100%** |

- **Recipe cost:** 5 brain calls in total, then 0.63 s to replay on all 105 pages with no AI.
- **Recipe rule:** a field gets a recipe when its selector matches the brains' answers on all 5 samples but one.
- **Why the rating recipe needs that rule:** on the 5th sample a brain read another book's stars from the "you might also like" list lower on the page, which is also most of the 22% per-page rating misses. The recipe always reads the main book's spot.
- **Speed:** brains on every page run at 1.6 pages/s, down from 2.66. The fixed form and the longer numbered view (about 1,240 prompt tokens) cost speed. The recipe path makes that matter little: brains run only on 5 pages per kind of page, plus pages whose checks fail.
- **Bug found and fixed while measuring:** the stock number 18 snapped to the price "£44.18". Numbers now snap only as whole numbers.
- **Still one site and one page layout.** The council's first step, a test set from several different sites, is not built yet.

## 5. Harness tuner, phase 1: the scoreboard and free server settings (2026-10-21, `bench/score.py`)

**Test set:** 4 sites, 10 saved pages each, 190 answers (`bench/testset.py`). The sites are books.toscrape, quotes.toscrape author pages, webscraper.io's test shop and 10 Wikipedia book articles. Each brain run asks every page 5 times in one mixed batch, so 200 questions go to 53 brains.

**Scoring rules:**
- Writing "none" when the page shows the answer is an error.
- Writing a value when the page shows nothing is also an error.
- Error bars resample whole pages, with 2,000 draws.
- Two settings are compared item by item: majority right or wrong over the 5 runs, with an exact McNemar test.
- 190 answers can only show differences of about 5 points.

**Answer key check:**
- The first baseline got 12 items wrong in most runs. Each was checked against its saved page, and the key was right on all 12.
- One miss was a harness bug, not a brain or key error. On *Brave New World* the brain wrote "February 1932" correctly, then the snap step copied the page's footnote mark and made it "February 1932 [ 1 ]". Snapping now drops footnote marks.
- That one fix took the baseline from 93.8% to 95.1%. The run from before the fix is kept as `score-base-before-snapfix.json`.

**The A/B tests** (5 runs each, same 190 answers):

| Setting | All sites | books | quotes | webscraper | wikipedia | Gap vs base | Pages/s |
|---|---|---|---|---|---|---|---|
| base: `--reasoning-budget 0`, `-ctxcp 2`, answer form enforced | 95.1% [91.8, 97.8] | 98% | 89% | 96% | 95% | | 2.69 |
| **`-rea off`** | **94.9%** [91.5, 97.8] | 97% | 89% | 96% | 95% | −0.1 pts [−1.0, +0.5], p = 1.0 | **3.03** |
| `-ctxcp 4` | 94.6% [91.1, 97.7] | 96% | 90% | 96% | 94% | −0.4 pts [−1.3, +0.2], p = 1.0 | 2.50 |
| no answer form (code parses the JSON) | 94.6% [91.2, 97.7] | 98% | 89% | 96% | 93% | −0.4 pts [−1.6, +0.6], p = 1.0 | 2.61 |

- **Accuracy:** none of the three changes moves it. Every gap is under half a point and every p is 1.0.
- **Speed is noisy between server starts.** base gave 2.12 and 2.69 pages/s on the same settings. So base and `-rea off` ran 2 more times each, taking turns:

| Head-to-head | base | `-rea off` |
|---|---|---|
| 1 | 2.69 | 3.03 |
| 2 | 2.44 | 2.70 |
| 3 | 2.26 | 2.59 |

- **`-rea off` was faster in 3 of 3, by about 13%, at the same accuracy.** It is now the default in `bench/brains.py` (`FLAGS`). Cause: `--reasoning-budget 0` turns GPU sampling off; `-rea off` keeps it on.
- **`-ctxcp 4` is not needed.** Every setting already reuses about 340 prompt tokens per question from the cache: the shared start of the prompt was never being thrown away at these prompt sizes.
- **The answer form stays.** Dropping it didn't make answers faster here (they are short), and the form guarantees valid JSON.

**What the brains still get wrong** (9 items wrong in most runs, the same in every setting):

| Kind | Items | What happens |
|---|---|---|
| Counting stars | books/00, books/09, webscraper/06, webscraper/08 | Books always draws 5 star icons and names the count in a class ("star-rating Three"); the brain reads the icons. On webscraper it reads 1 star as 5, and 2 stars next to "0 reviews" as 0. |
| Place cut short | quotes/04, quotes/09 | "Paris" for "Paris, France". The line starts "Born: November 22, 1869 in ...", so snapping can't make it whole. |
| Wrong name | quotes/09 | The real name "Theodor Seuss Geisel" from the description instead of the page's "Dr. Seuss"; snapping then copies the whole description sentence. |
| 0 for none | wikipedia/00, wikipedia/04 | No page count on the page; the brain writes 0. |
| Two dates in one | wikipedia/05 | Moby-Dick lists a UK and a US date; the brain writes both. |

These are the starting list for phase 3's fix loop. Fixing them is harness work, with a risk of tuning to these 40 pages, so each fix has to be checked on pages it wasn't made from.

## 6. Harness tuner, phase 3 round 1: the fix loop (2026-10-21)

**Held-out pages:**
- `bench/testset.py --holdout` fetched the next 10 pages of each site, 190 more answers, with the same polite rules. None of them overlaps the test set.
- Fixes were written only from the test set failures. Every run now asks both sets in one batch: 400 questions, 5 runs.

**Two corrections to the held-out answer key, before any fix was scored:**
- "Serialised 1860" counted as a date because any capitalised word was accepted as a month. Real month names only now.
- 3 Wikipedia boxes name the publisher inside the "Published" row: "17 August 1945 (Secker and Warburg, London, England)". The key said "none" there. The brain answered "Secker and Warburg", which was right.
- Neither change touches the test set key.

**The rules, set before scoring:**
- A fix is kept only when, on held-out pages, it makes more items right than wrong. Right or wrong is the majority over 5 runs.
- **Code fixes** change what happens after the brain writes. They are re-scored on the very same brain answers (`--rescore`), so there is no noise.
- **Prompt and view fixes** change what the brain reads, so they need a new brain run. Their net held-out gain must beat the wobble between two runs with identical settings. That wobble was 3 test set items and 1 held-out item.
- **New check, "perfect brain":** the answer key goes in as if a brain wrote it, and anything code spoils is a harness bug. Before this round, code spoiled 5 perfect answers: the snap step stretched "July 1890" into "July 1890 Lippincott's Monthly Magazine". After it, 0.

**The fixes tried** (each compared to the same base; "test set" is where it was made from):

| Fix | Kind | Test set | Held-out | Verdict |
|---|---|---|---|---|
| **date**: a date field holds one date | code | +1, 0 broken | **+5, 0 broken** | **kept** |
| **ground**: a number must be on the page (digits, ×N or a number word); else none | code | +2, 0 broken | **+1, 0 broken** | **kept** |
| **nostyle**: hide `<style>`/`<script>` from the brain (Wikipedia's infobox CSS was being shown, and its "padding:0" hid a made-up 0) | view, bug fix | +1, 0 broken | 0, 1 broken (wobble) | **kept** as a bug fix; 5% shorter Wikipedia prompts |
| tail: finish a cut-short place ("Paris" → "Paris, France") | code | +2, 0 broken | 0, **1 broken** | dropped: it glued a date onto a held-out publisher |
| once: "a piece without ×N appears once" | prompt | +2, 2 broken | +1, 1 broken | dropped: wobble only, the lone stars stayed wrong |
| heading: "take names from headings, not descriptions" | prompt | +2, **6 broken** | 0, **3 broken** | dropped: it made names worse |

**All kept fixes together** (`p3-nostyle-date-ground` against `p3-base`):

| | Before | After | Gap (95% range) | Items fixed / broken |
|---|---|---|---|---|
| Test set | 94.2% | **96.5%** | +2.3 pts [+0.6, +4.4] | 4 / 0 |
| **Held-out** | 94.9% | **97.5%** | **+2.5 pts [+0.3, +4.9]** | 6 / 1 (the 1 is wobble) |

On held-out Wikipedia alone: 83% → 98%. The held-out gain's error bar stays above zero. McNemar p = 0.125: 6 items against 1 is too few for that test.

**Of the 9 items from section 5:**
- 3 are fixed and checked on new pages: both made-up page counts, and Moby-Dick's two dates.
- books/09 is right in this run, but that is wobble.
- 5 are still wrong, and the held-out pages show the same kinds again:

| Still wrong | Test set | Held-out | Why a single-page fix can't do it |
|---|---|---|---|
| Name taken from the description, then stretched to the whole sentence | Dr. Seuss | Elie Wiesel, Jim Henson | The brain writes the real full name; the heading prompt made it worse |
| Star counts | books/00 (reads the 5 icons), webscraper/06 and 08 | webscraper/02 and 04 (a lone star read as 5, now "none" since 5 isn't on the page) | 3 vs 5 are both "on the page" |
| Place cut short | quotes/04, 09 | none | the tail fix broke a held-out publisher |
| "335 + 355" pages | | Little Women | two volumes |

**The next fix is a vote across pages, not a better single page.** On most pages of a site, the brain takes the name from the heading and the stars from the right spot. A recipe built from that majority (section 4: 100% on books) reads the minority pages correctly too. It can be checked the same way: built on test set pages, replayed on held-out pages.

**Speed:** 3.95–4.16 pages/s in these 400-question runs (more questions keep all 53 brains busy). The fixes change it by no more than the wobble.

## 7. Harness tuner, phase 3 round 2: a vote across pages (2026-10-21, `vote` in `bench/score.py`)

**How it works:**
1. On each test set page, take the brains' majority answer over the 5 runs. The answer key is never used.
2. Every page piece that holds that answer suggests a recipe: a CSS selector from Scrapling's `generate_css_selector`, plus a way to read the piece:
   - its text
   - the whole number in it
   - a number word in its class ("star-rating Three")
   - how many identical icons sit together
3. A field gets the recipe that gives back the majority answer on the most test set pages, if that is at least 8 of 10.
4. Wherever a field has a recipe, code reads the value from the recipe instead of the brain. On held-out pages, that is a recipe checked on pages it wasn't made from.

**Self-check, recipes learned from the answer key:**
- 11 of 18 fields get a recipe, and every one reads all 10 held-out pages right.
- No recipe for quotes' date and place (one piece holds both) or for any Wikipedia field (each box puts its rows in a different order). The brain keeps those.

**Result** (the same brain answers as round 1's winner, so the only difference is the vote):

| | Round 1 winner | With the vote | Gap (95% range) | Items fixed / broken |
|---|---|---|---|---|
| Test set (recipes made here) | 96.5% | 98.6% | +2.1 pts [+0.5, +4.3] | 4 / 0 |
| **Held-out** | 97.5% | **99.4%** | **+1.9 pts [+0.3, +4.0]** | **4 / 0** |

The four held-out items fixed:
- the Elie Wiesel and Jim Henson names, read from the page heading instead of a description sentence
- two lone stars that the brain read as 5

On the test set it also fixed Dr. Seuss, the books star count read from the 5 icons, and both webscraper star counts.

- **Stable:** recipes learned from a different brain run (`p3-base`) are identical, and they give held-out +3 fixed, 0 broken.
- **Coverage:** books and webscraper get a recipe for every field, so their new pages need no brain call at all. Quotes needs the brain for 2 fields and Wikipedia for all 6.

**Phase 3 so far**, from the start of round 1 to now (`p3-base` → `p3-r2-vote`):

| | Before | After | Fixed / broken | McNemar p |
|---|---|---|---|---|
| Test set | 94.2% | 98.6% | 8 / 0 | 0.008 |
| **Held-out** | 94.9% | **99.4%** | **9 / 0** | **0.004** |

**Still wrong in most runs, 3 items:**
- quotes/04 and quotes/09 birthplaces are cut short ("Paris" for "Paris, France"). The tail fix that finished them broke a held-out publisher.
- Little Women's "335 + 355" pages.

These 80 pages come from 4 sites with fixed layouts, and the recipes are positional. A site whose layout changes from page to page gets no recipe, like Wikipedia, and falls back to the brain.

## 8. The page reader moves into Errand (2026-10-21, `errand/extract.py`)

**What moved:**
- The numbered view, the answer form and prompt, and the snap step.
- Round 1's fixes, now always on: one date per date field, numbers must be on the page, style and script hidden.
- The vote across pages (`learn_recipe`, `replay`).
- `read_pages`: the flow for one kind of page. Brains read sample pages, a recipe is learned from their answers, and code reads every page. A brain reads only the fields no recipe covers, and a recipe can be kept and reused for later pages of that kind.

`bench/brains.py` and `bench/score.py` now call this code, so the scoreboard measures the engine itself.

**Check that nothing changed:**
- All 13 saved phase 3 runs give the same answers through the engine as before, except one.
- The engine also reads date fields from recipes. So Dr. Seuss's birth date now comes from "Born: March 02, 1904 in ..." instead of his description's "2 March 1904", which is right now.

**Tests:**
- `tests/test_extract.py` has 9 tests on made-up pages with a fake brain, with no model and no network.
- Each fix was broken on purpose once, to make sure a test catches it.
- Whole suite: 48 passed.

**A fresh third set:**
- `bench/testset.py --set fresh` fetched the next 10 pages per site: 40 pages, 190 answers. The key was spot-checked against every Wikipedia box.
- It is used only to check the engine. One new brain run (`p3-engine-run`, 5 runs) asked all three sets.

**Two engine bugs, found by measuring and fixed:**
1. **Agreeing on missing values.** With 5 sample pages, a held-out Wikipedia "pages" recipe was accepted on one real example. Its selector used an id that exists on one page only, so it found nothing on the others, and "nothing" agreed with the 3 pages where the brain said none. A recipe must now read a real value right on at least 3 samples, and on 4 of every 5 samples that show one. This took held-out from 95.7% to 98.3% (5 fixed, 0 broken). The held-out pages found this bug, so they can't also prove the fix, but it has its own tests.
2. **Too few samples.** On fresh pages, 5 Wikipedia boxes happened to share a row order, the recipe trusted it, and the next pages broke. Learning once from 10 pages and reusing the recipe gives Wikipedia no recipe in any of the 5 runs, and breaks nothing. `read_pages` now takes 10 samples by default.

**The engine on all three sets** (same brain answers in every column):

| | Brains only | 5 samples per set | **Learned once on 10 pages, reused** |
|---|---|---|---|
| Test set | 96.3% | 98.5% (4 fixed / 0 broken) | **98.5%** (4 / 0) |
| Held-out | 97.8% | 98.3% (1 / 0) | **99.4%** (3 / 0) |
| **Fresh** (never used for any choice) | 94.1% | 90.4% (1 / **8**) | **97.3%** (6 / 0, p = 0.03) |
| Brain calls on new pages | 200 of 200 | 175 of 200 | **100 of 200** |

- With the recipe learned once, books and webscraper pages need no brain at all.
- The same recipes came out of all 5 brain runs.
- The fresh result equals round 2's vote, which used the 5-run majority: one run per page is enough.

**Seen but not looked into:** this 600-question run reused far fewer cached prompt tokens than the 400-question runs (62 vs 482 a question) and ran at 2.38 pages/s instead of about 4. Accuracy is not affected.

## 9. The real job loop (2026-10-21, `errand/engine.py`, `errand/fetch.py`, `errand/brains.py`)

`python -m errand start` now runs real jobs; `--demo` keeps the fake agents. A job is links plus fields. Claude in the room starts it through the connector's `start_job(prompt, urls, fields)`.

**How a job runs:**
- **The agents:** 53 agents share one task list. An agent takes the first task it can do now, and never waits in line.
- **Fetching:** robots.txt is obeyed, and reading it counts as that site's request. Requests go one at a time per site, with a 2–3 s pause, under an honest name. A 429 gets a 60/120/240 s back-off. Bot checks and login pages stop that page; Errand never solves or logs in. Links to this laptop or a private network are refused.
- **Reading:** brains read the first 10 pages of each kind of page (same site and path depth), and the vote learns a recipe from their answers. Code reads the rest, with a brain only for fields no recipe covers.
- **Brains:** llama-server starts with the first job, with the measured settings, and stops with Errand.
- **Results:** results go to `jobs/<job>.csv`, one row per link with its status, and an earlier job's file is never overwritten.
- **The room:** the room and connector show real numbers: pages fetched, pages read by code, recipes, brain calls.

**Live check:** 20 real pages from books.toscrape.com, fields title, price, stock, rating and UPC, no `focus` given:

| Run | Fields right | Brain calls | Read by code | Time |
|---|---|---|---|---|
| First | 80 / 100: every title came back as "In Her Wake \| Books to Scrape - Sandbox" | 10 | 10 | about 75 s |
| **After the fix** | **100 / 100** | 10 | 10 | 78 s (the polite pace: 20 pages × 2–3 s) |

**What went wrong in the first run:**
- With no `focus`, the page view included `<head>`. The tab title starts with the book's name, so the snap copied it, and the recipe learned that spot.
- The view is now the page's `<body>` when no focus is given, with a test. The bench always passes a focus, so its results don't change.

**Tests:** `tests/test_engine.py` has 7 tests against a fake website served on this laptop, with real HTTP and a fake brain. They cover:
- robots.txt, and the one-at-a-time pace with pauses
- the 429 back-off
- bot check and login pages
- refused links
- results never overwritten
- no brains: the job still ends, with a reason
- pause
- the API and the connector

The whole suite: 56 tests.

**Not built yet:**
- the stealth and JavaScript browser steps (such pages end as blocked)
- browser windows and hand-offs
- checker brains
- real huddles
- a raw-page cache on disk
- live tiles of what each brain writes

Idle agents show "picking up the next task" while a site pauses.

## 10. Browser windows and the fetch ladder (2026-10-21, `errand/browser.py`)

**What was built:**
- **Windows:** one headless Chromium holds up to 25 private windows, shared by the 53 agents. Every page gets a fresh window that is closed (wiped) afterwards. No new window opens while free RAM is under 2 GB. A page that hasn't loaded in 30 s is given up.
- **JavaScript step:** a plain download that is only an app shell goes to a window. "App shell" means under 100 visible characters, an app root with little text, or far more text inside the page's scripts than on the page.
- **Stealth step:** a download that was refused (403 or a bot-check page) gets one try in Scrapling's stealth browser, with CAPTCHA solving off. A bot check that is still there ends as `blocked: bot check`.
- **Shelf and hand-offs:** with every window busy, browser pages wait while agents take other work. An agent finishing in a window hands it straight to the next waiting page whose site is free.
- **In the room:** the desks show windows in use and pages waiting, and an agent working in a window shows the window's latest picture (640×400 JPEG).

**Live check:** 6 pages of quotes.toscrape.com/js, a practice site that builds its quotes with JavaScript. Fields: the first quote and its author.

| Run | Quotes right | Authors right | What was wrong |
|---|---|---|---|
| First | 1 / 6 | 1 / 6 | Only page 1 went to a window. Page 3's links gave it 104 visible characters, just over the old 100-character rule, so its empty shell went to the brains. The vote then learned the page header as "the quote". |
| Second | 4 / 6, two cut short | 4 / 6 | The view shortens long lines, and snapping didn't copy them back whole, because the page wraps quotes in “ ” and the brain's answer had no quote marks. |
| **Third** | **6 / 6, whole** | **4 / 6** | Two brain slips: page 3's author is from another quote, and page 5's is "Jojen", a name inside the quote. |

**Fixes, each with a test:**
- **App shell rule:** the scripts-hold-more-text-than-the-page test catches every one of the 6 pages. It flags 0 of 141 real saved pages from the bench.
- **Snapping:** it ignores the quote marks around a quotation.
- **The number check:** it accepts numbers written with separators ("1,036", "1.036", "1 036"). The perfect-brain check found this on the fresh set: two correct page counts were being thrown away. With it fixed, the engine flow on fresh pages (section 8) goes from 97.3% to **98.3%**, with test set and held-out unchanged. This uses the answer key only to find code that spoils correct answers.

**Tests:** `tests/test_browser.py` runs real Chromium on two fake sites, with one window between them: never more than 1 open, at least one hand-off, a JPEG picture taken. The stealth step is stood in for, so no stealth browser starts. The whole suite: 69 tests.

**Not done yet:** a checker for brain slips like the two authors above, which is piece 5.

## 11. Checker brains (measured, dropped) and real huddles (2026-10-21)

**The checker idea, measured before building** (`bench/score.py --check p3-engine-run`):
- A second brain judged every answer "right" or "wrong", using the spec's own checker role with a different prompt.
- The fields it called wrong were re-read alone. That is the spec's 2-of-3 vote: the re-read wins when it differs.
- It ran on all three sets with the same saved answers, 950 answers per set over 5 runs.

| Set | Wrong answers | Checker said "wrong" | Of those, really wrong | After re-reading |
|---|---|---|---|---|
| Test set | 35 | 349 | 30 | 17 fixed, **43 broken** |
| Held-out | 21 | 324 | 15 | 0 fixed, **43 broken** |
| Fresh | 46 | 343 | 41 | 7 fixed, **23 broken** |

- **Dropped:** it does find most real mistakes, but it calls about a third of all answers wrong, nearly all of them correct, and re-reading those breaks good answers on every set. The engine has no checker.
- **The vote across pages stays the main guard against slips.** The checker code lives only in the bench, to re-run the test.

**Real huddles** (`errand/engine.py`), for a recipe that stops working in the middle of a job, like a site redesign:
1. **Noticing:** a page "breaks" when a field the recipe reads comes back empty while 4 in 5 samples had it.
2. **Raising:** after 3 broken pages, a problem goes on the board. That kind's new pages wait; agents keep working on everything else.
3. **Rounds:** 3 agents re-read 3 broken pages with their brains, and the vote learns a recipe from just those. If it doesn't read every broken field, 9 agents try, then everyone. A round waits while more pages of that kind are still being fetched.
4. **Fixed:** the new recipe replaces the old one and is saved, and every broken and waiting page is read again.
5. **Not fixed:** one agent waits on you. Approve, and brains read those fields page by page. Skip, and that kind's pages are marked "skipped by you", including the ones the broken recipe already read.
6. **Where it shows:** the room's huddle screens and the connector's `list_problems` and `problem_detail` show the rounds.

**Tests** (`tests/test_huddle.py`), on a fake site that changes layout halfway through 24 pages:
- One wrapper added: fixed in round 1, with all 24 rows right.
- A different nesting on every page: no round fixes it, so it goes to you, and approving gives all rows right.
- Skipping ends the job.
- A round waiting for pages that then fail to download still ends.

The whole suite: 73 tests.

**Not built:** a 2B retry for empty fields on private jobs, where Gemini is off. The bench's remaining mistakes are wrong values, not empty ones, so it would rarely run.

## 12. Safe clicking, record and replay, skills (2026-10-21, `errand/clicks.py`)

**How it works:**
- **Steps:** a job can carry steps to do before reading, like `["click the 256 option"]`. Every page then opens in a browser window.
- **Safety:** only same-site links, option and tab buttons, radios and checkboxes are offered to the brain. Never buy, cart, sign up, log in or out, submit, send, delete, download, accept, anything disabled, anything in a form that would send it, or links to other sites.
- **Picking:** the brain writes the name of what to click, and code finds the one element with that name. Same-named elements count only if they go to the same place.
- **Checking:** after the click, the page's text or address must change, and it must still be the same site.
- **Record and replay:** a click that worked is saved for that kind of page (`errand/store.py`, table `clicks`). Later pages and later jobs replay it by the same name with no brain. Replays never use "the same spot": that could press a different option and read the wrong price.
- **Skills:** a job's fields and steps saved under a name, with `{blanks}` filled in when it runs (connector: `save_skill`, `run_skill`, `list_skills`).

**Live on webscraper.io's test shop** (5 laptops, step "click the 256 option", read the price):

| Run | Result |
|---|---|
| First | 0 / 5. The 2B copied the menu line "256 (button)", label included, so nothing matched. |
| **Fixed** | **5 / 5**: every price exactly $20 above its 128 GB default, the same as the research measured by hand ($295.99 → $315.99). The brain chose once, then 4 clicks replayed with no AI. |

The fix: the menu shows names only, and a copied "(…)" label at the end is ignored.

**Tests** (`tests/test_clicks.py`, real Chromium, fake shop):
- The safety rules.
- One brain choice, then 5 replays, with the next job reusing the saved click.
- "Buy now", "Register" and a disabled option are never offered, and the shop never received a buy request.
- A do-nothing button fails the step.
- Skills fill their blanks.

The whole suite: 77 tests.

**Not built:** clicks on logged-in pages (Errand never logs in), and typing into search boxes (a form). Both were left out on purpose by the council's navigation-only rule.

## Against rtrvr's demo

rtrvr's "53 agents" demo extracted 8 fields from 105 Product Hunt pages in 184 s on 53 cloud browsers. Here:
- 53 brains on one laptop filled 5 fields on 105 pages in **39.4 s**, from pages already downloaded.
- Downloading those pages politely took 102 s.
- The recipe path replayed in 0.42 s.

These were smaller, easier, static pages, so it isn't the same test. It shows the free laptop setup can handle a job of that size in about the same time or less. It does not show it beats rtrvr on rtrvr's own pages.

## Commands

```
python -X utf8 bench/fetch.py
python -X utf8 bench/fetch.py --b-only
python -X utf8 bench/brains.py --np 53
python -X utf8 bench/brains.py --np 53 --point
python -X utf8 bench/brains.py --np 8
python -X utf8 bench/brains.py --np 1 --recipe
python -X utf8 bench/brains.py --np 1
python -X utf8 bench/testset.py
python -X utf8 bench/score.py --variant base --runs 5
python -X utf8 bench/score.py --compare base rea-off
python -X utf8 bench/testset.py --holdout --fetch
python -X utf8 bench/score.py --perfect-brain
python -X utf8 bench/score.py --variant p3-nostyle --runs 5
python -X utf8 bench/score.py --rescore p3-nostyle p3-nostyle-date-ground
python -X utf8 bench/score.py --compare p3-base p3-nostyle-date-ground
python -X utf8 bench/score.py --rescore p3-nostyle p3-r2-vote
python -X utf8 bench/score.py --compare p3-nostyle-date-ground p3-r2-vote
python -m pytest tests/test_extract.py
python -X utf8 bench/testset.py --set fresh --fetch
python -X utf8 bench/score.py --variant p3-engine-run --runs 5
python -X utf8 -c "import sys; sys.path.insert(0, 'bench'); import score; score.engine('p3-engine-run', 'engine-learn10', samples=10, learn_on='testset')"
python -X utf8 bench/score.py --compare p3-engine-run engine-learn10
```

The server command is recorded in each `bench/brains-*.json` (`server_cmd`).

## Not measured

- pages larger than about 630 tokens
- JavaScript-heavy pages
- the checker, fixer and voting roles
- the live 53-tile screen
- a visible (non-headless) stealth browser on Set B
