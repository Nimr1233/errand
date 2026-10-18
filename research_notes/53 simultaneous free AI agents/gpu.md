# Free cloud GPUs for a batched LLM server (about 53 concurrent agent conversations, $0), as of October 2026

Research date: 2026-10-18. Every free tier below can change without notice, so each fact carries the date it was read. "Read 2026-10-17/18" means I fetched the page during this research. Other dates come from the cited source.

## Q1. Kaggle Notebooks: GPUs, quota, session length, internet, phone verification, and whether a server plus tunnel is allowed

### Takeaway
Kaggle is the best $0, no-card option. You get 2x T4 (2 x 16 GB, usable with vLLM tensor-parallel 2) or 1x P100, sessions of up to 12 hours, and a weekly GPU quota of "30 hours or sometimes higher". Phone verification is needed for internet access and GPUs. The Terms do not explicitly ban an inference server or a tunnel. They do require personal, non-commercial use and a single account. The weekly quota (about 30 h) means the server cannot stay up 24/7: plan on roughly 4 hours a day on average.

### Cited Findings
- Hardware per Kaggle's docs (read 2026-10-17): "1 Nvidia Tesla P100 GPU" with 4 CPU cores and 29 GB RAM, and "2 Nvidia Tesla T4 GPUs" with 4 CPU cores and 29 GB RAM. A TPU v3-8 option is also listed (96 CPU cores, 330 GB RAM). The page still says "At time of writing", which suggests old text — [Kaggle Notebooks docs](https://www.kaggle.com/docs/notebooks)
- Kaggle announced the T4 x2 option alongside the P100. "Both GPU environments count toward the same quota." Notebooks submitted through the API with GPU enabled default to P100. Kaggle also reported GPU stockouts and longer waits — [Kaggle product feedback: New GPU (T4s) options](https://www.kaggle.com/product-feedback/361104)
- Session length (verbatim): "12 hours execution time for CPU and GPU notebook sessions and 9 hours for TPU notebook sessions", and "In order to save successfully, the entire Notebook must execute within 12 hours" — [Kaggle Notebooks docs](https://www.kaggle.com/docs/notebooks)
- Weekly quota (verbatim): "You can use up to a quota limit per week of GPU. The quota resets weekly and is 30 hours or sometimes higher depending on demand and resources" — [Kaggle Efficient GPU Usage docs](https://www.kaggle.com/docs/efficient-gpu-usage). An aggregator (2026-09-21) says the exact figure is shown in account settings and "floats". It also says Colab Pro/Pro+ subscribers who link accounts get 15/30 extra GPU hours a week, which Kaggle may end — [GPUPerHour, Free Cloud GPUs in 2026](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- TPU quota is commonly listed as about 20 hours a week (third-party) — [AIFree.dev Kaggle offer](https://aifree.dev/offer/kaggle-free-gpu-tpu)
- The two Kaggle doc pages disagree on idle timeout. The Notebooks doc says: "While editing a Notebook, you are provided with 20 minutes of idle time for your interactive session. If the code is not modified or executed in that time the current interactive session will end" — [Kaggle Notebooks docs](https://www.kaggle.com/docs/notebooks). The GPU-tips doc says: "Interactive sessions remain active until they reach the 60 minute idle timeout limit" — [Kaggle Efficient GPU Usage docs](https://www.kaggle.com/docs/efficient-gpu-usage)
- Background (batch/commit) execution: "The same Notebook can have multiple concurrent batch sessions if you press the commit button prior to completing the first commit" — [Kaggle Efficient GPU Usage docs](https://www.kaggle.com/docs/efficient-gpu-usage)
- Phone verification gates internet access in notebooks and GPU use. These are community and course sources: "everyone must verify on Kaggle to use features such as internet in notebooks", and a missing internet toggle in Settings usually means the account is not phone-verified — [fast.ai forums](https://forums.fast.ai/t/beginner-using-colab-or-kaggle/96280); [Calvin University CS376 lab](https://cs.calvin.edu/courses/cs/376/25sp/units/01introduction/lab/). A third-party guide cites a Kaggle announcement that phone verification is required for notebooks, datasets, discussions and competitions — [AICreditMart Kaggle guide 2026](https://aicreditmart.com/ai-credits-providers/kaggle-free-gpu-tpu-30-hours-week-access-guide-2026/)
- Kaggle Terms of Use, verbatim (read 2026-10-17; no effective date was visible in the scrape):
  - "You also may not have, control, or operate under more than one active Kaggle account or Kaggle User ID."
  - "You will only use the Services for your own internal, personal, non-commercial use, and not on behalf of or for the benefit of any third party, and only in a manner that complies with all laws that apply to you."
  - Prohibited: use that "Engages in cryptomining or otherwise encourages, requests or allows any form of cryptomining."
  — [Kaggle Terms of Use](https://www.kaggle.com/terms)
- In practice, people run servers on Kaggle and expose them with tunnels. A public script starts a FastAPI server on Kaggle/Colab and runs `cloudflared tunnel --url http://localhost:8000` or ngrok — [HF Space run_server.py](https://huggingface.co/spaces/ahaahaaha/adaptive_rag/blob/6f931c4e30adb51a61fcac9dc4aa172a706f4d61/run_server.py). Other users run ngrok and Gradio apps from Kaggle — [OpenZiti forum](https://openziti.discourse.group/t/replace-ngrok-code-with-zrok-code/2146). The kgout PyPI package exists for tunnelling Kaggle output — [kgout on PyPI](https://pypi.org/project/kgout/)
- vLLM has been validated on Kaggle 2x T4 by the community "kaggle-vllm" toolkit: 2 x Tesla T4 (15,360 MiB each), SM75, TP=2, vLLM 0.18.1, PyTorch 2.10.0+cu128, CUDA 12.8, PyPI release 2026-08-31. Its compatibility defaults are `dtype="float16"`, `enforce_eager=True`, `disable_custom_all_reduce=True`. vLLM selected the `TRITON_ATTN` backend on SM75 because FlashAttention 2 was unavailable. The toolkit says it is not an official Kaggle or vLLM product — [kaggle-vllm on PyPI](https://pypi.org/project/kaggle-vllm/)
- The same toolkit's v0.3.x (PyPI 2026-10-15) reports a validated "four-L4 Kaggle run": exactly 4 x NVIDIA L4 (SM89), TP=4, vLLM 0.30.0 — [kaggle-vllm on PyPI](https://pypi.org/project/kaggle-vllm/). I found no Kaggle page that lists an L4 option for free notebooks. A search for one turned up only the T4/P100 announcements — [Kaggle product feedback](https://www.kaggle.com/product-feedback/361104)

### Inferences
- Allowed vs forbidden: nothing in the Kaggle text I retrieved forbids running vLLM/SGLang/llama.cpp in a notebook or exposing it through cloudflared/ngrok. That puts Kaggle in a grey zone: not explicitly allowed, not explicitly banned. Serving your own Chrome extension fits "your own internal, personal, non-commercial use". Serving other people, or a product, would breach "not on behalf of or for the benefit of any third party". Using a second account to get more quota is explicitly forbidden.
- Uptime budget: 30 GPU-hours a week and 12-hour sessions allow about two full 12-hour sessions plus about 6 hours, or about 4.3 hours a day on average. Running 24/7 is impossible on one account. The quota appears to count session hours, not GPU-hours: the T4 x2 environment shares the same quota as the P100, so the 2x T4 option is the better deal.
- To keep a server alive without a browser tab open, a committed "Save & Run All" batch run (headless, up to 12 hours) avoids the 20/60-minute interactive idle timeout. The server cell blocks until the 12-hour cap. The tunnel URL must be read from the run's logs or posted somewhere (for example a gist) that the extension can fetch. I did not test this on Kaggle.
- P100 is compute capability 6.0, below vLLM's floor of 7.0 (see Q4). On a P100, use llama.cpp. On T4 x2, use vLLM.
- The kaggle-vllm L4x4 result may come from competition-specific hardware, not the general free menu. Treat "Kaggle has free L4s" as unverified.

### Gaps
- I could not see Kaggle's live accelerator dropdown or account quota page (they need login). It is unconfirmed whether P100 is still offered in October 2026 and whether L4 or newer options exist.
- I found no official Kaggle statement on tunnels, ngrok/cloudflared, or "running servers" in notebooks, either allowing or banning them. I also found no reports of accounts banned for it.
- I found no Kaggle-official text stating the phone-verification requirement. It rests on community and course sources.
- Unknown: whether a long-running server cell in an interactive session counts as "executed" for the idle timer, and how many GPU sessions can run at once per account.

## Q2. Google Colab free tier: GPU availability, session limits, and exact FAQ prohibitions

### Takeaway
Colab free gives an unspecified GPU (users report a T4), sessions of at most 12 hours, and idle disconnects. Its FAQ explicitly forbids several things this use case needs: "file hosting, media serving, or other web service offerings not related to interactive compute with Colab", "connecting to remote proxies", and, for free users without compute units, "bypassing the notebook UI to interact primarily via a web UI" and "running distributed computing workers". Serving an always-on API to a Chrome extension falls under these, so Colab free is effectively disallowed for this purpose.

### Cited Findings
- Limits (verbatim): "Colab does not publish these limits, in part because they can vary over time." "notebooks can run for at most 12 hours, depending on availability and your usage patterns." "Runtimes will time out if you are idle." — [Colab FAQ](https://research.google.com/colaboratory/faq.html) (read 2026-10-17; page has no date)
- GPUs (verbatim): "The types of GPUs and TPUs that are available in Colab vary over time." "In the version of Colab that is free of charge, access to expensive resources like GPUs is heavily restricted." — [Colab FAQ](https://research.google.com/colaboratory/faq.html). The FAQ does not name the free GPU. Users report a T4 — [GPUPerHour, 2026-09-21](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- Disallowed on all managed runtimes (verbatim list): "file hosting, media serving, or other web service offerings not related to interactive compute with Colab"; "downloading torrents or engaging in peer-to-peer file-sharing"; "connecting to remote proxies"; "mining cryptocurrency"; "running denial-of-service attacks"; "password cracking"; "using multiple accounts to work around access or resource usage restrictions"; "creating deepfakes"; "employing techniques such as containerization to circumvent anti-abuse policies" — [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Additionally disallowed on free runtimes without a positive compute-unit balance, which may be terminated without warning (verbatim): "remote control such as SSH shells, remote desktops"; "bypassing the notebook UI to interact primarily via a web UI"; "chess training"; "running distributed computing workers" — [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- The FAQ does not use the word "tunnel" — [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Interactive priority: "Colab prioritizes interactive compute." "Colab prioritizes users who are actively programming in a notebook." — [Colab FAQ](https://research.google.com/colaboratory/faq.html). Google also warns free users that "execution will be interrupted when user interaction ceases, and the VM will be deleted soon after that" — quoted by [GPUPerHour, 2026-09-21](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- Colab Pro for Education (free for US students, launched 2025-07-18) is "no longer available for new signups at this time" — [GPUPerHour, 2026-09-21](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)

### Inferences
- An OpenAI-compatible endpoint that a Chrome extension calls through a tunnel is a "web service offering not related to interactive compute". It is reached outside the notebook UI, and tunnel agents arguably count as "remote proxies". Colab free is the worst fit here: it is explicitly prohibited, the session ends when you stop interacting, and Google may terminate it without warning. Reasonable only for short, attended tests.

### Gaps
- No official free-tier GPU model, idle-timeout figure (the often-quoted 90 minutes is not on the FAQ), or daily/weekly GPU allowance. Google does not publish these.
- I found no 2025-2026 reports specifically documenting Colab enforcement against ngrok/cloudflared for LLM APIs.

## Q3. Every other free GPU route (SageMaker Studio Lab, Lightning, Modal, Paperspace, HF ZeroGPU, hyperscalers, Intel, AMD, NVIDIA, Codespaces, Saturn, Deepnote, Vast/RunPod, student programs)

### Takeaway
Outside Kaggle, almost nothing gives free, no-card GPU time suitable for an always-on batched server in October 2026:
- **Studio Lab:** closed to new users.
- **Lightning AI:** whole platform offline since 2026-10-16 after a security incident.
- **HF ZeroGPU:** minutes per day.
- **Google Cloud trial:** forbids GPUs.
- **Paperspace free:** a 2015-era 8 GB M4000.

The usable credit-based routes are trial-like:
- **Modal Starter:** $30/month, renewing. About 51 T4-hours or about 37 L4-hours a month. Native HTTPS endpoints, no tunnel needed. Card requirement unconfirmed.
- **AMD Developer Cloud:** a one-off $100 on MI300X by application, expiring in 30 days.

### Cited Findings
**Amazon SageMaker Studio Lab**
- AWS: "Amazon SageMaker Studio Lab is no longer open to new customers. Existing customers can continue to use the service as normal" — quoted from AWS docs by [GPUPerHour, 2026-09-21](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) (AWS page: [Studio Lab availability change](https://docs.aws.amazon.com/sagemaker/latest/dg/studio-lab-availability-change.html))
- FAQ (read 2026-10-17, verbatim): it "doesn't require an AWS account"; "GPU runtime is limited to 4 hours per session and no more than a total of 4 hours in a 24-hour period"; "CPU runtime is limited to 4 hours per session and no more than a total of 8 hours in a 24-hour period"; a mobile phone number is required, and "One phone number can only be used for one account"; "Attempting to access compute in ways beyond our standard user interface may result in your account being suspended, blocked, or deleted." — [Studio Lab FAQ](https://studiolab.sagemaker.aws/faq)

**Lightning AI**
- Site banner, read 2026-10-17/18 (lightning.ai and lightning.ai/pricing both return HTTP 503): "On October 15, 11:00 PM UTC we identified a security incident on the Lightning Platform involving unauthorized access to credentials. We revoked all user access to the Lightning Platform on October 16 at 1:00 AM UTC... the Platform will remain inaccessible to all users" — [Lightning AI](https://lightning.ai/)
- Before the outage (2026-09-21): free plan "1 free active Studio (4 hour restarts)", 50 GB storage, "Free Studios become paid after 4 hours". The monthly free-credit amount was unconfirmed because third parties disagree — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- Separately, PyTorch Lightning PyPI versions 2.6.2 and 2.6.3 were malicious (April 2026 supply-chain attack) — [Aviatrix threat research](https://aviatrix.ai/threat-research-center/pytorch-lightning-supply-chain-attack-2026/)

**Modal**
- Pricing page (read 2026-10-17): Starter "$30 / month free credits", including "$30 of compute (GPUs, CPUs, Memory) per month"; 100 containers and 10 GPU concurrency; "Scheduled and Web Functions (limited)". Per-second prices: T4 $0.000164/s, L4 $0.000222/s, A10 $0.000306/s, A100 40 GB $0.000583/s, A100 80 GB $0.000694/s, H100 $0.001097/s. "Graduate students, labs, and researchers can get up to $10k in free compute credits" (by application). The page does not say whether a card is required — [Modal pricing](https://modal.com/pricing)

**Paperspace / DigitalOcean Gradient**
- Free plan: a "Free GPU (M4000)" machine for notebooks in private workspaces, 5 GB storage, auto-shutdown after 6 hours at most. Docs last verified 2026-07-13; free-capacity availability untested — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) citing [DigitalOcean Paperspace pricing](https://docs.digitalocean.com/products/paperspace/pricing/)
- The M4000 has 8 GB VRAM and 192 GB/s bandwidth (Maxwell, 2015) — [GPUPerHour spec table](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)

**Hugging Face ZeroGPU / Spaces**
- ZeroGPU uses a shared RTX PRO 6000 Blackwell; the default `large` is half a GPU with 48 GB. A free account gets 5 minutes of GPU time a day and unauthenticated visitors get 2. Gradio Spaces only, 60-second default GPU function, no `torch.compile`. PRO ($9/month) gets 40 minutes — [GPUPerHour, 2026-09-21](https://gpuperhour.com/blog/free-cloud-gpus-and-credits), citing [HF ZeroGPU docs](https://huggingface.co/docs/hub/spaces-zerogpu)
- The sources conflict. A forum thread cites 3.5 minutes a day for free and 25 for PRO, and an HF staff answer (April 2026) mentions a request-based limit of 3 times per day — [HF forum: free ZeroGPU quota](https://discuss.huggingface.co/t/what-is-the-free-zerogpu-quota-for-1-space/178610); [HF forum: free account quota issue](https://discuss.huggingface.co/t/free-account-zerogpu-quota-issue/175180/9)

**Hyperscaler free trials (all need a card)**
- Google Cloud: "$300 Welcome credit to spend over 90 days", but during the trial you cannot "Add GPUs to your VM instances", and "GPUs and TPUs are not included in the Free Tier offer." AWS: up to $200 over 6 months on a plan "Limited to select services only". Azure: "$200 credit to explore Azure for up to 30 days", requiring a phone number and a non-prepaid card; GPU quota for new subscriptions not stated — [GPUPerHour, 2026-09-21](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) citing [Google Cloud free features](https://docs.cloud.google.com/free/docs/free-cloud-features), [AWS Free Tier](https://aws.amazon.com/free/), [Azure free account](https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account)

**Student programs**
- Azure for Students: "$100 credit to use on Azure services within 12 months", "No credit card required", for full-time university students. Only burstable CPU VMs are listed as free services, and GPU eligibility is not stated — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) citing [Azure for Students](https://azure.microsoft.com/en-us/free/students)
- GitHub Student Developer Pack (2026-09-21): "$100 in Azure credit"; Camber student plan "40 CPU hours, 5 GPU hours, 50 GB of storage"; a Deepnote plan with no GPU; Codespaces (no GPU mentioned). No DigitalOcean credit appeared on the pack page — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) citing [GitHub Education Pack](https://education.github.com/pack)

**AMD Developer Cloud**
- (verbatim, page updated 2026-07-14) "AMD is offering an initial $100 complimentary cloud credit to qualified developers who apply and join AMD AI Developer Program. Complimentary credit hours expire thirty (30) days from the date of deposit". Allocation is "determined by AMD in its sole discretion, based on the intended use case". "Complimentary AMD cloud credit applies only to use on AMD Instinct MI300X GPUs." "If you are granted complimentary credit hours... and your credit expires and you have no active payment method on file, your AMD GPU VM will be destroyed" — [AMD Developer Cloud](https://www.amd.com/en/developer/resources/cloud-access/amd-developer-cloud.html)
- Card requirement is unclear. AMD's wording implies a payment method is optional, but a third-party guide says "you add a payment method (required even with credits)" and estimates about 50 hours on one MI300X at about $1.99/hr — [AdwaitX](https://www.adwaitx.com/openclaw-vllm-amd-developer-cloud-free/). An older vLLM-forum offer was framed as GPU hours instead of dollars — [vLLM forum](https://discuss.vllm.ai/t/amd-developer-cloud-free-gpu-hours/974)

**Intel Tiber AI Cloud**
- A secondary source (2026-07-23) lists it as free GPU access with no card: JupyterLab and training notebooks on Intel Gaudi and Data Center GPU Max, using oneAPI/PyTorch XPU (not CUDA), with batch-based shared sessions that are not always on. No quotas given — [AIMultiple free cloud GPU](https://aimultiple.com/free-cloud-gpu)

**NVIDIA, startup programmes, RunPod/Vast**
- NVIDIA Inception: "free cloud credits from NVIDIA and partners", no amount stated. Requires an incorporated company less than 10 years old with a website, so it is not for individuals — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) citing [NVIDIA Inception](https://www.nvidia.com/en-us/startups/)
- RunPod referral: a new user who loads at least $10 gets "a random weighted bonus between $5 and $500" ($5 fixed in Europe), with Google sign-in required. Cheapest live rentals on 2026-10-18: RTX 3090 $0.27/hr (Vast.ai), L4 $0.59/hr (RunPod); no T4 in stock — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)

### Inferences
- Modal's $30/month: $30 / ($0.000164 x 3600 = $0.59/hr) ≈ 51 T4-hours, or $30 / $0.80/hr ≈ 37 L4-hours, or about 27 A10-hours a month. Modal web endpoints get HTTPS URLs directly, so no tunnel is needed and the Chrome extension can call them. Because it is serverless, a vLLM container can scale to zero between sessions, which stretches the credit for bursty agent use. Cold starts (model load) cost time and credit.
- An AMD MI300X (192 GB) running vLLM/ROCm could easily hold 53 concurrent 8B conversations with long contexts. It is the strongest hardware here, but it is a one-off, approved-by-application, 30-day trial, so it does not meet a sustained $0 goal.
- Intel Gaudi/Max (non-CUDA) and Paperspace's M4000 (compute capability 5.x, below vLLM's 7.0 floor) are poor fits for a vLLM batching server.
- ZeroGPU's 5 minutes a day and its Gradio-only, 60-second-per-call model make it unusable for 53 agents.

### Gaps
- Whether Modal Starter requires a credit card. Not stated on the pricing page, and I did not confirm it elsewhere.
- Lightning AI's free-credit amount, and when or whether the platform comes back.
- GitHub Codespaces GPU machines: I found no current source. GPU codespaces do not appear in the 2026 Student Pack listing.
- Saturn Cloud's free tier (GPU or not) and Deepnote GPU: no 2026 source found, except that the Student Pack Deepnote plan has no GPU.
- Intel Tiber free-tier quotas, and whether an inference server or external access is allowed. No primary source.
- Azure for Students GPU quota: not stated by Microsoft.
- NVIDIA developer-program GPU hosting for individuals: none found. NVIDIA's hosted free API (build.nvidia.com) is not GPU hosting and was out of scope here.

## Q4. Throughput of a T4/P100/L4 serving a 4B-8B model with vLLM at about 53 concurrent requests, and which models fit in 16 GB

### Takeaway
I found no published batched (concurrency 32-64) vLLM benchmark on T4. On a single T4, the binding limit for 53 conversations is KV-cache memory, not compute. With a 4-bit 4B model, about 10 GB remains for KV, roughly 1.3K tokens of context per conversation, so long agent transcripts will queue or be preempted. Kaggle's 2x T4 with TP=2 roughly doubles that. My back-of-envelope estimate (inference, not measured) is a few hundred to about 650 output tokens/s aggregate, roughly 8-12 tokens/s per agent. Prefill of long agent prompts is likely the real throughput limit.

### Cited Findings
- T4 specs: 16 GB VRAM, 320 GB/s memory bandwidth, 65 TFLOPS FP16 dense, Turing (2018). RTX 4090 for comparison: 24 GB, 1,008 GB/s — [GPUPerHour spec table](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- vLLM hardware floor is compute capability 7.0, and the T4 (7.5) meets it. T4 lacks bfloat16, so run `--dtype float16` — [MarkAI Code T4 guide](https://markaicode.com/benchmarks/cuda-production-benchmark-latency/); [RunAIHome FlashAttention fixes 2026](https://runaihome.com/blog/flashattention-only-supports-ampere-gpus-fix-2026/). FlashAttention 2 is unavailable on SM75, and vLLM uses `TRITON_ATTN` — [kaggle-vllm](https://pypi.org/project/kaggle-vllm/). Some newer model backends (for example Qwen3-VL, late 2025) dropped Turing support — [RunAIHome](https://runaihome.com/blog/flashattention-only-supports-ampere-gpus-fix-2026/)
- Single-stream T4 (Colab, 2026-03-22): Qwen2.5-7B-Instruct-AWQ on vLLM with `--max-model-len 2048 --gpu-memory-utilization 0.85 --enforce-eager --dtype float16 --quantization awq` reached 22.60 tok/s, TTFT 841 ms. Ollama with qwen2.5:7b Q4_K_M (4.36 GiB) reached 31.11 tok/s, TTFT 233 ms. Single request only, and the author says fp16 7B exceeds single-T4 headroom — [Nishant0905 gist](https://gist.github.com/Nishant0905/d1c5ff79a4622f8d0db747db3e759e84)
- T4 batch 1, Llama-3.1-8B: llama.cpp Q4_0 30.8 tok/s; W4A16 16.7 tok/s; W4A8 47.7 tok/s (research paper, different engine) — [arXiv 2604.21026](https://arxiv.org/pdf/2604.21026)
- One blog claims 1,450 tok/s for Llama 3 8B at 8 concurrent on a single T4 with vLLM, but it is from one environment run and carries a self-described correction. Low confidence: fp16 8B weights (about 16 GB) do not fit a 16 GB T4 — [MarkAI Code](https://markaicode.com/benchmarks/cuda-production-benchmark-latency/)
- Dual-T4 TP=2 vs a single GPU (kaggle-vllm M4 study): the first concurrency at which TP2 output throughput became favorable was 64 for Qwen2.5-3B (balanced workload), 32 for Phi-4-mini, and 16 for Ministral-3-3B and Llama-3.2-3B. Prefill-heavy workloads crossed over at about 4. Qwen at prefill-heavy concurrency 64 was "resource-gated". At low load (OPT-125M), TP2 was 26.73% slower in graph mode and 44.78% slower in eager mode. No tokens/s published — [kaggle-vllm](https://pypi.org/project/kaggle-vllm/)
- llama.cpp vs vLLM at 64 concurrent (Qwen2.5-7B, 4,096 tokens per slot, `-np 64 -cb`, on RTX 4090/L40S/5090, not T4): vLLM delivered 2.8-4.4x llama.cpp's aggregate throughput. llama.cpp reached about 2,391 tok/s on a 4090, and its aggregate rose about 7-14x from 1 to 64 requests — [Computing for Geeks](https://computingforgeeks.com/ollama-vs-vllm-vs-llama-cpp/)
- General vLLM behaviour: at concurrency 1-4 the GPU is underused. At 64-256, throughput plateaus and latency degrades from queueing and memory pressure — [vLLM forum: benchmark concurrency](https://discuss.vllm.ai/t/how-to-benchmark-concurrency/1611/2)
- Qwen3-4B architecture: 36 layers, 32 attention heads, 8 KV heads, head_dim 128, hidden 2560, max_position_embeddings 40960, trained in bfloat16 — [Qwen3-4B config.json](https://huggingface.co/Qwen/Qwen3-4B/raw/main/config.json)

### Inferences
These are my calculations, not measurements.
- **KV per token (Qwen3-4B, fp16):** 2 (K,V) x 36 layers x 8 KV heads x 128 x 2 bytes = 147,456 B ≈ 144 KiB/token.
- **Single T4, Qwen3-4B in fp16 (about 8 GB weights):** about 4-5 GB left for KV, roughly 28-35K tokens total, or about 550-650 tokens per conversation at 53 concurrent. Unworkable for agents.
- **Single T4, Qwen3-4B in 4-bit AWQ/GPTQ (about 2.5-3 GB):** about 10 GB KV, roughly 70K tokens, or about 1.3K tokens per conversation. Workable only with short contexts. Otherwise vLLM serves a subset and queues the rest.
- **Kaggle 2x T4, TP=2:**
  - Qwen3-4B fp16: about 18 GB KV, roughly 125K tokens, or about 2.4K per conversation.
  - Qwen3-4B 4-bit: about 23 GB KV, roughly 160K tokens, or about 3K per conversation.
  - 8B models (Llama-3.1-8B: 32 layers, 8 KV heads ≈ 128 KiB/token; architecture from memory, not fetched) fit in fp16 only with TP=2 (about 16 GB weights over about 27 GB usable), leaving about 11 GB KV, or about 1.6K tokens per conversation. With 4-bit on TP=2, about 3K per conversation.
- **Decode throughput ceiling:** each decode step reads the weights (about 2.7 GB at 4-bit) plus all live KV (up to about 10 GB). At 320 GB/s that is about 40 ms per step, about 25 steps/s x 53 ≈ 1,300 tok/s theoretical. With Triton attention, eager mode and real-world bandwidth efficiency of 30-50%, expect about 400-650 tok/s aggregate on one T4, about 8-12 tok/s per agent. 2x T4 adds bandwidth but TP overhead in eager mode is real (above).
- **Prefill is likely the bottleneck:** agent turns resend large prompts (system prompt, tool schemas, history). At an effective 15-20 TFLOPS on T4, a 4B model prefills roughly 2-2.5K tokens/s. 53 agents each sending a 3K-token uncached prompt is about 160K tokens, about 60-80 s per round. vLLM automatic prefix caching helps multi-turn, but the small KV pool evicts prefixes quickly.
- **Requests per minute:** order of magnitude only, roughly 30-100 agent turns per minute on Kaggle 2x T4 with a 4B 4-bit model. That is about one turn per agent per minute.
- **Models to use on T4:** 3B-4B instruct models in fp16 or AWQ/GPTQ 4-bit (Qwen3-4B, Phi-4-mini, Llama-3.2-3B, Ministral-3-3B, which kaggle-vllm tested on 2x T4). Use 7B-8B only as 4-bit, or as fp16 across 2x T4. Run with `--dtype float16`. Qwen3 is bf16-trained, so fp16 overflow is possible on some models; test before trusting it.
- **P100:** compute capability 6.0 is below the vLLM floor, so use llama.cpp (`llama-server -np N -cb`). Aggregate throughput will be several times lower than vLLM.
- **L4** (24 GB, Ada, bf16/FP8, about 300 GB/s): not available free except possibly via the unverified Kaggle L4x4 or Modal credits (about 37 hours a month).

### Gaps
- No measured vLLM or SGLang tokens/s on T4, 2x T4 or L4 at concurrency 32-64 for any 4B-8B model. The report writer should present the numbers above as estimates. The fastest way to get real numbers is `vllm bench serve --max-concurrency 1,8,16,32,53,64` on Kaggle 2x T4.
- Whether vLLM's fp8 KV-cache storage (which would roughly double KV capacity) works on Turing SM75. Not verified.
- SGLang support status on T4 in 2026. Not researched.

## Q5. Practical setup: reaching the server from a Chrome extension, auto-shutdown, idle timeouts, uptime per day and week

### Takeaway
To reach a notebook-hosted server from a laptop you need a tunnel. Cloudflare Quick Tunnels need no account and allow 200 in-flight requests, which is enough for 53, but they do not support SSE streaming and are "for testing and development". ngrok free allows 20,000 HTTP requests a month and 1 GB of data, which 53 agents would burn through in hours. Realistic uptime: Kaggle about 30 hours a week in up to 12-hour sessions; Colab up to 12 hours, attended and disallowed for this use; Studio Lab 4 hours a day for existing users only; Paperspace 6 hours per session.

### Cited Findings
- Cloudflare Quick Tunnels (trycloudflare), verbatim: "Each Quick Tunnel supports up to 200 in-flight requests" (excess requests get HTTP 429); "Quick Tunnels do not support Server-Sent Events (SSE)"; "Quick Tunnels have no uptime guarantee"; "Quick Tunnels are for testing and development"; "You do not need a Cloudflare account or domain." — [Cloudflare docs: Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)
- A Cloudflare Tunnel connectivity incident on 2026-07-28 required restarting cloudflared connectors — [Pulsetic: Cloudflare incident](https://pulsetic.com/status/cloudflare/incidents/5977/)
- ngrok free plan, verbatim: HTTP request rate "4,000 / min"; "Data transfer out" "1 GB / month"; "HTTP requests" "20,000 / month"; "Up to 3" online endpoints; "The dev domain is the only domain available on the free plan"; "ngrok shows an interstitial page in front of all HTML browser traffic on the free tier"; "Free endpoints have no timeout—they can stay online indefinitely." — [ngrok free plan limits](https://ngrok.com/docs/pricing-limits/free-plan-limits/). An older Colab forum report quotes a 120 requests/min free limit (ERR_NGROK_734), which conflicts with the current 4,000/min — [Stable Diffusion Art forum](https://stable-diffusion-art.com/forums/topic/colab-notebook-no-longer-has-ngrok-link/). A Kaggle tool README says ngrok free tunnels disconnect after about 2 hours, which conflicts with ngrok's "no timeout" statement — [kgout](https://pypi.org/project/kgout/)
- Kaggle: 12-hour session cap; 20-minute interactive idle limit in the Notebooks doc vs 60-minute in the GPU-tips doc; commits run as batch sessions — [Kaggle Notebooks docs](https://www.kaggle.com/docs/notebooks); [Kaggle Efficient GPU Usage](https://www.kaggle.com/docs/efficient-gpu-usage)
- Colab: up to 12 hours; idle timeouts; interruption "when user interaction ceases" — [Colab FAQ](https://research.google.com/colaboratory/faq.html); [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- Studio Lab: 4 hours per GPU session, 4 hours per 24 hours — [Studio Lab FAQ](https://studiolab.sagemaker.aws/faq). Paperspace free: auto-shutdown after at most 6 hours — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- The kaggle-vllm `serve` command binds to "notebook-local loopback", so external exposure needs a tunnel the user adds — [kaggle-vllm](https://pypi.org/project/kaggle-vllm/)
- The Kaggle models must be downloaded each session (internet on) or attached as Kaggle Inputs. kaggle-vllm notes "offline Kaggle Inputs are required" for its runtime artifacts — [kaggle-vllm](https://pypi.org/project/kaggle-vllm/)

### Inferences
- Recommended $0 stack:
  1. Kaggle, phone-verified, internet ON, GPU T4 x2.
  2. vLLM with `--tensor-parallel-size 2 --dtype float16`, a 3B-4B instruct model (4-bit for longer contexts), and `--max-num-seqs 64`.
  3. `cloudflared tunnel --url http://localhost:8000`.
  4. The Chrome extension calls the OpenAI-compatible `/v1/chat/completions` with `stream: false`, because Quick Tunnels drop SSE.
  5. Run as a committed (Save & Run All) notebook so it survives closing the browser, for up to 12 hours.
- The Quick Tunnel URL is random and changes every session, so the extension needs a way to learn the new URL: a pasted setting, or the notebook writing it to a gist or pastebin the extension polls.
- A named Cloudflare Tunnel (stable hostname, SSE works) needs a Cloudflare account and a domain on Cloudflare, which may cost money for the domain.
- ngrok free is a poor fit. At about 1 request per agent per minute, 53 agents make about 3,180 requests an hour, which exhausts 20,000 a month in about 6 hours. 1 GB a month also caps data. The interstitial affects only HTML browser traffic; API calls with the `ngrok-skip-browser-warning` header avoid it (from memory, not verified here).
- With one Kaggle account, the server can be up about 30 hours a week. More accounts would breach Kaggle's single-account rule, and Colab and Studio Lab have the same rule. For sustained 24/7 at $0, no compliant option was found. The cheapest non-free fallback on 2026-10-18 was a rented RTX 3090 at $0.27/hr (about $6.50/day) — [GPUPerHour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)

### Gaps
- Not tested: whether Kaggle commit sessions keep outbound tunnel processes alive for the full 12 hours, and whether Kaggle's network allows cloudflared's QUIC/HTTP2 egress in October 2026.
- No official Kaggle or Colab statement found on detection or enforcement against tunnels.
