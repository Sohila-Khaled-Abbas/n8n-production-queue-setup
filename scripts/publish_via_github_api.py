#!/usr/bin/env python3
"""
publish_via_github_api.py

Automated GitHub Repository Creator & Pusher using GitHub REST API.
Use this script if GitHub CLI ('gh') is not installed on your system.
"""

import os
import sys
import subprocess
import urllib.request
import json

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISHED_REPOS_DIR = os.path.join(PROJECT_ROOT, "published_repos")
GITHUB_USER = "Sohila-Khaled-Abbas"

def create_github_repo(repo_name, token, description="Production-grade n8n workflow showcase"):
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "n8n-Portfolio-Publisher"
    }
    payload = json.dumps({
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": False
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  -> Created GitHub repo: {data.get('html_url')}")
            return data.get("clone_url")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        if "name already exists" in err_body:
            print(f"  -> Repo '{repo_name}' already exists on GitHub. Continuing...")
            return f"https://github.com/{GITHUB_USER}/{repo_name}.git"
        else:
            print(f"  -> HTTP Error {e.code}: {err_body}")
            return None
    except Exception as e:
        print(f"  -> Error creating repo {repo_name}: {e}")
        return None

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        token = sys.argv[1]

    if not token:
        print("❌ Error: GitHub Personal Access Token (PAT) is required.")
        print("\nUsage:")
        print("  python scripts/publish_via_github_api.py YOUR_GITHUB_PAT_TOKEN")
        print("  or set $env:GITHUB_TOKEN='YOUR_TOKEN' and run the script.")
        print("\nGenerate a Token here: https://github.com/settings/tokens (Scope: 'repo')")
        sys.exit(1)

    print("🚀 Publishing all showcase repositories via GitHub REST API...")
    
    if not os.path.exists(PUBLISHED_REPOS_DIR):
        print(f"Error: Directory {PUBLISHED_REPOS_DIR} not found.")
        sys.exit(1)

    subdirs = [d for d in os.listdir(PUBLISHED_REPOS_DIR) if os.path.isdir(os.path.join(PUBLISHED_REPOS_DIR, d))]
    
    for repo_name in subdirs:
        repo_path = os.path.join(PUBLISHED_REPOS_DIR, repo_name)
        print(f"\n📦 Processing {repo_name}...")
        
        # Create Repo on GitHub
        clone_url = create_github_repo(repo_name, token)
        if not clone_url:
            continue
            
        # Git Push
        try:
            # Set remote URL with token authentication for pushing
            authenticated_url = clone_url.replace("https://", f"https://x-access-token:{token}@")
            
            subprocess.run(["git", "remote", "remove", "origin"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", authenticated_url], cwd=repo_path, check=True)
            
            print(f"  -> Pushing main branch to GitHub...")
            result = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Successfully published: https://github.com/{GITHUB_USER}/{repo_name}")
            else:
                print(f"  ❌ Push failed: {result.stderr or result.stdout}")
        except Exception as e:
            print(f"  ❌ Git operation error: {e}")

    print("\n🎉 All repository publishing operations completed!")

if __name__ == "__main__":
    main()
