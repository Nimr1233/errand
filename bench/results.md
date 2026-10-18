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
python -X utf8 bench/brains.py --np 8
python -X utf8 bench/brains.py --np 1 --recipe
python -X utf8 bench/brains.py --np 1
```

The server command is recorded in each `bench/brains-*.json` (`server_cmd`).

## Not measured

- pages larger than about 630 tokens
- JavaScript-heavy pages
- the checker, fixer and voting roles
- the live 53-tile screen
- a visible (non-headless) stealth browser on Set B
