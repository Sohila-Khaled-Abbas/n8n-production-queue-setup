# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-07-06

### Added
- Created this `changelog.md` file to track project version updates.
- Created `contribution.md` containing software engineering and development guidelines.

### Fixed
- **Sticky Note Color Bug**: Pinned n8n and Task Runner versions globally to `2.28.6` across the `docker-compose.yml`, `Dockerfile`, and `Dockerfile.runner`. This pulls the official bugfix for the local Windows UI colorpicker issue (n8n Issue #29899).
- **RAG Indexer Load PDF Node**: Fixed the indexer pipeline in `Apple RAG ChatBot.json`. The `Load PDF` node was missing crucial binary parameters (`type: binary`, `loader: pdfLoader`, `binaryDataKey: data`), causing it to index raw JSON strings of file metadata (filenames, IDs) instead of parsing the actual PDF contents.
- **RAG LLM Reasoning Timeouts**: Upgraded the RAG Chatbot workflow to production-grade:
  - Replaced the local `Ollama Chat Model` (`qwen2.5:1.5b`) with a `Google Gemini Chat Model` node using the pre-existing `googlePalmApi` credentials.
  - Replaced the local `Ollama Model` in the Qdrant retrieval tool with a `Google Gemini Chat Model` node pointing to the same credential.
  - Resolved reasoning loops and Axios/network timeouts during complex multi-step RAG processes.

## [1.0.0] - 2026-07-05
- Initial release of the production-ready n8n stack with autoscaler, backup profile, and Qdrant integration.
