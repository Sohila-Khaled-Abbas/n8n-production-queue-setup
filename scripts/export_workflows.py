#!/usr/bin/env python
import json
import os
import subprocess
import sys
import re

# Ensure the workflows/ directory exists
os.makedirs("workflows", exist_ok=True)

# Reconfigure stdout/stderr to UTF-8 on Windows to prevent print crashes on Unicode characters
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def sanitize_filename(name):
    # Remove characters that are invalid in Windows and Unix filenames
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def main():
    print("Step 1: Exporting all workflows inside n8n container...")
    # Export all workflows to a temporary file inside the n8n container
    export_cmd = ["docker", "compose", "exec", "n8n", "n8n", "export:workflow", "--all", "--output=/home/node/all_workflows_temp.json"]
    result = subprocess.run(export_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing n8n export command: {result.stderr or result.stdout}")
        sys.exit(1)
        
    print("Step 2: Copying export file to host...")
    # Copy the file from the container to the host
    cp_cmd = ["docker", "compose", "cp", "n8n:/home/node/all_workflows_temp.json", "workflows/all_workflows_temp.json"]
    result = subprocess.run(cp_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error copying file: {result.stderr or result.stdout}")
        sys.exit(1)

    print("Step 3: Splitting workflows into individual files...")
    temp_path = "workflows/all_workflows_temp.json"
    if not os.path.exists(temp_path):
        print(f"Error: {temp_path} not found.")
        sys.exit(1)

    try:
        with open(temp_path, "r", encoding="utf-8") as f:
            workflows = json.load(f)
            
        print(f"Found {len(workflows)} workflows.")
        for wf in workflows:
            wf_name = wf.get("name", "Unnamed Workflow")
            clean_name = sanitize_filename(wf_name)
            wf_file = f"workflows/{clean_name}.json"
            
            # n8n expects a list containing the workflow object for standard importing
            with open(wf_file, "w", encoding="utf-8") as out:
                json.dump([wf], out, indent=2)
            print(f"  -> Saved: {wf_file}")

    except Exception as e:
        print(f"Error parsing/writing JSON: {e}")
        sys.exit(1)
    finally:
        # Step 4: Cleanup temp files on host
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Cleanup the temp file inside n8n container
        cleanup_cmd = ["docker", "compose", "exec", "n8n", "rm", "/home/node/all_workflows_temp.json"]
        subprocess.run(cleanup_cmd, capture_output=True)

    print("\nSuccess! All workflows successfully exported and split.")

if __name__ == "__main__":
    main()
