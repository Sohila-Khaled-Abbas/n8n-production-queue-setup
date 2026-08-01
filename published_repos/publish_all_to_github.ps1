# PowerShell script to push all generated repositories to GitHub
$env:Path += ";C:\Program Files\GitHub CLI"
$env:GITHUB_TOKEN = ""
$GITHUB_USER = 'Sohila-Khaled-Abbas'

Write-Host 'Publishing n8n-workflow-gourmet-bistro-customer-service to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-gourmet-bistro-customer-service'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-gourmet-bistro-customer-service" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-gourmet-bistro-customer-service.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-upwork-ai-proposal-creator to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-upwork-ai-proposal-creator'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-upwork-ai-proposal-creator" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-upwork-ai-proposal-creator.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-emaar-towers-lead-qualification to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-emaar-towers-lead-qualification'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-emaar-towers-lead-qualification" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-emaar-towers-lead-qualification.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-delivery-telegram-bot to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-delivery-telegram-bot'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-delivery-telegram-bot" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-delivery-telegram-bot.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-apple-rag-chatbot-v2 to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-apple-rag-chatbot-v2'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-apple-rag-chatbot-v2" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-apple-rag-chatbot-v2.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-daily-viral-content-radar to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-daily-viral-content-radar'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-daily-viral-content-radar" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-daily-viral-content-radar.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-telegram-notion-etl to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-telegram-notion-etl'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-telegram-notion-etl" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-telegram-notion-etl.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-gdrive-pdf-qdrant-indexer to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-gdrive-pdf-qdrant-indexer'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-gdrive-pdf-qdrant-indexer" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-gdrive-pdf-qdrant-indexer.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-sentiment-analysis-agent to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-sentiment-analysis-agent'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-sentiment-analysis-agent" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-sentiment-analysis-agent.git" 2>$null
    git push -u origin main
}

Write-Host 'Publishing n8n-workflow-gpt-oss-20b-huggingface to GitHub...'
Set-Location -Path 'D:\courses\Data Science\Data Engineering\n8n\published_repos\n8n-workflow-gpt-oss-20b-huggingface'
if (-not (Test-Path '.git')) { git init; git branch -M main }
git add .
git commit -m 'Initial release of n8n production showcase workflow'
gh repo create "$GITHUB_USER/n8n-workflow-gpt-oss-20b-huggingface" --public --source=. --remote=origin --push -y 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/n8n-workflow-gpt-oss-20b-huggingface.git" 2>$null
    git push -u origin main
}

Write-Host '🎉 All showcase repositories published successfully!'
