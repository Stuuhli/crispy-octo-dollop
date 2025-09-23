# Installation Guide

## 1. System Preparation
- Enable the Ubuntu **universe** repository and refresh the package list:
  ```bash
  sudo add-apt-repository universe
  sudo apt update
  ```
- Install Python tooling (adjust the Python minor version if you use another distribution):
  ```bash
  sudo apt install python3.12-venv python3-pip
  ```

## 2. Python Environment
- Create and activate a virtual environment:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- Install the backend and frontend dependencies:
  ```bash
  pip install -r requirements.txt
  pip install -r requirements_frontend.txt
  ```

## 3. Configuration
- Copy `app/dev.env` (or create it) and set these values:
  - `JWT_SECRET_KEY` – long, randomly generated secret.
  - `JWT_ALGORITHM` – typically `HS256`.
  - `ACCESS_TOKEN_EXPIRE_MINUTES` – access-token lifetime in minutes.
  - Paths for databases/logs (`USER_HISTORY`, `CHAT_STORE_PATH`, …) matching your environment.
- Mirror the same settings in `frontend_gradio/utils/dev_frontend.env` for the frontend.

## 4. Container Images (Apptainer)
The following images are required. Build or pull them in this order:

| Purpose | Image | Command |
| ------- | ----- | ------- |
| LLM serving (Ollama, optional vLLM) | `ollama.sif` | `apptainer pull ollama.sif docker://ollama/ollama` |
| Milvus vector DB | `milvus.v2.5.2.sif` | `apptainer build milvus.v2.5.2.sif docker://milvusdb/milvus:v2.5.2` |
| FastAPI backend | `fastapi_container.sif` | `apptainer build fastapi_container.sif container_recipes/fastapi_recipe.def` |
| Redis | `redis.sif` | `apptainer build redis.sif container_recipes/redis.def` |
| Gradio frontend | `gradio.sif` | `apptainer build gradio.sif container_recipes/gradio.def` |

> Note: Milvus may need additional mounts/configuration from `milvus_configs/`. Use `--fakeroot` if required.

## 5. Start the Services
1. Launch Milvus and its dependencies:
   ```bash
   sudo bash script_milvus.sh
   bash script_backend.sh
   ```
2. Start the frontend/CLI:
   ```bash
   bash script_frontend.sh
   ```

## 6. User and Role Management
- Log in via `/validate_user/{username}`; a successful response returns a JWT.
- Every subsequent API call must set `Authorization: Bearer <access_token>`.
- The CLI stores the token automatically; only admin accounts can run `create` afterward.
- Maintain user-to-collection mappings in `app/user_collection_db.json` (see `helper_scripts/backend_admin.py`).

## 7. Additional Information
- The `data/` directory (PDFs) and `frontend_gradio/utils/dev_frontend.env` are not versioned and must be copied manually.
- Review secrets, log locations, and backup strategy before running in production.

Your local environment is now ready; see `README.md` for operational guidance.
