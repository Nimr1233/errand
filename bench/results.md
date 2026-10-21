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
```

The server command is recorded in each `bench/brains-*.json` (`server_cmd`).

## Not measured

- pages larger than about 630 tokens
- JavaScript-heavy pages
- the checker, fixer and voting roles
- the live 53-tile screen
- a visible (non-headless) stealth browser on Set B
