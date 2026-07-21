param(
    [switch]$PushToGit = $true
)

$ErrorActionPreference = "Stop"

# Get the directory where the script is located, then move up to project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "Starting n8n Auto-Sync process..." -ForegroundColor Cyan

# 1. Export workflows from the running n8n container
Write-Host "`n[1/3] Exporting workflows from n8n container..." -ForegroundColor Yellow
python scripts/export_workflows.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to export workflows."
    exit $LASTEXITCODE
}

# 2. Update docs/data.json based on exported workflows
Write-Host "`n[2/3] Updating docs and metadata..." -ForegroundColor Yellow
python scripts/generate_docs_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to generate docs data."
    exit $LASTEXITCODE
}

# 3. Commit and push to git
if ($PushToGit) {
    Write-Host "`n[3/3] Committing to git repository..." -ForegroundColor Yellow
    
    # Check if there are any changes
    $status = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($status)) {
        Write-Host "No changes detected. Git repository is up to date." -ForegroundColor Green
    } else {
        git add .
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git commit -m "Auto-update workflows and docs - $timestamp"
        
        Write-Host "Pushing changes to remote..." -ForegroundColor Yellow
        git push
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to push to git repository."
            exit $LASTEXITCODE
        }
        Write-Host "Successfully synced to git repository." -ForegroundColor Green
    }
} else {
    Write-Host "`n[3/3] Skipping git push as requested." -ForegroundColor DarkGray
}

Write-Host "`nAuto-sync process completed successfully!" -ForegroundColor Green
