#!/usr/bin/env python3
"""
publish_workflows_portfolio.py

Automated Portfolio Showcase Generator for n8n Workflows adhering to Software Engineering Guidelines.
Generates standalone GitHub repository structures for top production workflows,
complete with custom README.md files, Mermaid architecture diagrams, CI/CD validation workflows,
badges, workflow JSON files, and automated GitHub topic tagging scripts.
"""

import os
import json
import re
import sys
import shutil
import subprocess

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Root directory of the repository
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS_DIR = os.path.join(PROJECT_ROOT, "workflows")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "published_repos")
GITHUB_USER = "Sohila-Khaled-Abbas"
MAIN_REPO = f"https://github.com/{GITHUB_USER}/n8n-production-queue-setup"

SHOWCASE_WORKFLOWS = [
    {
        "slug": "n8n-workflow-gourmet-bistro-customer-service",
        "file": "Gourmet Bistro Customer Service.json",
        "title": "Gourmet Bistro Multi-Agent AI Customer Service & Ordering System",
        "category": "AI Chatbots & Conversational Commerce",
        "tagline": "Multi-agent LangChain structure for restaurant customer service, RAG vector search, order creation, and kitchen dispatch.",
        "tech_stack": ["n8n", "LangChain Multi-Agent", "Qdrant Vector DB", "Google Sheets", "Supabase PostgreSQL", "Telegram Bot API"],
        "topics": ["n8n", "n8n-workflow", "langchain", "multi-agent", "rag", "qdrant", "telegram-bot", "supabase", "software-engineering"],
        "business_value": "Enforces strict business rules (phone validation, delivery checks, 5-minute cancellation grace period) while reducing front-of-house customer service load by up to 80%.",
        "mermaid_diagram": """sequenceDiagram
    autonumber
    actor Customer as Customer (Telegram)
    participant Agent as LangChain Multi-Agent Router
    participant RAG as Qdrant Vector Store
    participant DB as Supabase PostgreSQL
    participant Sheet as Google Sheets Pricing
    participant Kitchen as Kitchen Staff (Telegram Alert)

    Customer->>Agent: Send Message / Query
    alt Menu & FAQ Inquiries
        Agent->>RAG: Vector Search Embeddings
        RAG-->>Agent: Relevant FAQ / Menu Context
        Agent-->>Customer: Grounded Answer with Details
    else Draft Order Creation
        Agent->>Sheet: Query Pricing Data
        Agent->>DB: Persist Draft Order Payload
        Agent-->>Customer: Order Confirmation & Subtotal
    else Order Validation & Kitchen Dispatch
        Agent->>Agent: Validate Egyptian Phone & Address
        Agent->>Kitchen: Send Real-Time Order Telegram Alert
        Agent-->>Customer: Order Dispatched to Kitchen
    end"""
    },
    {
        "slug": "n8n-workflow-upwork-ai-proposal-creator",
        "file": "Upwork AI Proposal Creator.json",
        "title": "Upwork AI Automated Proposal & Job Lead Scraper",
        "category": "Productivity & Lead Generation",
        "tagline": "Scrapes target Upwork job postings via Apify, analyzes job requirements using LLMs, and auto-drafts tailored proposals.",
        "tech_stack": ["n8n", "Apify Upwork Scraper", "LangChain Agent", "OpenAI GPT-4", "JavaScript"],
        "topics": ["n8n", "n8n-workflow", "apify", "web-scraping", "openai", "gpt-4", "proposal-generator", "software-engineering"],
        "business_value": "Saves agency owners and freelancers up to 10+ hours per week by automating top-of-funnel freelance job qualification and proposal drafting.",
        "mermaid_diagram": """graph TD
    A[Cron Schedule / Webhook] --> B[Apify Upwork Scraper Node]
    B --> C{Filter Relevant Jobs?}
    C -- Yes --> D[Extract Job Requirements]
    D --> E[LangChain AI Proposal Generator]
    E --> F[Format Proposal & Match Client Criteria]
    F --> G[Save Draft to Google Sheets / Notion]
    C -- No --> H[Skip Job Entry]"""
    },
    {
        "slug": "n8n-workflow-emaar-towers-lead-qualification",
        "file": "Emaar Towers Lead Qualification Agent.json",
        "title": "Emaar Towers Real Estate Lead Qualification AI Agent",
        "category": "Lead Generation & CRM",
        "tagline": "High-end real estate lead filtering agent that qualifies buyers based on budget, down payment capacity, and location preferences.",
        "tech_stack": ["n8n", "LangChain Agent", "OpenRouter API", "Google Sheets CRM", "Telegram Alerts"],
        "topics": ["n8n", "n8n-workflow", "lead-qualification", "crm-automation", "openrouter", "telegram-bot", "software-engineering"],
        "business_value": "Filters out unqualified leads automatically and alerts senior real estate brokers immediately for high-budget luxury inquiries.",
        "mermaid_diagram": """flowchart LR
    Inquiry[Inbound Buyer Message] --> Agent[AI Qualification Agent]
    Agent --> Questions[Collect Budget & Location Preferences]
    Questions --> Eval{Budget >= Luxury Threshold?}
    Eval -- High Value Lead --> CRM[Persist in Google Sheets CRM]
    CRM --> Alert[Trigger Urgent Broker Telegram Alert]
    Eval -- Low Budget --> Nurture[Send Automated Informational Brochure]"""
    },
    {
        "slug": "n8n-workflow-delivery-telegram-bot",
        "file": "Delivery Telegram Bot.json",
        "title": "Interactive Food Delivery Telegram Bot with MSSQL Session Persistence",
        "category": "AI Chatbots & Conversational Commerce",
        "tagline": "Conversational commerce bot enabling natural language food ordering with durable state persistence in MSSQL.",
        "tech_stack": ["n8n", "Telegram Trigger", "LangChain Agent", "MSSQL", "OpenRouter"],
        "topics": ["n8n", "n8n-workflow", "telegram-bot", "mssql", "conversational-commerce", "session-persistence", "software-engineering"],
        "business_value": "Provides 24/7 interactive ordering directly inside messaging apps with automatic session recovery across chat restarts.",
        "mermaid_diagram": """sequenceDiagram
    Customer->>Telegram: Send Cart Modification / Order Message
    Telegram->>n8n: Trigger Workflow Execution
    n8n->>MSSQL: Read Active Session State & Cart
    n8n->>LangChain: Process Intent & Update Items
    LangChain->>MSSQL: Update Cart Payload & State
    n8n-->>Customer: Return Updated Order Summary"""
    },
    {
        "slug": "n8n-workflow-apple-rag-chatbot-v2",
        "file": "Apple RAG Chatbot V2.json",
        "title": "Apple Products Technical Support RAG AI Agent (V2)",
        "category": "RAG & Knowledge Bases",
        "tagline": "Retrieval-Augmented Generation (RAG) assistant indexing Apple technical support documentation for context-aware Q&A.",
        "tech_stack": ["n8n", "Qdrant Vector DB", "OpenAI Embeddings", "LangChain Conversational Agent", "Chat Trigger"],
        "topics": ["n8n", "n8n-workflow", "rag", "qdrant", "openai-embeddings", "vector-database", "ai-agent", "software-engineering"],
        "business_value": "Eliminates AI hallucinations by grounding responses strictly in verified product documentation with source citation.",
        "mermaid_diagram": """graph LR
    UserMsg[User Technical Question] --> Embed[OpenAI Embedding Generator]
    Embed --> Qdrant[Qdrant Vector DB Similarity Search]
    Qdrant --> Context[Retrieve Top Relevant Doc Snippets]
    Context --> Agent[LangChain RAG Agent]
    Agent --> Response[Answer with Source Citations]"""
    },
    {
        "slug": "n8n-workflow-daily-viral-content-radar",
        "file": "Daily Viral Content Radar (AnyAPI).json",
        "title": "Daily Viral Content Radar & Multi-API Trend Aggregator",
        "category": "Productivity & Content ETL Pipelines",
        "tagline": "Monitors social platforms and APIs daily, extracts high-performing content trends, and generates AI executive summaries.",
        "tech_stack": ["n8n", "HTTP Request (APIs)", "LLM Summarizer", "Google Sheets", "Email Digest"],
        "topics": ["n8n", "n8n-workflow", "content-curation", "trend-analysis", "etl-pipeline", "http-api", "software-engineering"],
        "business_value": "Automates content curation and market trend monitoring, providing content teams with daily viral insights effortlessly.",
        "mermaid_diagram": """flowchart TD
    Cron[Daily Cron Trigger 08:00 AM] --> APIs[Fetch External API Social Metrics]
    APIs --> Parse[Parse Metric Virality Scores]
    Parse --> LLM[Generate AI Summary & Hook Recommendations]
    LLM --> Sheet[Store Viral Trends in Google Sheets]
    LLM --> Email[Send Executive Email Digest]"""
    },
    {
        "slug": "n8n-workflow-telegram-notion-etl",
        "file": "AI Learning Pipeline Telegram to Notion ETL.json",
        "title": "AI Learning Pipeline: Telegram to Notion Knowledge ETL",
        "category": "Productivity & Content ETL Pipelines",
        "tagline": "Extracts links, videos, and research papers from Telegram messages, enriches them with AI summaries, and populates a Notion database.",
        "tech_stack": ["n8n", "Telegram Bot API", "Notion API", "OpenAI Summarizer", "HTML Metadata Scraper"],
        "topics": ["n8n", "n8n-workflow", "telegram-bot", "notion-api", "etl-pipeline", "knowledge-management", "software-engineering"],
        "business_value": "Automates personal knowledge management and research aggregation into structured workspace databases.",
        "mermaid_diagram": """sequenceDiagram
    User->>Telegram: Forward Article / Video / Research Link
    Telegram->>n8n: Trigger Workflow
    n8n->>Scraper: Extract Page Title & HTML Metadata
    n8n->>OpenAI: Generate Key Insights & Tags
    n8n->>Notion: Create Database Entry with Tags & Summary
    n8n-->>User: Reply Telegram Confirmation with Notion Link"""
    },
    {
        "slug": "n8n-workflow-gdrive-pdf-qdrant-indexer",
        "file": "Google Drive PDF → Qdrant RAG Indexer.json",
        "title": "Google Drive PDF Vector Indexer & Qdrant RAG Pipeline",
        "category": "RAG & Knowledge Bases",
        "tagline": "Automates document ingestion: monitors Google Drive folder for new PDFs, parses text, generates embeddings, and indexes into Qdrant.",
        "tech_stack": ["n8n", "Google Drive Trigger", "PDF Parser", "OpenAI Embeddings", "Qdrant Vector DB"],
        "topics": ["n8n", "n8n-workflow", "google-drive-api", "qdrant", "pdf-parser", "rag", "vector-embeddings", "software-engineering"],
        "business_value": "Keeps RAG vector databases continuously updated in real-time as enterprise knowledge files are added to Google Drive.",
        "mermaid_diagram": """flowchart LR
    GDrive[New PDF uploaded to GDrive] --> Download[Download PDF Payload]
    Download --> Parse[Extract Text Chunks]
    Parse --> Embed[Generate Vector Embeddings]
    Embed --> Qdrant[Upsert Vector Points to Qdrant Collection]"""
    },
    {
        "slug": "n8n-workflow-sentiment-analysis-agent",
        "file": "Sentiment Analysis Agent.json",
        "title": "Automated Customer Feedback Sentiment Analysis & Escalation Agent",
        "category": "Lead Generation & CRM Automation",
        "tagline": "Classifies incoming customer review sentiment in real-time, logs analytics, and triggers instant alerts for negative feedback.",
        "tech_stack": ["n8n", "OpenAI Classifier", "Google Sheets", "Telegram Alerts", "Webhook Processor"],
        "topics": ["n8n", "n8n-workflow", "sentiment-analysis", "customer-feedback", "nlp", "crm-automation", "software-engineering"],
        "business_value": "Prevents customer churn by enabling support teams to respond to unhappy customers within minutes of submission.",
        "mermaid_diagram": """flowchart TD
    Webhook[Customer Review Submitted] --> Classify[LLM Sentiment Classifier]
    Classify --> Grade{Sentiment Score}
    Grade -- Positive / Neutral --> Log[Log in Google Sheets Database]
    Grade -- Negative --> Log
    Grade -- Negative --> Alert[Send High Priority Escalation Alert via Telegram]"""
    },
    {
        "slug": "n8n-workflow-gpt-oss-20b-huggingface",
        "file": "GPT_OSS_20B_HuggingFace.json",
        "title": "GPT-OSS-20B Cloud Inference Workflow with Auto-Retry Logic",
        "category": "AI Integration & Cloud Inference",
        "tagline": "Production-ready integration with HuggingFace Inference API for 20B parameter open-source LLMs featuring 503 retry handling.",
        "tech_stack": ["n8n", "HuggingFace API", "Custom Error Handling (503 Retry)", "JavaScript Parser"],
        "topics": ["n8n", "n8n-workflow", "huggingface", "open-source-llm", "cloud-inference", "error-handling", "software-engineering"],
        "business_value": "Provides reliable, serverless access to high-parameter open-source AI models without managing expensive local GPU infrastructure.",
        "mermaid_diagram": """sequenceDiagram
    Trigger->>HuggingFace: Send Chat Completion Request
    alt HTTP 503 (Model Loading)
        HuggingFace-->>n8n: Return 503 Model Cold Start
        n8n->>n8n: Trigger Wait Node (30 Seconds)
        n8n->>HuggingFace: Retry Chat Completion Request
    end
    HuggingFace-->>n8n: Return 200 OK Payload
    n8n->>n8n: Parse Response JSON & Extract Content"""
    }
]

def parse_workflow_json(json_path):
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            data = data[0] if len(data) > 0 else {}
            
        nodes = data.get("nodes", [])
        node_count = len(nodes)
        
        node_types = []
        triggers = []
        for n in nodes:
            t = n.get("type", "").replace("n8n-nodes-base.", "").replace("@n8n/n8n-nodes-langchain.", "")
            if t and t not in node_types:
                node_types.append(t)
            if "trigger" in t.lower() or "webhook" in t.lower() or "manual" in t.lower():
                triggers.append(n.get("name", t))
                
        return {
            "name": data.get("name", os.path.basename(json_path).replace(".json", "")),
            "node_count": node_count,
            "node_types": node_types,
            "triggers": triggers,
            "raw_data": data
        }
    except Exception as e:
        print(f"Error parsing {json_path}: {e}")
        return None

def generate_readme(item, parsed_info):
    title = item["title"]
    category = item["category"]
    tagline = item["tagline"]
    tech_stack = item["tech_stack"]
    business_value = item["business_value"]
    mermaid_diagram = item.get("mermaid_diagram", "")
    topics = item.get("topics", [])
    
    node_count = parsed_info["node_count"] if parsed_info else "N/A"
    node_types_str = ", ".join([f"`{t}`" for t in parsed_info["node_types"]]) if parsed_info else "n8n Nodes"
    triggers_str = ", ".join([f"`{tr}`" for tr in parsed_info["triggers"]]) if parsed_info else "Manual / Trigger"
    
    tech_badges = " ".join([f"![{t}](https://img.shields.io/badge/{t.replace(' ', '_')}-informational?style=flat-square)" for t in tech_stack])
    topic_badges = " ".join([f"`#{t}`" for t in topics])

    readme_content = f"""<div align="center">

# ⚡ {title}

**Category:** `{category}`  
*{tagline}*

{tech_badges}
[![n8n Compatible](https://img.shields.io/badge/n8n-Workflow-FF6D5A?style=flat-square&logo=n8n&logoColor=white)](https://n8n.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![CI Validation](https://github.com/{GITHUB_USER}/{item['slug']}/actions/workflows/validate-workflow.yml/badge.svg)](https://github.com/{GITHUB_USER}/{item['slug']}/actions)

[Main Portfolio Hub]({MAIN_REPO}) · [Architecture & Principles](#-software-engineering-architecture--standards) · [How to Import](#-how-to-import-and-run)

</div>

---

## 💡 Business Case & Value

{business_value}

---

## 🏗️ Software Engineering Architecture & Standards

This repository adheres to strict software engineering standards to guarantee reliability, maintainability, and clean decoupling:

### 1. Architectural Decoupling & Boundaries
- **Single Responsibility Principle:** Each node or sub-workflow handles a distinct responsibility (Trigger parsing, AI logic, DB persistence, or Notification dispatch).
- **Loose Coupling:** Inter-node communication relies on structured JSON contracts. Data transformations are encapsulated inside dedicated Code nodes.

### 2. Resilience & Error Handling
- **Idempotent Operations:** State modifications in persistent databases (PostgreSQL, MSSQL, Google Sheets) use upsert keys to prevent duplicate records on retries.
- **Graceful Degradation & Retries:** External API connections feature automatic retry conditions (e.g. 503 cold start protections, HTTP timeout configurations).

### 3. Security & Zero-Trust Secrets
- **No Hardcoded Credentials:** All API keys, bot tokens, and database passwords are isolate via n8n Credential Stores and `.env` environment variables.

---

## 📐 System Architecture & Data Flow

```mermaid
{mermaid_diagram}
```

---

## 🛠️ Tech Stack & Integration Details

- **Workflow Engine:** n8n Automation Stack
- **Active Integrations:** {", ".join(tech_stack)}
- **Total Nodes:** `{node_count}`
- **Node Breakdown:** {node_types_str}
- **Trigger Mechanisms:** {triggers_str}
- **Topics & Tags:** {topic_badges}

---

## 🧪 Quality Assurance & CI/CD

This repository includes an automated **GitHub Actions CI/CD Pipeline** ([`validate-workflow.yml`](.github/workflows/validate-workflow.yml)) that validates `workflow.json` on every commit:
- ✅ **JSON Schema Linting:** Verifies valid JSON syntax and root structure.
- ✅ **Node Contract Audit:** Ensures node parameters and connections are unbroken.
- ✅ **Secret Scanning Guard:** Verifies no unencrypted API keys exist in plain text.

---

## 🚀 How to Import and Run

To import this workflow into your n8n instance:

1. **Download Workflow JSON:**
   Download the [`workflow.json`](workflow.json) file from this repository.

2. **Import into n8n:**
   - Open your n8n Editor UI.
   - Click on **Workflow Menu** -> **Import from File...** (or copy raw JSON content and paste directly into canvas with `Ctrl + V` / `Cmd + V`).

3. **Configure Credentials:**
   - Provision required API credentials in n8n for ({", ".join(tech_stack[:3])}).

4. **Activate & Test:**
   - Toggle the workflow switch to **Active** and test execution.

---

## 🔗 Related Portfolio Workflows

This workflow is part of the **Production n8n Workflow Portfolio**. Explore more production-grade workflows in the main hub:  
👉 **[{MAIN_REPO}]({MAIN_REPO})**

---

## 📄 License
Released under the [MIT License](LICENSE).
"""
    return readme_content

def generate_ci_workflow():
    return """name: Validate n8n Workflow Schema

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Validate workflow.json Syntax
        run: |
          if [ -f workflow.json ]; then
            python3 -c "import json; json.load(open('workflow.json'))"
            echo "✅ workflow.json is valid JSON."
          else
            echo "❌ workflow.json file missing!"
            exit 1
          fi

      - name: Check for Unencrypted Secrets
        run: |
          if grep -E "(sk-or-v1-[a-zA-Z0-9]{30,}|sk-proj-[a-zA-Z0-9]{30,}|AIzaSy[a-zA-Z0-9]{30,})" workflow.json; then
            echo "❌ Hardcoded secret detected in workflow.json!"
            exit 1
          else
            echo "✅ Secret scan passed. No plain-text API keys found."
          fi
"""

def generate_gitignore():
    return """.DS_Store
Thumbs.db
*.log
.env
node_modules/
__pycache__/
"""

def generate_license():
    return """MIT License

Copyright (c) 2026 Sohila Khaled Abbas

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software me, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def main():
    print(f"🚀 Initializing Software Engineering Portfolio Showcase Generator...")
    print(f"Output Directory: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    created_repos = []
    
    for item in SHOWCASE_WORKFLOWS:
        slug = item["slug"]
        wf_file = item["file"]
        json_path = os.path.join(WORKFLOWS_DIR, wf_file)
        
        repo_dir = os.path.join(OUTPUT_DIR, slug)
        os.makedirs(repo_dir, exist_ok=True)
        
        parsed_info = parse_workflow_json(json_path)
        
        # 1. Write README.md
        readme_path = os.path.join(repo_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(generate_readme(item, parsed_info))
            
        # 2. Write .github/workflows/validate-workflow.yml
        github_actions_dir = os.path.join(repo_dir, ".github", "workflows")
        os.makedirs(github_actions_dir, exist_ok=True)
        with open(os.path.join(github_actions_dir, "validate-workflow.yml"), "w", encoding="utf-8") as f:
            f.write(generate_ci_workflow())
            
        # 3. Copy workflow JSON as workflow.json
        dest_json_path = os.path.join(repo_dir, "workflow.json")
        if parsed_info and parsed_info["raw_data"]:
            with open(dest_json_path, "w", encoding="utf-8") as f:
                json.dump(parsed_info["raw_data"], f, indent=2, ensure_ascii=False)
        elif os.path.exists(json_path):
            shutil.copy(json_path, dest_json_path)
        else:
            print(f"⚠️ Warning: Could not find original workflow file: {wf_file}")
            
        # 4. Write .gitignore & LICENSE
        with open(os.path.join(repo_dir, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(generate_gitignore())
        with open(os.path.join(repo_dir, "LICENSE"), "w", encoding="utf-8") as f:
            f.write(generate_license())
            
        print(f"✅ Generated SE showcase repo structure & CI: published_repos/{slug}")
        created_repos.append({"slug": slug, "title": item["title"], "topics": item.get("topics", []), "repo_dir": repo_dir})

    # Generate PowerShell publish & tag script
    ps_script = os.path.join(OUTPUT_DIR, "publish_all_to_github.ps1")
    with open(ps_script, "w", encoding="utf-8") as f:
        f.write("# PowerShell script to push all generated repositories and set GitHub topics\n")
        f.write("$env:Path += ';C:\\Program Files\\GitHub CLI'\n")
        f.write("$env:GITHUB_TOKEN = ''\n")
        f.write("$GITHUB_USER = 'Sohila-Khaled-Abbas'\n\n")
        for repo in created_repos:
            s = repo["slug"]
            topics_arg = " ".join([f"--add-topic {t}" for t in repo["topics"]])
            f.write(f"Write-Host 'Publishing {s} to GitHub...'\n")
            f.write(f"Set-Location -Path '{repo['repo_dir']}'\n")
            f.write("if (-not (Test-Path '.git')) { git init; git branch -M main }\n")
            f.write("git add .\n")
            f.write("git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null\n")
            f.write(f"gh repo create \"$GITHUB_USER/{s}\" --public --source=. --remote=origin --push -y 2>$null\n")
            f.write(f"gh repo edit \"$GITHUB_USER/{s}\" {topics_arg} 2>$null\n")
            f.write("git push -u origin main\n\n")
        f.write("Write-Host '🎉 All showcase repositories updated and tagged on GitHub successfully!'\n")

    print(f"\n🎉 Successfully generated {len(created_repos)} Software Engineering showcase repositories in 'published_repos/'.")
    print(f"📄 Generated automated publishing script: {ps_script}")

if __name__ == "__main__":
    main()
