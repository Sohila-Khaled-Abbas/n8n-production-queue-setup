#!/usr/bin/env python3
"""
publish_workflows_portfolio.py

Automated Portfolio Showcase Generator for n8n Workflows.
Generates standalone GitHub repository structures for top production workflows,
complete with custom README.md files, metadata, badges, workflow JSON files, and git setup scripts.
"""

import os
import json
import re
import sys
import shutil

# Reconfigure stdout/stderr to UTF-8 on Windows to prevent UnicodeEncodeError on emojis
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

# Curated List of Top Production Showcase Workflows
SHOWCASE_WORKFLOWS = [
    {
        "slug": "n8n-workflow-gourmet-bistro-customer-service",
        "file": "Gourmet Bistro Customer Service.json",
        "title": "Gourmet Bistro Multi-Agent AI Customer Service & Ordering System",
        "category": "AI Chatbots & Conversational Commerce",
        "tagline": "Multi-agent LangChain structure for restaurant customer service, RAG vector search, order creation, and kitchen dispatch.",
        "tech_stack": ["n8n", "LangChain Multi-Agent", "Qdrant Vector DB", "Google Sheets", "Supabase PostgreSQL", "Telegram Bot API"],
        "business_value": "Enforces strict business rules (phone validation, delivery checks, 5-minute cancellation grace period) while reducing front-of-house customer service load by up to 80%."
    },
    {
        "slug": "n8n-workflow-upwork-ai-proposal-creator",
        "file": "Upwork AI Proposal Creator.json",
        "title": "Upwork AI Automated Proposal & Job Lead Scraper",
        "category": "Productivity & Lead Generation",
        "tagline": "Scrapes target Upwork job postings via Apify, analyzes job requirements using LLMs, and auto-drafts tailored proposal proposals.",
        "tech_stack": ["n8n", "Apify Upwork Scraper", "LangChain Agent", "OpenAI GPT-4", "JavaScript"],
        "business_value": "Saves agency owners and freelancers up to 10+ hours per week by automating top-of-funnel freelance job qualification and proposal drafting."
    },
    {
        "slug": "n8n-workflow-emaar-towers-lead-qualification",
        "file": "Emaar Towers Lead Qualification Agent.json",
        "title": "Emaar Towers Real Estate Lead Qualification AI Agent",
        "category": "Lead Generation & CRM",
        "tagline": "High-end real estate lead filtering agent that qualifies buyers based on budget, down payment capacity, and location preferences.",
        "tech_stack": ["n8n", "LangChain Agent", "OpenRouter API", "Google Sheets CRM", "Telegram Alerts"],
        "business_value": "Filters out unqualified leads automatically and alerts senior real estate brokers immediately for high-budget luxury inquiries."
    },
    {
        "slug": "n8n-workflow-delivery-telegram-bot",
        "file": "Delivery Telegram Bot.json",
        "title": "Interactive Food Delivery Telegram Bot with MSSQL Session Persistence",
        "category": "AI Chatbots & Conversational Commerce",
        "tagline": "Conversational commerce bot enabling natural language food ordering with durable state persistence in MSSQL.",
        "tech_stack": ["n8n", "Telegram Trigger", "LangChain Agent", "MSSQL", "OpenRouter"],
        "business_value": "Provides 24/7 interactive ordering directly inside messaging apps with automatic session recovery across chat restarts."
    },
    {
        "slug": "n8n-workflow-apple-rag-chatbot-v2",
        "file": "Apple RAG Chatbot V2.json",
        "title": "Apple Products Technical Support RAG AI Agent (V2)",
        "category": "RAG & Knowledge Bases",
        "tagline": "Retrieval-Augmented Generation (RAG) assistant indexing Apple technical support documentation for context-aware Q&A.",
        "tech_stack": ["n8n", "Qdrant Vector DB", "OpenAI Embeddings", "LangChain Conversational Agent", "Chat Trigger"],
        "business_value": "Eliminates AI hallucinations by grounding responses strictly in verified product documentation with source citation."
    },
    {
        "slug": "n8n-workflow-daily-viral-content-radar",
        "file": "Daily Viral Content Radar (AnyAPI).json",
        "title": "Daily Viral Content Radar & Multi-API Trend Aggregator",
        "category": "Productivity & Content ETL Pipelines",
        "tagline": "Monitors social platforms and APIs daily, extracts high-performing content trends, and generates AI executive summaries.",
        "tech_stack": ["n8n", "HTTP Request (APIs)", "LLM Summarizer", "Google Sheets", "Email Digest"],
        "business_value": "Automates content curation and market trend monitoring, providing content teams with daily viral insights effortlessly."
    },
    {
        "slug": "n8n-workflow-telegram-notion-etl",
        "file": "AI Learning Pipeline Telegram to Notion ETL.json",
        "title": "AI Learning Pipeline: Telegram to Notion Knowledge ETL",
        "category": "Productivity & Content ETL Pipelines",
        "tagline": "Extracts links, videos, and research papers from Telegram messages, enriches them with AI summaries, and populates a Notion database.",
        "tech_stack": ["n8n", "Telegram Bot API", "Notion API", "OpenAI Summarizer", "HTML Metadata Scraper"],
        "business_value": "Automates personal knowledge management and research aggregation into structured workspace databases."
    },
    {
        "slug": "n8n-workflow-gdrive-pdf-qdrant-indexer",
        "file": "Google Drive PDF → Qdrant RAG Indexer.json",
        "title": "Google Drive PDF Vector Indexer & Qdrant RAG Pipeline",
        "category": "RAG & Knowledge Bases",
        "tagline": "Automates document ingestion: monitors Google Drive folder for new PDFs, parses text, generates embeddings, and indexes into Qdrant.",
        "tech_stack": ["n8n", "Google Drive Trigger", "PDF Parser", "OpenAI Embeddings", "Qdrant Vector DB"],
        "business_value": "Keeps RAG vector databases continuously updated in real-time as enterprise knowledge files are added to Google Drive."
    },
    {
        "slug": "n8n-workflow-sentiment-analysis-agent",
        "file": "Sentiment Analysis Agent.json",
        "title": "Automated Customer Feedback Sentiment Analysis & Escalation Agent",
        "category": "Lead Generation & CRM Automation",
        "tagline": "Classifies incoming customer review sentiment in real-time, logs analytics, and triggers instant alerts for negative feedback.",
        "tech_stack": ["n8n", "OpenAI Classifier", "Google Sheets", "Telegram Alerts", "Webhook Processor"],
        "business_value": "Prevents customer churn by enabling support teams to respond to unhappy customers within minutes of submission."
    },
    {
        "slug": "n8n-workflow-gpt-oss-20b-huggingface",
        "file": "GPT-OSS-20B HuggingFace Inference Workflow",
        "file": "GPT_OSS_20B_HuggingFace.json",
        "title": "GPT-OSS-20B Cloud Inference Workflow with Auto-Retry Logic",
        "category": "AI Integration & Cloud Inference",
        "tagline": "Production-ready integration with HuggingFace Inference API for 20B parameter open-source LLMs featuring 503 retry handling.",
        "tech_stack": ["n8n", "HuggingFace API", "Custom Error Handling (503 Retry)", "JavaScript Parser"],
        "business_value": "Provides reliable, serverless access to high-parameter open-source AI models without managing expensive local GPU infrastructure."
    }
]

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def parse_workflow_json(json_path):
    """Parses a workflow JSON to extract node statistics and integration types."""
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
    slug = item["slug"]
    
    node_count = parsed_info["node_count"] if parsed_info else "N/A"
    node_types_str = ", ".join([f"`{t}`" for t in parsed_info["node_types"]]) if parsed_info else "n8n Nodes"
    triggers_str = ", ".join([f"`{tr}`" for tr in parsed_info["triggers"]]) if parsed_info else "Manual / Trigger"
    
    tech_badges = " ".join([f"![{t}](https://img.shields.io/badge/{t.replace(' ', '_')}-informational?style=flat-square)" for t in tech_stack])

    readme_content = f"""<div align="center">

# ⚡ {title}

**Category:** `{category}`  
*{tagline}*

{tech_badges}
[![n8n Compatible](https://img.shields.io/badge/n8n-Workflow-FF6D5A?style=flat-square&logo=n8n&logoColor=white)](https://n8n.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

[Main Portfolio Hub]({MAIN_REPO}) · [How to Import](#-how-to-import-and-run) · [Workflow Architecture](#-workflow-architecture)

</div>

---

## 💡 Business Case & Value

{business_value}

---

## 🛠️ Tech Stack & Integrations

- **Workflow Orchestrator:** n8n Automation Engine
- **Integrations:** {", ".join(tech_stack)}
- **Total Workflow Nodes:** `{node_count}`
- **Active Node Types:** {node_types_str}
- **Triggers:** {triggers_str}

---

## 📐 Workflow Architecture & Nodes

This repository contains the production-grade n8n workflow exported as standard JSON (`workflow.json`). 

### Core Components
1. **Trigger Layer:** Executes automatically based on incoming events, webhooks, or scheduled crons.
2. **AI & Processing Layer:** Processes natural language or payload data, enforcing validation rules and error retries.
3. **Storage & Notification Layer:** Persists state to database systems (PostgreSQL, MSSQL, Google Sheets) and alerts relevant channels (Telegram, Email, Notion).

---

## 🚀 How to Import and Run

To import this workflow into your n8n instance:

1. **Download Workflow JSON:**
   Download the [`workflow.json`](workflow.json) file from this repository.

2. **Import into n8n:**
   - Open your n8n Editor UI.
   - Click on the **Workflow menu** (top right) -> **Import from File...** (or copy raw JSON content and paste directly into canvas with `Ctrl + V` / `Cmd + V`).

3. **Configure Credentials:**
   - Set up required API credentials in n8n for the respective integrations ({", ".join(tech_stack[:3])}).

4. **Activate:**
   - Toggle the workflow switch to **Active** and test execution.

---

## 🔗 Related Portfolio Workflows

This workflow is part of the **Production n8n Workflow Portfolio**. Explore more production-grade workflows in the primary repository:
👉 **[{MAIN_REPO}]({MAIN_REPO})**

---

## 📄 License
This workflow is open-source and released under the [MIT License](LICENSE).
"""
    return readme_content

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
    print(f"🚀 Initializing Showcase Portfolio Generator...")
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
            
        # 2. Copy workflow JSON as workflow.json
        dest_json_path = os.path.join(repo_dir, "workflow.json")
        if parsed_info and parsed_info["raw_data"]:
            with open(dest_json_path, "w", encoding="utf-8") as f:
                json.dump(parsed_info["raw_data"], f, indent=2, ensure_ascii=False)
        elif os.path.exists(json_path):
            shutil.copy(json_path, dest_json_path)
        else:
            print(f"⚠️ Warning: Could not find original workflow file: {wf_file}")
            
        # 3. Write .gitignore & LICENSE
        with open(os.path.join(repo_dir, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(generate_gitignore())
        with open(os.path.join(repo_dir, "LICENSE"), "w", encoding="utf-8") as f:
            f.write(generate_license())
            
        print(f"✅ Generated showcase repo structure: published_repos/{slug}")
        created_repos.append({"slug": slug, "title": item["title"], "repo_dir": repo_dir})

    # Generate helper publish PowerShell & Bash scripts
    ps_script = os.path.join(OUTPUT_DIR, "publish_all_to_github.ps1")
    with open(ps_script, "w", encoding="utf-8") as f:
        f.write("# PowerShell script to push all generated repositories to GitHub\n")
        f.write("$GITHUB_USER = 'Sohila-Khaled-Abbas'\n\n")
        for repo in created_repos:
            s = repo["slug"]
            f.write(f"Write-Host 'Publishing {s} to GitHub...'\n")
            f.write(f"Set-Location -Path '{repo['repo_dir']}'\n")
            f.write("if (-not (Test-Path '.git')) { git init; git branch -M main }\n")
            f.write("git add .\n")
            f.write("git commit -m 'Initial release of n8n production showcase workflow'\n")
            f.write(f"gh repo create \"$GITHUB_USER/{s}\" --public --source=. --remote=origin --push -y 2>$null\n")
            f.write("if ($LASTEXITCODE -ne 0) {\n")
            f.write(f"    git remote add origin \"https://github.com/$GITHUB_USER/{s}.git\" 2>$null\n")
            f.write("    git push -u origin main\n")
            f.write("}\n\n")
        f.write("Write-Host '🎉 All showcase repositories published successfully!'\n")

    print(f"\n🎉 Successfully created {len(created_repos)} standalone showcase repositories inside 'published_repos/'.")
    print(f"📄 Generated automated publishing script: {ps_script}")

if __name__ == "__main__":
    main()
