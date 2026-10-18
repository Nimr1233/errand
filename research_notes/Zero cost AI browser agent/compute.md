# Zero-cost compute and techniques for 1,000-site jobs and many parallel browser workers (as of 2026-10-18)

Context from the assignment (not re-verified here): reverse engineering showed rtrvr.ai caps in-browser parallelism at 20 tabs and runs its "1,000 sites" jobs on its own cloud in batches of 10 URLs with 4 in flight (about 40 concurrent). The aim is to match "1,000 sites, one prompt" and "53 agents at once" for $0.

Dating convention: "fetched 2026-10-18" means I read the official page on that date. Other dates are the source's own publication or "last updated" date.

## Q1. Free cloud machines that can run headless Chrome/Playwright workers: real limits, credit card, trial vs always-free, scraping terms

### Takeaway
As of October 2026 the only free option with real parallel capacity and no credit card is GitHub Actions on a public repo: 20 concurrent jobs, each a 4 vCPU / 16 GB Linux runner. Its terms ban hosted-runner use "unrelated to" the software project, so a scraping fleet is a ToS risk. Oracle Always Free has been halved to 2 OCPU / 12 GB and needs a card. Hugging Face Spaces no longer allows free Docker or Gradio compute. Cloudflare's free Browser Rendering gives 10 minutes a day. The AWS, Azure and GCP offers that give real VMs are card-gated trials or tiny 1 GB VMs.

### Cited Findings

**GitHub Actions (fetched 2026-10-18)**
- Usage is free on public repos: "GitHub Actions usage is free for self-hosted runners and for public repositories that use standard GitHub-hosted runners." Larger runners are always billed, even on public repos. — [GitHub Docs: Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- Private repos get 2,000 minutes a month on GitHub Free and 3,000 on Pro. Linux 2-core x64 costs $0.006/min after that, and Windows 2-core costs $0.010/min. — [GitHub Docs: Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- Concurrency limits for standard hosted runners: Free 20, Pro 40, Team 60, Enterprise 500. A job can run at most 6 hours. A matrix can have at most 256 jobs per workflow run. — [GitHub Docs: Actions limits](https://docs.github.com/en/actions/reference/limits)
- Public repo runners are 4 CPU / 16 GB RAM / 14 GB SSD on x64 (ubuntu-latest, 24.04, 22.04, 26.04). arm64 runners (ubuntu-24.04-arm and others) have the same spec. Private repo runners are 2 CPU / 8 GB. — [GitHub Docs: GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- Banned uses for all Actions: cryptomining, unauthorized access, reselling Actions as a service, "Any activity that places a burden on our servers, where that burden is disproportionate to the benefits provided to users", and using Actions "as a content delivery network or as part of a serverless application". Hosted runners carry an extra ban: "any other activity unrelated to the production, testing, deployment, or publication of the software project". Web scraping is not named. — [GitHub Terms for Additional Products and Features](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)
- Simon Willison's "Git scraping" pattern (2020) is a widely known example of scheduled Actions workflows that fetch data and commit it. His post doesn't discuss GitHub's terms or limits. — [Simon Willison, Git scraping](https://simonwillison.net/2020/Oct/9/git-scraping/)
- No credit card is needed. A GitHub account is enough for public-repo use. (Inferred from the billing page saying public-repo usage is free; there is no explicit "no card" statement.)

**Oracle Cloud Always Free (docs fetched 2026-10-18)**
- Ampere A1 now gives "the first 1,500 OCPU hours and 9,000 GB hours per month for free", which the docs call "equivalent to 2 OCPUs and 12 GB of memory" (one instance, or two 1-OCPU instances). Instances must be created in the home region. — [Oracle Docs: Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- The allowance used to be 4 OCPU / 24 GB (3,000 OCPU-hours / 18,000 GB-hours). Oracle edited the docs without notice, and the author spotted the change in late June 2026 (article dated 2026-06-26). The console banner still showed "4 OCPUs and 24 GB" at that point. Enforcement dates are unconfirmed. Once enforced, Always Free instances above the limit are shut down until resized. — [terminalbytes, 2026-06-26](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026/)
- Other sources conflict on the effective date, giving June 15, 2026 or August 18, 2026 for enforcement or termination. — [cnelecar](https://www.cnelecar.com/blog/oracle-always-free-arm-limits-cut-2026/); [LinuxToday](https://www.linuxtoday.com/blog/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/); [mrplanb](https://www.mrplanb.com/datacenter/free-vps-tiers)
- AMD micro: up to two VM.Standard.E2.1.Micro instances, each with 1/8 OCPU, 1 GB RAM and 50 Mbps internet bandwidth. Outbound data allowance is 10 TB/month. Block storage is 200 GB total. — [Oracle Docs: Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- Idle reclamation: an instance can be reclaimed if over 7 days its 95th-percentile CPU, network, and (on A1) memory are all below 20%. "Out of host capacity" errors are common for free shapes. — [Oracle Docs: Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- A card is required for verification. Oracle places a temporary hold and doesn't charge unless you upgrade. A 2019 Oracle blog exempted only "recognized Oracle users". An HN commenter reports that sign-up without a payment method isn't possible and that virtual or prepaid cards are rejected (anecdotal). — [Oracle sign-up docs](https://docs.cloud.oracle.com/iaas/Content/GSG/Tasks/signingup_topic-Sign_Up_for_Free_Oracle_Cloud_Promotion.htm); [HN comment](https://hn.svelte.dev/item/49183750)

**Google Cloud (fetched 2026-10-18)**
- Free Tier gives 1 non-preemptible e2-micro VM a month in us-west1, us-central1 or us-east1, 30 GB-months of standard persistent disk, and 1 GB of egress from North America a month. The trial is 90 days with $300 credit. "A Google Cloud billing account is required", and a credit card or other payment method is needed. Crypto mining is banned during the trial. — [Google Cloud Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)
- Cloud Run always-free: 2M requests, 180,000 vCPU-seconds and 360,000 GB-seconds a month. A card is required (checked 2026-09-16). — [flaviocopes free-tier comparison, checked 2026-09-16](https://flaviocopes.com/hosting-free-tiers/)

**AWS**
- Accounts created on or after July 15, 2025 get up to $200 in credits ($100 at sign-up plus $100 from activities). The Free plan ends after 6 months or when credits run out, whichever is first. Older accounts stay on the legacy 12-month program. — [AWS What's New, 2025-07](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/)
- A payment method is required at sign-up. Lambda stays always-free at 1M requests and 400,000 GB-s (checked 2026-09-16). — [flaviocopes, 2026-09-16](https://flaviocopes.com/hosting-free-tiers/)

**Azure**
- $200 of credit for 30 days. The 12-month free services include 750 hours each of B1s, B2pts v2 (Arm) and B2ats v2 (AMD) burstable VMs. There is a temporary $1 card authorization. — [Azure free VMs page](https://azure.microsoft.com/en-us/free/virtual-machines)
- Sign-up needs a phone number and a credit or non-prepaid debit card. App Service F1 gives 60 CPU-minutes a day (checked 2026-09-16). — [flaviocopes, 2026-09-16](https://flaviocopes.com/hosting-free-tiers/)

**Cloudflare Browser Rendering ("Browser Run")**
- Workers Free: 10 minutes of browser time a day (429 errors until the next UTC day after that), 3 concurrent browsers, one new browser every 20 seconds, 60-second idle timeout (extendable to 20 minutes with keep_alive), and one Quick Actions request every 10 seconds. Paid defaults: 200 concurrent and 3 new browsers per second. Limits page last updated 2026-10-14. — [Cloudflare Browser Rendering limits](https://developers.cloudflare.com/browser-rendering/limits/)
- Workers Paid pricing: 10 browser-hours a month included, then $0.09/hour, plus 10 concurrent browsers included, then $2/browser. Pricing page last updated 2026-04-21. — [Cloudflare Browser Rendering pricing](https://developers.cloudflare.com/browser-rendering/platform/pricing/)

**Hugging Face Spaces (fetched 2026-10-18)**
- "Static Spaces are free for everyone. Gradio and Docker Spaces run on compute and require a paid plan to create: PRO for personal accounts, Team or Enterprise for organizations." Free accounts can still host up to 2 ZeroGPU Gradio Spaces. CPU Basic is 2 vCPU / 16 GB with no hourly cost but now needs a paid plan to create. Free hardware sleeps when unused. Outbound traffic is limited to ports 80, 443 and 8080. — [HF Spaces overview](https://huggingface.co/docs/hub/en/spaces-overview)

**Google Colab (fetched 2026-10-18)**
- Free notebooks run "for at most 12 hours", and limits are unpublished and fluctuate. Banned on all managed runtimes: "connecting to remote proxies", "using multiple accounts to work around access or resource usage restrictions", web-service offerings, and more. Free runtimes also ban "remote control such as SSH shells", "bypassing the notebook UI to interact primarily via a web UI", and "running distributed computing workers". Scraping and crawling are not named. — [Colab FAQ](https://research.google.com/colaboratory/faq.html)

**Kaggle**
- Only third-party figures were found: 12-hour sessions, about 30 GPU-hours a week, and a recent bump to 4 CPU / about 29 GB RAM on GPU notebooks (older sources say 2 CPU / 13 GB). Not verified against Kaggle docs. — [lilys.ai note](https://lilys.ai/en/notes/google-tpu-20251128/free-kaggle-gpu-29gb-4-cpu-update); [kgz on PyPI](https://pypi.org/p/kgz)

**Render, Railway, Fly.io (checked 2026-09-16)**
- Render: 512 MB RAM and under one CPU per web service, 750 instance-hours a month per workspace, spin-down after 15 idle minutes, 5 GB bandwidth, no card to start. The docs say not to use it for production. — [flaviocopes, 2026-09-16](https://flaviocopes.com/hosting-free-tiers/)
- Railway: a 30-day trial with $5 credit, then $1 a month covering 0.5 GB / 1 vCPU per service. No card to start once GitHub is verified. A separate source claims a mandatory card from March 2026, so sources conflict. — [flaviocopes](https://flaviocopes.com/hosting-free-tiers/); [Render article citing Railway changes](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026)
- Fly.io: no free allowance. The trial is 7 days or 2 machine-hours, and a card is required for every org. — [flaviocopes](https://flaviocopes.com/hosting-free-tiers/)

### Inferences
- Ranking for parallel browser workers at $0 with no card:
  1. The user's own laptop.
  2. GitHub Actions on a public repo: up to 20 jobs × 4 vCPU / 16 GB = 80 vCPU / 320 GB in aggregate, 6-hour job cap, with ToS risk.
  3. Colab free: one 12-hour notebook, and fleet use is explicitly banned.
  Everything else is either card-gated (Oracle, GCP, AWS, Azure, Fly) or too small for Chromium (Render 512 MB, Railway 0.5 GB, GCP e2-micro, Oracle AMD micro 1 GB, Cloudflare free at 10 min/day).
- The cleanest way to reach "53 agents at once" for free is a GitHub Actions matrix of 6–20 jobs with a few browser contexts each. But the hosted-runner rule against activity "unrelated to the production, testing, deployment, or publication of the software project" makes a general scraping service on Actions a clear ToS risk, and the "serverless application" ban covers using Actions as an on-demand backend. Recommend it only for testing the project, or for small Git-scraping-style public-data jobs. It is not a production backend.
- Oracle's current 2 OCPU / 12 GB fits roughly 5–10 concurrent browser pages (see Q2). The "4 OCPU / 24 GB" figure in the assignment is out of date as of mid-2026. Oracle also needs a card, which breaks the "ideally no credit card" goal.
- Cloudflare free math: at 10 browser-minutes a day and about 3–6 seconds per page, that is roughly 100–200 page loads a day. 1,000 pages would take 5–10 days. That only works as an occasional fallback for JS-heavy pages.
- Datacenter IPs from GitHub, Oracle and Google are more likely to be flagged by anti-bot systems than a home IP (see Q4). Free cloud adds parallelism but can lower success rates.

### Gaps
- No primary Oracle announcement gives the effective date of the A1 cut. Only the docs wording and secondary reports exist.
- I didn't check the acceptable-use policies of Oracle, GCP, AWS or Azure for scraping-specific clauses. The general pattern is bans on unauthorized access and abuse, but I didn't verify it.
- Official Kaggle limits, and whether internet-enabled notebooks still need phone verification, weren't verified.
- I didn't find whether Cloudflare Workers Free needs a card. It is widely believed not to, but I didn't verify that.
- The exact RAM of the GCP e2-micro (commonly 1 GB) and the Azure B1s (commonly 1 vCPU / 1 GB) wasn't confirmed this session.

## Q2. How many headless Chromium instances realistically fit on a 16 GB / 6-core Windows 11 laptop and on a 24 GB / 4-core ARM VM?

### Takeaway
No rigorous public benchmark exists. The numbers I found are rules of thumb: about 50–150 MB for a cold headless browser process, 150–500 MB per active tab or session, and up to about 2 GB for heavy SPAs. A practical ceiling is about 10–20 concurrent pages on the 16 GB / 6-core laptop, which matches rtrvr's 20-tab cap. A 24 GB / 4-core ARM VM fits about 10–20 pages and is CPU-bound, and Oracle's current 12 GB / 2 OCPU fits about 5–10. Use one browser with many contexts, not many browser instances.

### Cited Findings
- Measured peak total memory (Python driver plus browser) after loading example.com and idling 5 seconds: headless Chromium 706 MB, "minimal" Chromium 690 MB, headed Chromium 1,094 MB, headless Firefox 826 MB, WebKit 588 MB (June 2025). It doesn't break out per-page cost. — [datawookie, Playwright Browser Footprint, 2025-06](https://datawookie.dev/blog/2025/06/playwright-browser-footprint/)
- Rules of thumb: about 1 GB per Chromium instance, 4 GB recommended for 2+ concurrent browsers, 200–800 MB per instance when active, 500–2,000 MB for complex SPAs, 50–150 MB to cold-boot, 150–300 MB per tab, and 300–500 MB per concurrent session (vendor). These come from undated guides and vendor pages, not reproducible benchmarks. — [webscraping.ai resource requirements](https://webscraping.ai/faq/headless-chromium/what-are-the-resource-requirements-for-running-headless-chromium-at-scale); [use-apify VPS guide](https://use-apify.com/blog/run-playwright-scrapers-vps); [Railway browserless template](https://railway.com/deploy/browserless-headless-chrome)
- Contexts are recommended over instance-per-session because each new instance duplicates per-process overhead. — [DEV: contexts vs instances](https://dev.to/deepak_mishra_35863517037/scaling-headless-browsers-managing-contexts-vs-instances-1d73)
- One third-party estimate for Crawlee: 200–500 MB base plus 50–150 MB per concurrent browser. Not official. — [webscraping.ai Crawlee memory FAQ](https://webscraping.ai/faq/crawlee/how-much-memory-does-crawlee-use-for-large-scale-scraping)
- Crawlee autoscales concurrency to the available CPU and memory. Its docs warn that setting minConcurrency too high relative to memory and CPU makes the crawler "run extremely slow or crash". — [Crawlee BrowserCrawlerOptions](https://crawlee.dev/api/browser-crawler/interface/BrowserCrawlerOptions)
- Crawl4AI's default MemoryAdaptiveDispatcher stops starting new sessions above 90% system memory, with max_session_permit 10 and check_interval 1.0 s. SemaphoreDispatcher defaults to 20 sessions. — [Crawl4AI multi-URL crawling docs](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
- A GitHub public-repo runner is 4 vCPU / 16 GB on both x64 and arm64. — [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

### Inferences
- 16 GB / 6-core Windows 11 laptop: assume 4–6 GB for Windows and apps, leaving about 10 GB. At 250–500 MB per active page, that is about 20–40 pages by memory. CPU is the tighter limit, since JS-heavy pages need about 0.3–0.5 core while loading, so expect about 12–20 concurrent pages before latency degrades. That puts rtrvr's 20-tab cap near the practical ceiling, not an arbitrary product limit. Blocking images, fonts and media and closing pages promptly can push it toward 30.
- 24 GB / 4-core ARM VM (the old Oracle shape): memory allows about 40 pages but 4 cores limit it to about 10–20. The current Oracle 2 OCPU / 12 GB allows about 5–10. A GitHub runner (4 vCPU / 16 GB) fits about 8–15 each, so 20 parallel jobs give about 160–300 concurrent pages in aggregate.
- "53 agents at once" is almost certainly 53 lightweight contexts or tabs, or 53 logical tasks with most of them waiting on LLM calls, not 53 full Chromium processes on one machine. A laptop can hold 53 mostly idle contexts if only about 10–20 render at once. The real bottleneck is LLM rate limits, which belong to another researcher's scope.
- HTTP-only fetching (no browser) costs a few MB per concurrent request, so 100+ concurrent fetches fit easily on the same laptop. Route to a browser only when a page needs JS (see Q4).

### Gaps
- I found no controlled benchmark of per-context or per-tab memory under Playwright, and none of chromium-headless-shell versus full Chromium on Windows. The user should measure total RSS across all Chromium child processes on their own target sites.
- I found no ARM-specific (Ampere) numbers for Chromium memory or CPU per page.
- I didn't verify the default share of system memory Crawlee uses for autoscaling (commonly cited as 25%).

## Q3. Taking the LLM out of the per-page loop (extractor-once-then-replay, JSON-LD, __NEXT_DATA__, site APIs, sitemaps): how well it works and which open-source tools do it

### Takeaway
"Generate selectors once with an LLM, replay without one" is a documented, first-class feature in Crawl4AI, and the research literature supports it (AutoCrawler 2024, XPath Agent 2025). Scrapling (adaptive relocation), AutoScraper (learn from examples) and ScrapeGraphAI (ScriptCreatorGraph emits a BeautifulSoup function) offer related approaches. The catch is that it amortizes per site template. 1,000 pages on a few templates cost about 0 tokens, but 1,000 different sites still need about 1 small LLM call per site unless generic extractors (JSON-LD, Next.js hydration data, metadata) cover them, and about half of crawled pages carry structured data.

### Cited Findings
- Crawl4AI's `JsonCssExtractionStrategy.generate_schema` and `JsonXPathExtractionStrategy.generate_schema` take sample HTML or a URL plus a natural-language query and return a schema. The docs call this "a one-time cost" that "can be reused for unlimited extractions without further LLM calls". Validation is on by default and refines selectors that return nothing. Multiple labeled samples push the LLM toward stable selectors over positional ones. A TokenUsage object tracks cost because generation "may make multiple LLM calls internally". The docs claim "LLM-based extraction can be 10–1000x slower for large-scale crawling" and that schema extraction is "near-instant". RegexExtractionStrategy can also have an LLM write a pattern once and cache it. Docs v0.9.x, page last updated 2025-05-02. — [Crawl4AI no-LLM strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
- AutoCrawler (arXiv 2404.12753, April 2024) defines a "crawler generation" task for vertical pages, where an LLM produces reusable rules or action sequences. The authors argue that per-page generative agents have "insufficient reusability". It uses a progressive top-down / step-back HTML-pruning framework. Code: github.com/EZ-hwh/AutoCrawler. — [AutoCrawler paper](https://arxiv.org/html/2404.12753v1)
- XPath Agent (arXiv 2502.15688, February 2025) has a weaker LLM extract the targets and a stronger LLM write XPath from a few sampled pages. On the SWDE dataset it reports better F1 than AutoCrawler while "significantly reducing token usage". — [XPath Agent paper](https://arxiv.org/pdf/2502.15688)
- Scrapling's adaptive mode: `auto_save=True` stores a fingerprint of the matched element (tag, attributes, parent and child context, nearby text, DOM position) in local SQLite. After a redesign, `adaptive=True` returns the most similar element on the new page. The exact API varies between versions. — [ScrapingBee on Scrapling](https://www.scrapingbee.com/blog/scrapling-adaptive-python-web-scraping/); [Apify SDK Scrapling guide](https://docs.apify.com/sdk/python/docs/guides/scrapling); [Better Stack guide](https://betterstack.com/community/guides/scaling-python/scrapling-adaptive/)
- AutoScraper: `build(url, wanted_list)` learns rules from example values, `get_result_similar` / `get_result_exact` replay them, and `save` / `load` persist the model. It is MIT-licensed with about 8.1k stars (fetched 2026-10-18). JavaScript-rendered pages aren't documented. — [AutoScraper GitHub](https://github.com/alirezamika/autoscraper)
- ScrapeGraphAI's ScriptCreatorGraph outputs Python code (an `extract_data(html) -> dict` function using BeautifulSoup) instead of data, which you save and reuse on fresh HTML. Config needs `llm` and `library`. Details come from mirrors and docs sites and weren't verified against the repo. — [ScrapeGraphAI ScriptCreatorGraph docs](https://scrapegraph-doc.onrender.com/docs/Graphs/script_creator_graph); [Mintlify mirror](https://www.mintlify.com/ScrapeGraphAI/Scrapegraph-ai/graphs/script-creator)
- Structured-data prevalence (Web Data Commons, October 2024 crawl, the latest found): 51.25% of examined pages had structured data, up from 50.6% in 2023. Of sites with structured data, 70% use JSON-LD, 46% Microdata, 3% RDFa and 23% hCard, about 11.5M sites in total for JSON-LD. — [Uni Mannheim WDC 2024 release](https://www.uni-mannheim.de/dws/news/wdc-json-ld-microdata-rdfa-data-corpus-2024-published); [W3C list announcement, 2025-01](https://lists.w3.org/Archives/Public/semantic-web/2025Jan/0013.html)
- Next.js: Pages Router sites embed a `__NEXT_DATA__` JSON script that is stable and easy to parse. App Router sites stream RSC "flight data" through `self.__next_f.push()` chunks, which are JSON-like but harder to parse. `njsparser` (PyPI) handles both. Moving to Server Components can leave less data in either place. — [trickster.dev, scraping Next.js in 2025](https://www.trickster.dev/post/scraping-nextjs-web-sites-in-2025); [njsparser](https://pypi.org/p/njsparser); [catchmetrics deep dive](https://www.catchmetrics.io/blog/nextjs-page-data-deep-dive-and-performance-insights)
- RFC 9309 lets crawlers read other robots.txt records such as `Sitemap:`, which is the standard way to find a site's URL list without crawling. — [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)

### Inferences
- Recommended zero-token cascade per page:
  1. JSON-LD, Microdata or OpenGraph metadata (covers roughly half of pages per WDC).
  2. Hydration blobs (`__NEXT_DATA__`, `self.__next_f`, Nuxt and similar).
  3. The site's own JSON/XHR API, found once.
  4. A cached per-template CSS/XPath schema (Crawl4AI `generate_schema`, validated on 2–3 samples).
  5. An LLM only as a last resort or for repair when the schema returns empty or fails validation.
- For "1,000 sites, one prompt", token cost depends on template diversity. Same-template pages (product listings, search results, directories) amortize to about 0. For 1,000 distinct domains, expect about 1 schema-generation call per domain that steps 1–3 don't cover. That is still far cheaper than about 1 LLM call per page plus browser screenshots.
- Selector drift is the main failure. Scrapling's adaptive relocation and Crawl4AI's validate-and-refine are the cheapest mitigations. Trigger regeneration whenever required fields come back empty.

### Gaps
- No independent study of how often LLM-generated selectors fail on real sites over time. The papers report SWDE results, and I didn't retrieve their exact F1 numbers.
- No 2025 or 2026 Web Data Commons figures were found. The 2024 crawl is the latest.
- No data on what share of sites expose usable JSON APIs or Next.js hydration data.

## Q4. Free open-source crawling stacks (Crawl4AI, Scrapy, Playwright, Crawlee) for fetching 1,000 pages quickly and politely: throughput and anti-bot handling without paid proxies

### Takeaway
On static pages, HTTP-only Scrapy finishes 1,000 pages in about 30 seconds. Browser-based crawlers run about 1–3 pages per second per process in one small benchmark. An HTTP-first stack that falls back to a browser only when needed finishes 1,000 pages in minutes on a laptop. Without paid proxies, anti-bot success depends mostly on IP reputation. A home IP with a stealth browser (nodriver, Camoufox, Patchright) does far better than datacenter IPs from free clouds.

### Cited Findings
- A Bright Data benchmark (reported by Olostep) fetched 1,000 static catalog pages in 31.57 s with Scrapy (about 1,900 pages/min) versus 156.01 s with Selenium. The benchmark is vendor-run and undated in the excerpt. — [Olostep: Scrapy vs Selenium](https://www.olostep.com/blog/scrapy-vs-selenium)
- MarkCrawl's benchmark: scrapy+md at 5.0 pages/s, Playwright at 2.5 pages/s, Crawlee at 1.3 pages/s on its test sites. The maintainer of one tested tool wrote it, and the test set is unclear. — [MarkCrawl BENCHMARKS.md](https://raw.githubusercontent.com/AIMLPM/markcrawl/main/docs/BENCHMARKS.md)
- Crawl4AI's `arun_many()` uses dispatchers. MemoryAdaptiveDispatcher (the default) has a memory_threshold_percent of 90 and max_session_permit of 10. SemaphoreDispatcher has max_session_permit 20. The optional RateLimiter defaults to base_delay (1.0, 3.0) s, max_delay 60 s, max_retries 3, rate_limit_codes [429, 503]. Streaming mode is supported, and the docs give no throughput numbers. — [Crawl4AI multi-URL crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
- Scrapy AutoThrottle defaults: AUTOTHROTTLE_START_DELAY 5.0 s, AUTOTHROTTLE_MAX_DELAY 60.0 s, AUTOTHROTTLE_TARGET_CONCURRENCY 1.0, which aims for one concurrent request per remote site. — [Scrapy AutoThrottle docs](https://docs.scrapy.org/en/latest/topics/autothrottle.html)
- Anti-bot benchmark (May 2026, one author, 7 tools, 31 live Cloudflare targets, 651 verdicts): nodriver had 28 OK, 3 gated and 0 blocked, the only tool with no hard blocks. Camoufox was one of four libraries to pass strict lab fingerprint tests. A clean fingerprint on a flagged datacenter IP still gets blocked. — [ianlpaterson anti-detect benchmark 2026](https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi/)
- Camoufox is a Firefox fork that spoofs fingerprint APIs at the C level, and its Firefox TLS is whitelisted on many targets that block Chrome-shaped automation. Patchright is a Playwright fork that patches CDP leaks. Cloudflare updates its detection rules several times a month, so rankings go stale. — [send.win stealth browsers 2026](https://blog.send.win/9-best-stealth-headless-browsers-for-scraping-in-2026/?amp=1); [use-apify Cloudflare guide](https://use-apify.com/blog/how-to-bypass-cloudflare-web-scraping)
- Default headless Playwright is detectable. — [trickster.dev, scraping Next.js in 2025](https://www.trickster.dev/post/scraping-nextjs-web-sites-in-2025)

### Inferences
- A practical $0 design to match rtrvr's cloud (about 40 concurrent):
  1. Async HTTP fetch with Scrapy, Crawlee's HTTP crawler or Scrapling's Fetcher at 16–32 global concurrency and 1 per domain.
  2. Escalate to Playwright, Patchright or Camoufox only on JS-required or blocked responses, using 10–20 browser contexts on the laptop.
  3. Run the extraction cascade from Q3.
  For 1,000 distinct domains, per-domain politeness barely slows anything (about 1 request each), so wall-clock time is set by global concurrency. At 2.5 pages/s per browser process, 1,000 pages take about 7 minutes single-threaded and a few minutes with 10+ contexts.
- Free clouds (GitHub, Oracle, Google) run on datacenter ASNs, so anti-bot block rates will be higher there than on the user's home laptop. For a no-proxy setup, the laptop is likely the better worker for protected sites, with free cloud used for unprotected ones.
- Don't treat "bypass" as a goal. Back off on 403/429/challenge responses and mark the site as needing user-driven access, rather than escalating evasion (see Q5).

### Gaps
- No independent, recent head-to-head benchmark of Crawl4AI, Crawlee, Scrapy and Playwright on the same 1,000-URL set.
- The anti-bot benchmark comes from one author and its method wasn't verified. Results drift as Cloudflare updates.
- I didn't verify the current release versions of Crawl4AI, Crawlee, Scrapling or Scrapy as of October 2026, beyond the Crawl4AI docs header (v0.9.x).

## Q5. Legal and ethical guardrails: robots.txt, per-domain rate limits, ToS risk of scraping from free cloud

### Takeaway
Follow RFC 9309: refresh robots.txt at least every 24 hours, treat 5xx as disallow-all, and remember robots.txt grants no authorization. Default to about 1 concurrent request per domain with jittered 1–5 s delays and exponential backoff on 429/503, which is what Scrapy and Crawl4AI defaults already encode. The bigger ToS exposure is the compute provider. GitHub's hosted-runner and "serverless" rules and Colab's bans on proxies, multi-accounting and distributed workers mean a "free scraping fleet" on those platforms can get the account suspended.

### Cited Findings
- RFC 9309 (September 2022): "Crawlers SHOULD NOT use the cached version for more than 24 hours, unless the robots.txt file is unreachable." The parsing limit "MUST be at least 500 kibibytes". On 4xx the crawler "MAY access any resources on the server". On 5xx or unreachable it "MUST assume complete disallow". Crawl-delay is not defined. "These rules are not a form of access authorization." — [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
- Scrapy's AutoThrottle targets 1.0 concurrent request per remote site by default, with a 5 s start delay and a 60 s maximum. — [Scrapy AutoThrottle](https://docs.scrapy.org/en/latest/topics/autothrottle.html)
- Crawl4AI's RateLimiter defaults to a random 1–3 s base delay, backs off up to 60 s on 429/503, and retries 3 times. — [Crawl4AI multi-URL crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
- GitHub hosted runners ban activity "unrelated to the production, testing, deployment, or publication of the software project". All Actions use bans disproportionate server burden and use "as part of a serverless application". — [GitHub additional product terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)
- Colab bans "connecting to remote proxies", "using multiple accounts to work around access or resource usage restrictions", and containerization "to circumvent anti-abuse policies". Free runtimes additionally ban "running distributed computing workers". — [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Hugging Face Spaces allow outbound traffic only on ports 80, 443 and 8080, and free compute Spaces now need a paid plan. — [HF Spaces overview](https://huggingface.co/docs/hub/en/spaces-overview)
- Google Cloud's free trial bans crypto mining and also restricts GPUs and Windows VMs. — [Google Cloud Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)

### Inferences
- Minimum guardrails for the product:
  1. Fetch and cache robots.txt per domain for 24 hours or less, and honor Disallow for the agent's user-agent and for `*`.
  2. Honor Crawl-delay as a courtesy even though it isn't standard.
  3. Use one in-flight request per domain with a jittered 1–3 s delay, plus exponential backoff and a per-domain stop after repeated 429/403 or challenge pages.
  4. Send an honest User-Agent with contact info for bulk jobs.
  5. Skip logged-in or paywalled content unless the user drives it from their own session.
  6. Keep audit logs.
- Don't spread one job across multiple free accounts to multiply quota. Colab explicitly bans it, and it is the same abuse pattern other providers police.
- Using the user's own browser and IP for user-initiated tasks (the rtrvr extension model) carries the lowest platform-ToS risk. Server-side fleets on free cloud carry the highest.

### Gaps
- No legal analysis was gathered on case law (for example, US CFAA or EU database rights) or on enforceability of site ToS against scrapers. That is outside what I could source in this pass.
- I didn't review Oracle, AWS, Azure or GCP acceptable-use policies for scraping-specific language.
