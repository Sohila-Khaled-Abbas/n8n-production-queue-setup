# 📜 Changelog

All notable changes to the **n8n Production Autoscaling Stack** will be documented in this file. This project follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-07-13

### ✨ Added
- **HuggingFace Inference API Integration**: Added auto-provisioned `httpHeaderAuth` credential (`HuggingFace API — n8n Stack`) for calling HuggingFace-hosted models (e.g. `openai/gpt-oss-20b`) from n8n workflows.
  - New `.env` variable: `HUGGINGFACE_API_TOKEN` — set your HF token once and the credential is seeded automatically by `n8n-init`.
  - New workflow: `GPT_OSS_20B_HuggingFace.json` — a complete workflow with Chat Trigger → HTTP Request → 503/model-loading retry logic → Response Parser.
- **Updated `provision.js`**: Extended the one-shot credential provisioner to create the HuggingFace `httpHeaderAuth` credential alongside existing PostgreSQL, Redis, WAHA, Ollama, and MSSQL credentials.

---

## [1.2.0] - 2026-07-06

### ✨ Added
- **Workflow Export Automation**: Developed `scripts/export_workflows.py`, a cross-platform Python script that runs on the host and automates exporting all active workflows from n8n's internal PostgreSQL database and splitting them into individual, clean, formatted JSON files in the `workflows/` directory.

### 🔧 Changed
- **Ollama Local Engine Restoration**: Reconfigured both the V1 and V2 workflows (`Apple RAG ChatBot` and `Apple RAG Chatbot V2`) to use local Ollama models (`qwen2.5:3b-4k`) with the shared credential `wDe9MCIO6q1M7Gau` to satisfy local computing preferences.

### 🐛 Fixed
- **Google Drive Trigger Error in V2**: Resolved the `No data with the current filter could be found` error. Corrected the folder watch target from an empty/invalid placeholder ID to the actual PDF folder ID `1kiyeVdh-lP45tH8uV-_8hpPVQc1DR_NK`.
- **Default Data Loader Parser Bug in V2**: Updated the LangChain `Default Data Loader` parameters to specify `"loader": "pdfLoader"` and `"binaryDataKey": "data"`, enabling accurate text extraction from PDF streams.
- **RAG System Prompt Constraints**: Removed artificial instructions limiting the AI agent to only Q1 reports, permitting full reasoning over Q1-Q4 fiscal data.

---

## [1.1.0] - 2026-07-06

### 🐛 Fixed
- **Windows Color Picker UI Freeze**: Globally pinned n8n and Task Runner versions in `docker-compose.yml` to `2.28.6` to pull the patch resolving local Windows UI colorpicker freezes.

---

## [1.0.0] - 2026-07-05

### 🚀 Added
- **Production Queue Stack**: Initial release of the production-ready n8n stack featuring Redis queue-mode workers, autoscaling logic, Qdrant database integration, and WAHA community node deployment.
