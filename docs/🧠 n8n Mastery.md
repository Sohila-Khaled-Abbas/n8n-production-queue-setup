---
aliases:
  - n8n learning path
  - n8n MOC
type: Map of Content
tags:
  - n8n
  - MOC
date: 2026-07-24
status: Active
---
---

> This MOC sequences n8n mastery across five phases (a bootstrap phase, plus the four requested) aligned to this community's actual production stack: Docker queue-mode execution, external task runners, Qdrant/Ollama-based RAG, and Redis-driven worker scaling. Each phase links to atomic concept notes, a capstone drawn from the workflow portfolio where one exists, and success criteria gating the move to the next phase.

> [!info] Portfolio Indexing 74 workflows isn't a curriculum until it's tagged. Tag each source workflow with `#n8n/fundamentals`, `#n8n/data-engineering`, `#n8n/ai-agents`, or `#n8n/architecture` as you go, and log it in a companion [[Workflow Portfolio Index]] note. Right now Phases 1–3 each have a clean match in the existing portfolio (ETL, scraping/CRM, multi-agent chatbots). Phase 4 doesn't — see the warning there.

![AI Automation Mastery Roadmap](./AI_Automation_Mastery_Roadmap.png)
![Blueprint for Building AI Agents](./Blueprint_for_Building_AI_Agents.png)
## At a Glance

|Phase|Focus|Capstone|
|---|---|---|
|0|Environment Bootstrap|[[Bootstrap the Base Stack]]|
|1|n8n Fundamentals|[[Telegram to Notion Pipeline]]|
|2|Data Engineering & Code Automation|[[Lead Enrichment Scraper]]|
|3|AI, Agents & RAG|[[Multi-Agent RAG Support Chatbot]]|
|4|Production Architecture & Scaling|[[Production Migration and Load Test]]|

---

## Phase 0: Environment Bootstrap

#n8n/fundamentals

> [!warning] Prerequisite, Not Optional Phases 1–3 assume a running self-hosted instance with task runners and Redis reachable — not n8n Cloud. In a self-hosted-first community, standing up the base stack is a Day 1 task. Phase 4 is about _mastering and scaling_ this same architecture later, not first contact with it. A learner who skips this hits a wall in Phase 2 the moment the Python task runner isn't there.

### Core Concepts

- **Containers**
    - [[Docker Fundamentals]]
    - [[Docker Compose Basics]]
- **Base Install**
    - [[n8n Self-Hosted Setup]]
    - [[n8nio-n8n vs n8nio-runners Images]]
    - [[Environment Variables and .env Files]]
- **Low-Resource Machines**
    - [[WSL2 for Windows Users]]
    - [[Docker RAM Capping]]

### Capstone Project: [[Bootstrap the Base Stack]]

- Clone the community's reference `docker-compose.yml`
- Get n8n + PostgreSQL running locally in single-instance (non-queue) mode
- Run one trigger-to-action workflow end-to-end and confirm data survives a container restart

### Success Criteria

> [!success] Milestone: Ready for Phase 1
> 
> - Stack runs locally without hand-holding
> - Learner can stop, rebuild, and restart containers without losing workflow data
> - Learner can name what this setup is _missing_ relative to production (queue mode, workers, autoscaling) — that gap is Phase 4

---

## Phase 1: n8n Fundamentals

#n8n/fundamentals

> [!info] Alignment Correction n8n's "Quickstart" and "Essentials: Your First Workflows" courses (the latter is Course 1 of n8n's own Foundations program) are real, current, and a reasonable spine for this phase — but they currently award a completion badge, not a certification. n8n has stated a certification program is planned, not live yet.[^1] Frame this phase as "aligned to n8n Foundations," not "matches the certification," and revisit once that changes.

### Core Concepts

- **Triggers & Entry Points**
    - [[Webhook Trigger]]
    - [[Schedule Trigger]]
    - [[Manual Trigger]]
    - [[App-Specific Trigger Nodes]]
- **Core Data Model**
    - [[n8n Item Data Structure]]
    - [[n8n Expressions Syntax]]
    - [[Binary vs JSON Data]]
- **Flow Control**
    - [[IF Node]]
    - [[Switch Node]]
    - [[Merge Node]]
    - [[Loop Over Items]]
- **Data Transformation**
    - [[Edit Fields (Set) Node]]
    - [[Code Node — JavaScript Basics]]
- **Connectivity**
    - [[HTTP Request Node]]
    - [[Credentials and Authentication Types]]
    - [[REST API Fundamentals]]
- **Reliability**
    - [[Error Workflow]]
    - [[Error Trigger Node]]
    - [[Execution Logs and Debugging]]

### Capstone Project: [[Telegram to Notion Pipeline]]

- Trigger on an incoming Telegram message
- Parse and transform message content and metadata using expressions — no hardcoded values
- Push a structured record to a Notion database via API
- Handle at least one failure mode gracefully (malformed input, Notion rate limit)

### Success Criteria

> [!success] Milestone: Ready for Phase 2
> 
> - Builds a multi-node workflow from trigger to final action with no tutorial open
> - Reads and writes n8n's item-array structure fluently using expressions
> - Debugs a failing node from execution data, not guesswork
> - Has configured at least two distinct credential types (e.g., API key and OAuth2)

> [!warning] Common Failure Mode Learners who hardcode values instead of learning expressions hit a wall immediately in Phase 2 — passing dynamic data across a task-runner process boundary can't be faked with hardcoding.

---

## Phase 2: Data Engineering & Code Automation

#n8n/data-engineering

> [!info] This Isn't Optional Advanced Tooling — It's the Only Path As of n8n v2.0, the old bundled/Pyodide-based Python Code node is gone. Python in n8n now runs _exclusively_ through the external task runner. That reframes this phase: task runners aren't an advanced layer on top of Python support, they _are_ Python support. Budget real setup time — the `n8nio/runners` image version must match the main `n8nio/n8n` image, and n8n itself must be ≥1.111.0.

> [!warning] Known Setup Gotchas
> 
> - The Task Broker binds to `127.0.0.1` by default — invisible to a runner in a separate container until rebound
> - Don't pull the `latest-debian` tag looking for a Python-ready image — it's a long-abandoned tag pinned to an old n8n version
> - `$evaluateExpression()` inside a Code node breaks under the task runner's secure mode (it disables evaluating strings as code) — don't design around it

### Core Concepts

- **Task Runner Fundamentals**
    - [[External Task Runners]]
    - [[Python Task Runner Environment]]
    - [[JavaScript Task Runner Environment]]
    - [[Task Broker and Sidecar Containers]]
- **Python Data Engineering**
    - [[Pandas DataFrame Operations in n8n]]
    - [[NumPy for Numerical Transforms]]
    - [[Pillow for Image Processing]]
- **JavaScript Automation**
    - [[Puppeteer Fundamentals]]
    - [[Playwright with Stealth Plugin]]
    - [[AJV Schema Validation]]
- **Data Quality**
    - [[Data Cleaning Patterns]]
    - [[Deduplication Strategies]]
    - [[Schema Validation Before Ingestion]]
- **Scraping Discipline**
    - [[Rate Limiting and Backoff]]
    - [[Headless Browser Detection Evasion]]
    - [[Scraping Ethics and robots.txt]]

### Capstone Project: [[Lead Enrichment Scraper]]

- Scrape a target directory/site with Playwright + stealth
- Validate every scraped record against an AJV schema before it moves downstream
- Clean, dedupe, and enrich records with Pandas inside the Python task runner
- Load validated leads into the CRM — this is the portfolio's Lead Generation/CRM automation line

### Success Criteria

> [!success] Milestone: Ready for Phase 3
> 
> - Writes and debugs Python (pandas) inside a task runner independently, including reading the runner's own logs, not just n8n's
> - Scrapes a JS-rendered page without getting blocked on the first attempt
> - Can explain _why_ task runners are process-isolated (a security boundary, not a convenience), not just how to configure one
> - Validates every external or scraped data source against a schema before trusting it downstream

---

## Phase 3: AI, Agents & RAG

#n8n/ai-agents #n8n/rag

> [!info] Infrastructure Dependency Qdrant and Ollama both need to already be running, reachable containers — that's Phase 0's job. This phase is about using them well, not deploying them for the first time.

### Core Concepts

- **Agent Architecture**
    - [[LangChain Nodes in n8n]]
    - [[AI Agent Node]]
    - [[Tool Calling and Function Calling]]
    - [[Multi-Agent Routing]]
    - [[Agent Memory — Buffer and Postgres-Backed]]
- **Retrieval-Augmented Generation**
    - [[RAG Pipeline Architecture]]
    - [[Qdrant Vector Store Node]]
    - [[Embeddings Models]]
    - [[Chunking Strategies]]
    - [[Document Loaders]]
    - [[Binary PDF Data Extraction]]
- **Model Providers**
    - [[Local Ollama Inference]]
    - [[VRAM Optimization and Quantization]]
    - [[Google Gemini API]]
    - [[HuggingFace Inference API]]
    - [[Model Routing by Cost, Latency, and Sensitivity]]
- **Custom Tooling**
    - [[Model Context Protocol (MCP)]]
    - [[FastMCP AI Workflow Architect]]
    - [[n8n as an MCP Server]]

### Capstone Project: [[Multi-Agent RAG Support Chatbot]]

- A router agent delegates to at least two specialized sub-agents — not one agent with many tools bolted on
- One sub-agent performs Qdrant-backed RAG over ingested PDFs: binary in, chunk, embed, retrieve
- Chat memory persists across turns (Postgres-backed)
- At least one agent call routes to local Ollama and another to Gemini or HuggingFace — deliberately, for a stated reason (cost, latency, or data sensitivity), not arbitrarily

### Success Criteria

> [!success] Milestone: Ready for Phase 4
> 
> - Ships a working RAG pipeline end-to-end: binary PDF in, grounded answer out
> - Builds real multi-agent delegation, not a single agent with a long tool list
> - Can state the VRAM/quantization tradeoff behind at least one local model choice
> - Can justify — not just execute — a routing decision between local and hosted inference

---

## Phase 4: Production Architecture & Scaling

#architecture #n8n/scaling

> [!warning] No Portfolio Capstone Available The 74-workflow portfolio behind this roadmap is entirely application-layer — chatbots, ETL, CRM automation, scraping. None of it is infrastructure-layer. The capstone below is constructed for this roadmap, not pulled from the existing portfolio. Worth flagging to the community: this is a gap in the portfolio, not the curriculum.

> [!info] "Autoscaling" Is a Pattern, Not a Button n8n core gives you queue mode, Redis (via Bull) as the broker, and workers you can scale manually. _Dynamic_ autoscaling — spinning workers up or down off queue depth — sits on top of that, usually via community tooling (e.g. the `n8n-autoscaling` project, now compatible with v2.0 and covering both worker and runner scaling) or your own orchestration. Teach it as an architecture pattern to implement, not a setting to toggle.

### Core Concepts

- **Execution Architecture**
    - [[Queue Mode Execution]]
    - [[Main Process vs Worker Process]]
    - [[Dedicated Webhook Processors]]
- **Scaling**
    - [[Redis as Queue Broker]]
    - [[Queue Depth as a Scaling Signal]]
    - [[Dynamic Worker Autoscaling]]
    - [[Runner Autoscaling]]
- **Persistence & Data**
    - [[PostgreSQL for n8n]]
    - [[Execution Data Pruning and Retention]]
    - [[Postgres Vacuuming and Maintenance]]
- **Resource Management**
    - [[Docker Compose Production Config]]
    - [[WSL2 and Docker RAM Capping]]
    - [[Per-Container Resource Limits]]
- **Operations**
    - [[Monitoring and Observability for n8n]]
    - [[Backup and Disaster Recovery]]
    - [[Security Hardening and Isolation Boundaries]]

### Capstone Project: [[Production Migration and Load Test]]

- Migrate the Phase 2 or Phase 3 capstone to run under queue mode with dedicated workers
- Configure autoscaling (via community tooling or a custom script) with an explicit queue-depth threshold
- Simulate concurrent load and benchmark before/after
- Write a runbook: what breaks, how you'd detect it, how you'd recover

### Success Criteria

> [!success] Milestone: Roadmap Complete
> 
> - Stands up the full queue-mode stack from scratch on a clean machine, unaided
> - Can explain and tune the autoscaling trigger logic, not just accept a template default
> - Diagnoses and clears a backed-up queue under simulated load
> - Has a _tested_, not just written, Postgres backup/restore process
> - Runs the full stack inside RAM-capped WSL2 without OOM crashes

---

## Meta

- [[Workflow Portfolio Index]] — phase-tagged index of the 74+ production workflows
- [[n8n Glossary]]
- [[Community Learning Log]]

---

## Sources & Verification

_Verified July 2026 — n8n ships fast; re-check version-specific claims before the next cohort runs through this._

> [!info] Why This Section Exists The framing corrections earlier in this MOC — certification status, v2.0's Python architecture, task runner version requirements, autoscaling as a pattern rather than a shipped toggle — came from checking current docs and community threads, not from general recall. Sources are marked _(official)_ vs _(community)_ so you can weigh them accordingly; the community ones are right about the practical gotchas but aren't authoritative on version behavior.

### Phase 1 — Course & Certification Status

- [n8n Quickstart](https://learn.n8n.io/courses/course-v1:n8n+QS101+2026H2/) _(official)_ — badge course, not a certification; runs from triggers through building a basic AI agent
- [Essentials: Your First Workflows](https://learn.n8n.io/courses/course-v1:n8n+N8N101+2026H2/about) _(official)_ — Course 1 of n8n's own Foundations program

### Phase 2 — Task Runner Architecture (v2.0)

- [n8n v2.0 Breaking Changes](https://docs.n8n.io/2-0-breaking-changes/) _(official docs)_ — removal of the Pyodide Python engine, task-runner-only Python, `$evaluateExpression()` behavior under secure mode
- [Set Up Task Runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners) _(official docs)_ — version-matching requirement between runner and main images, localhost-only broker default
- [n8nio/runners image — GitHub](https://github.com/n8n-io/n8n/tree/master/docker/images/runners) _(official repo)_ — contents of the sidecar image
- [Adding external libraries to task runners](https://dev.to/codebangkok/n8n-code-node-import-external-library-python-javascript-4lp7) _(community)_ — extending the runner image with pandas/numpy via a custom Dockerfile
- [n8n v2 Python Task Runner survival guide](https://nfirdausblog.wordpress.com/2025/12/31/solving-the-n8n-v2-python-task-runner-nightmare-a-step-by-step-survival-guide/) _(community, field-reported)_ — stale image tags, broker networking failures

### Phase 4 — Queue Mode & Scaling

- [Enable Queue Mode](https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode) _(official docs)_ — main/worker/Redis execution architecture
- [Queue Mode reference — Community Charts](https://community-charts.github.io/docs/charts/n8n/queue-mode) _(third-party docs)_ — autoscaling constraints, MCP server endpoint support
- [n8n-autoscaling v2.0 update — community.n8n.io](https://community.n8n.io/t/n8n-autoscaling-updated-for-v2-0-includes-queue-mode-worker-scaling-runner-scaling-cloudflare-etc/245688) _(community forum)_ — third-party project handling worker + runner autoscaling

---
![NotebookLM Mind Map](./NotebookLM_Mind_Map.png)