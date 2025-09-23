# Crispy Octo Dollop

Retrieval-augmented generation stack with a FastAPI backend, Milvus as vector store, Redis for session state, plus a Gradio frontend and CLI. LLM serving (Ollama or vLLM) and ingestion pipelines run inside Apptainer containers.

## Overview
- **Backend**: FastAPI (`app/main.py`) handles authentication, retrieval, and ingestion workflows.
- **Vector DB**: Milvus 2.5.2 with role-based access control.
- **LLM serving**: Ollama or vLLM via Apptainer images.
- **Frontend**: Gradio UI and a companion CLI (`CLI.py`).
- **Authentication**: JWT access tokens; every write endpoint requires an `Authorization: Bearer` header.

## Prerequisites
- Windows with WSL2 (Ubuntu) or a native Linux host.
- Apptainer/Singularity for container builds.
- Python ≥ 3.12.

See [`installation.md`](installation.md) for a detailed setup walkthrough.

## Quick Start
1. **Install dependencies**
   - Create a virtual environment and install requirements (see `installation.md`).
   - Configure `app/dev.env` and `frontend_gradio/utils/dev_frontend.env` (paths, ports, secrets, JWT settings).
2. **Build container images**
   - Build/pull Apptainer images for Milvus, FastAPI, Redis, Gradio, and Ollama.
3. **Launch services**
   ```bash
   sudo bash script_milvus.sh      # Milvus + dependencies
   bash script_backend.sh          # FastAPI / Redis
   bash script_frontend.sh         # CLI / Gradio
   ```
4. **Authenticate and obtain a token**
   - CLI: `validate <username>` prompts for the password and stores the returned JWT.
   - REST: `POST /validate_user/{username}` with `{ "username": "…", "password": "…" }` returns `{ "access_token": …, "token_type": "bearer" }`.
5. **Call protected endpoints**
   - Include `Authorization: Bearer <token>` in every subsequent request.
   - The CLI adds the header automatically after a successful login.

## Authentication & Roles
- Tokens embed `admin` and `collections` claims and expire after 180 minutes by default (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- Admins can create users via the CLI (`create`) or `POST /create_user`; non-admins receive HTTP 403.
- User-to-collection mappings live in `app/user_collection_db.json` and are cached in Redis when sessions start.

## Typical CLI Flow
1. `validate <username>` – authenticate and store the token.
2. `chat <message>` – send messages with the stored Bearer token.
3. `create` – admin-only, provisions Milvus roles for the new user.
4. `quit` – calls `/logout` with the Bearer header and exits the session.

## Unversioned Assets
- `app/dev.env` (local secrets)
- `frontend_gradio/utils/dev_frontend.env`
- `data/` directory containing source PDFs
- Optional Milvus configuration under `milvus_configs/`

## Testing & Quality
- Sanity-check modules with `python3 -m compileall app`.
- Add unit/integration tests for JWT validation and protected endpoints (see `TODO.md`).

## Further Reading
- Admin helpers: `helper_scripts/` for managing users and collections.
- Roadmap: [`TODO.md`](TODO.md) for GraphRAG integration and security tasks.
