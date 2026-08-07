# PowerShell script to push all generated repositories and set GitHub descriptions and topics
$env:Path += ';C:\Program Files\GitHub CLI'
$env:GITHUB_TOKEN = ''
$GITHUB_USER = 'Sohila-Khaled-Abbas'

Write-Host 'Publishing n8n-workflow-gourmet-bistro-customer-service to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-gourmet-bistro-customer-service'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-gourmet-bistro-customer-service" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-gourmet-bistro-customer-service" --description "Multi-agent LangChain restaurant assistant with Qdrant/Supabase RAG, Google Sheets dynamic pricing, order management with 5-min grace cancellation, and Telegram kitchen dispatch." --add-topic n8n --add-topic n8n-workflow --add-topic langchain --add-topic multi-agent --add-topic rag --add-topic qdrant --add-topic telegram-bot --add-topic supabase --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-upwork-ai-proposal-creator to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-upwork-ai-proposal-creator'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-upwork-ai-proposal-creator" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-upwork-ai-proposal-creator" --description "Automated lead generation pipeline scraping Upwork jobs via Apify, evaluating client requirements with GPT-4, and generating tailored freelance proposals." --add-topic n8n --add-topic n8n-workflow --add-topic apify --add-topic web-scraping --add-topic openai --add-topic gpt-4 --add-topic proposal-generator --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-emaar-towers-lead-qualification to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-emaar-towers-lead-qualification'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-emaar-towers-lead-qualification" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-emaar-towers-lead-qualification" --description "Real estate AI lead qualification agent evaluating buyer budgets, property preferences, and down payment readiness with OpenRouter LLM, CRM logging, and agent routing." --add-topic n8n --add-topic n8n-workflow --add-topic lead-qualification --add-topic crm-automation --add-topic openrouter --add-topic telegram-bot --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-delivery-telegram-bot to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-delivery-telegram-bot'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-delivery-telegram-bot" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-delivery-telegram-bot" --description "Interactive Telegram delivery bot with natural language cart management, LangChain agent, OpenRouter inference, and MSSQL session state persistence." --add-topic n8n --add-topic n8n-workflow --add-topic telegram-bot --add-topic mssql --add-topic conversational-commerce --add-topic session-persistence --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-apple-rag-chatbot-v2 to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-apple-rag-chatbot-v2'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-apple-rag-chatbot-v2" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-apple-rag-chatbot-v2" --description "Autonomous RAG chatbot indexing Apple 10-K filings and products using OpenAI embeddings, Qdrant vector store, and conversational memory with hybrid reranking." --add-topic n8n --add-topic n8n-workflow --add-topic rag --add-topic qdrant --add-topic openai-embeddings --add-topic vector-database --add-topic ai-agent --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-daily-viral-content-radar to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-daily-viral-content-radar'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-daily-viral-content-radar" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-daily-viral-content-radar" --description "Automated trend monitoring pipeline scraping viral content, extracting engagement metrics, classifying topics via AI, and generating daily digest reports." --add-topic n8n --add-topic n8n-workflow --add-topic content-curation --add-topic trend-analysis --add-topic etl-pipeline --add-topic http-api --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-telegram-notion-etl to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-telegram-notion-etl'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-telegram-notion-etl" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-telegram-notion-etl" --description "Content curation pipeline extracting links and media from Telegram, generating AI summaries with key takeaways, and persisting structured entries in Notion." --add-topic n8n --add-topic n8n-workflow --add-topic telegram-bot --add-topic notion-api --add-topic etl-pipeline --add-topic knowledge-management --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-gdrive-pdf-qdrant-indexer to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-gdrive-pdf-qdrant-indexer'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-gdrive-pdf-qdrant-indexer" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-gdrive-pdf-qdrant-indexer" --description "Event-driven ETL pipeline monitoring Google Drive for PDFs, extracting and chunking text, generating embeddings, and upserting vectors into Qdrant for RAG." --add-topic n8n --add-topic n8n-workflow --add-topic google-drive-api --add-topic qdrant --add-topic pdf-parser --add-topic rag --add-topic vector-embeddings --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-sentiment-analysis-agent to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-sentiment-analysis-agent'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-sentiment-analysis-agent" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-sentiment-analysis-agent" --description "Real-time customer feedback sentiment classifier logging sentiment scores to Google Sheets and triggering instant priority alerts for negative reviews." --add-topic n8n --add-topic n8n-workflow --add-topic sentiment-analysis --add-topic customer-feedback --add-topic nlp --add-topic crm-automation --add-topic software-engineering 2>$null
git push -u origin main

Write-Host 'Publishing n8n-workflow-gpt-oss-20b-huggingface to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-gpt-oss-20b-huggingface'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'feat: update showcase workflow with software engineering architecture, CI/CD, and tags' 2>$null
gh repo create "$GITHUB_USER/n8n-workflow-gpt-oss-20b-huggingface" --public --source=. --remote=origin --push -y 2>$null
gh repo edit "$GITHUB_USER/n8n-workflow-gpt-oss-20b-huggingface" --description "Cloud LLM inference workflow integrating HuggingFace API with automatic 503 cold-start retries, Wait node backoff, and robust response parsing." --add-topic n8n --add-topic n8n-workflow --add-topic huggingface --add-topic open-source-llm --add-topic cloud-inference --add-topic error-handling --add-topic software-engineering 2>$null
git push -u origin main

Write-Host '🎉 All showcase repositories updated with descriptions and tagged on GitHub successfully!'
