"""
Python script to update GitHub Repository Descriptions and Topics
using either GitHub Personal Access Token (GITHUB_TOKEN) or GitHub CLI (gh).
"""

import os
import json
import subprocess
import urllib.request
import urllib.error

GITHUB_USER = "Sohila-Khaled-Abbas"

REPOSITORIES = [
    {
        "name": "n8n-production-queue-setup",
        "description": "Production-grade n8n workflow portfolio featuring 74 automation pipelines: multi-agent AI chatbots, Qdrant RAG, PostgreSQL/MSSQL state persistence, and CRM integrations.",
        "topics": ["n8n", "n8n-workflows", "automation", "rag", "langchain", "qdrant", "supabase", "etl-pipeline", "ai-agents", "portfolio"]
    },
    {
        "name": "n8n-workflow-gourmet-bistro-customer-service",
        "description": "Multi-agent LangChain restaurant assistant with Qdrant/Supabase RAG, Google Sheets dynamic pricing, order management with 5-min grace cancellation, and Telegram kitchen dispatch.",
        "topics": ["n8n", "n8n-workflow", "langchain", "multi-agent", "rag", "qdrant", "supabase", "telegram-bot", "software-engineering"]
    },
    {
        "name": "n8n-workflow-apple-rag-chatbot-v2",
        "description": "Autonomous RAG chatbot indexing Apple 10-K filings and products using OpenAI embeddings, Qdrant vector store, and conversational memory with hybrid reranking.",
        "topics": ["n8n", "n8n-workflow", "rag", "qdrant", "openai-embeddings", "vector-database", "ai-agent", "software-engineering"]
    },
    {
        "name": "n8n-workflow-upwork-ai-proposal-creator",
        "description": "Automated lead generation pipeline scraping Upwork jobs via Apify, evaluating client requirements with GPT-4, and generating tailored freelance proposals.",
        "topics": ["n8n", "n8n-workflow", "apify", "web-scraping", "openai", "gpt-4", "proposal-generator", "software-engineering"]
    },
    {
        "name": "n8n-workflow-delivery-telegram-bot",
        "description": "Interactive Telegram delivery bot with natural language cart management, LangChain agent, OpenRouter inference, and MSSQL session state persistence.",
        "topics": ["n8n", "n8n-workflow", "telegram-bot", "mssql", "conversational-commerce", "session-persistence", "software-engineering"]
    },
    {
        "name": "n8n-workflow-emaar-towers-lead-qualification",
        "description": "Real estate AI lead qualification agent evaluating buyer budgets, property preferences, and down payment readiness with OpenRouter LLM, CRM logging, and agent routing.",
        "topics": ["n8n", "n8n-workflow", "lead-qualification", "crm-automation", "openrouter", "telegram-bot", "software-engineering"]
    },
    {
        "name": "n8n-workflow-gdrive-pdf-qdrant-indexer",
        "description": "Event-driven ETL pipeline monitoring Google Drive for PDFs, extracting and chunking text, generating embeddings, and upserting vectors into Qdrant for RAG.",
        "topics": ["n8n", "n8n-workflow", "google-drive-api", "qdrant", "pdf-parser", "rag", "vector-embeddings", "software-engineering"]
    },
    {
        "name": "n8n-workflow-sentiment-analysis-agent",
        "description": "Real-time customer feedback sentiment classifier logging sentiment scores to Google Sheets and triggering instant priority alerts for negative reviews.",
        "topics": ["n8n", "n8n-workflow", "sentiment-analysis", "customer-feedback", "nlp", "crm-automation", "software-engineering"]
    },
    {
        "name": "n8n-workflow-telegram-notion-etl",
        "description": "Content curation pipeline extracting links and media from Telegram, generating AI summaries with key takeaways, and persisting structured entries in Notion.",
        "topics": ["n8n", "n8n-workflow", "telegram-bot", "notion-api", "etl-pipeline", "knowledge-management", "software-engineering"]
    },
    {
        "name": "n8n-workflow-gpt-oss-20b-huggingface",
        "description": "Cloud LLM inference workflow integrating HuggingFace API with automatic 503 cold-start retries, Wait node backoff, and robust response parsing.",
        "topics": ["n8n", "n8n-workflow", "huggingface", "open-source-llm", "cloud-inference", "error-handling", "software-engineering"]
    },
    {
        "name": "n8n-workflow-daily-viral-content-radar",
        "description": "Automated trend monitoring pipeline scraping viral content, extracting engagement metrics, classifying topics via AI, and generating daily digest reports.",
        "topics": ["n8n", "n8n-workflow", "content-curation", "trend-analysis", "etl-pipeline", "http-api", "software-engineering"]
    }
]

def update_via_api(token: str):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "n8n-portfolio-updater"
    }
    for repo in REPOSITORIES:
        repo_name = repo["name"]
        url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}"
        data = json.dumps({"description": repo["description"]}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"✅ Description updated for {repo_name}")
        except Exception as e:
            print(f"⚠️ Failed to update description for {repo_name}: {e}")

        # Update topics
        topics_url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/topics"
        topics_data = json.dumps({"names": repo["topics"]}).encode("utf-8")
        req_top = urllib.request.Request(topics_url, data=topics_data, headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"}, method="PUT")
        try:
            with urllib.request.urlopen(req_top) as resp:
                print(f"🏷️ Topics updated for {repo_name}")
        except Exception as e:
            print(f"⚠️ Failed to update topics for {repo_name}: {e}")

def update_via_gh():
    for repo in REPOSITORIES:
        repo_name = repo["name"]
        desc = repo["description"]
        topics_args = " ".join([f"--add-topic {t}" for t in repo["topics"]])
        cmd = f'gh repo edit "{GITHUB_USER}/{repo_name}" --description "{desc}" {topics_args}'
        print(f"Running: {cmd}")
        os.system(cmd)

if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        print(f"Using GITHUB_TOKEN to update {len(REPOSITORIES)} repositories via GitHub API...")
        update_via_api(token)
    else:
        print(f"GITHUB_TOKEN not found in env, attempting GitHub CLI (gh)...")
        update_via_gh()
