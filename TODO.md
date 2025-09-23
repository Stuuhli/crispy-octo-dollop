# GraphRAG Integration TODO

## Architecture & Infrastructure
- [ ] Add `graphrag` and required drivers (e.g., Neo4j, Weaviate) to `requirements.txt`/`installation.md` and prepare a local test setup.
- [ ] Decide on the graph store (e.g., Neo4j container, SQLite/NetworkX) and wire it into `script_backend.sh` or your orchestration layer.
- [ ] Extend `app/config.py` / `.env` with GraphRAG configuration keys (index paths, cache directories, backend URL).

## Ingestion Pipeline
- [ ] Enhance the existing Milvus ingestion flow (`app/Ingestion_workflows/`) so that a GraphRAG pipeline run is triggered after vector creation.
- [ ] Update document metadata to version node IDs / relationships per collection (`data/` plus new storage for graph indexes).
- [ ] Add automated validation (e.g., `unit_tests/`) that checks vector and graph indexes stay in sync.

## Retrieval & Serving
- [ ] Implement a dedicated retriever (`app/retrievers/graphrag.py`) that executes GraphRAG queries and returns structured citations.
- [ ] Extend the FastAPI endpoint behind `API_CONV_SEND` with `retrieval_mode={vector, graph, hybrid}` and adjust response assembly.
- [ ] Add hybrid logic that merges graph summaries with Milvus context before calling the generator (`VLLM_GEN_URL`).

## CLI & User Flow
- [ ] Add CLI commands (e.g., `chat graph`, `chat hybrid`) and update messaging in `CLI.py`, including fallback when no graph index exists.
- [ ] Provide an administrator reindex workflow (CLI option or standalone script).

## Observability & Testing
- [ ] Extend retrieval logging (`RETRIEVAL_LOG_PATH`) to record graph traversals, nodes used, and answer quality.
- [ ] Add integration tests covering conversations in each mode (graph-only, hybrid, vector-only).

## Documentation & Rollout
- [ ] Update README / `installation.md` with setup steps, ports, and resource requirements for the graph backend.
- [ ] Document deployment and backup strategy for GraphRAG indexes (export/import, health checks).

# JWT Auth TODO
- [x] `app/config.py`: load/document `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (`installation.md`).
- [x] `app/utils/utils_auth.py`: provide token helpers (`create_jwt_token`, `decode_jwt_token`) and retain password hashing.
- [x] `app/main.py`: return a JWT from `/validate_user` and protect routes via `Depends(get_current_user)`.
- [ ] `app/utils/utils_req_templates.py`: add request/response models if we want JWT payloads in OpenAPI responses.
- [x] `CLI.py`: persist the Bearer token after login and send it with subsequent requests.
- [ ] `frontend_gradio/`: refactor API calls to use JWT, add refresh/logout handling if needed.
- [x] Admin-only endpoints (`create_user`, `ingest_file`, `create_collection`, `internal_get_vectordb`) enforce claims.
- [ ] Logging / fraud detection: capture 401/403 events centrally via `utils_logging`.
- [ ] Tests: add unit tests for token creation/expiry (`unit_tests/`) and integration tests with/without valid tokens.
- [x] Documentation: README / `installation.md` now describe secret generation and Bearer headers.
- [ ] Secret management: plan rotation and secure storage (Vault, deployment env vars instead of static `.env`).
