# GraphRAG Integration TODO

## Architektur & Infrastruktur
- [ ] `graphrag` und benötigte Treiber (z.B. Neo4j, Weaviate) in `requirements.txt`/`installation.md` aufnehmen und lokale Testinstallation vorbereiten.
- [ ] Entscheidung für Graph-Speicher (z.B. Neo4j-Container, SQLite/NetworkX) treffen und in `script_backend.sh` bzw. Orchestration einbinden.
- [ ] Konfigurationsschlüssel für GraphRAG (Index-Pfade, Cache-Verzeichnisse, Backend-URL) in `app/config.py` und `.env` ergänzen.

## Datenaufnahme (Ingestion)
- [ ] Bestehenden Milvus-Ingestionspfad (`app/Ingestion_workflows/`) erweitern, sodass nach erfolgreicher Vektor-Erstellung auch ein GraphRAG-Pipeline-Run angestoßen wird.
- [ ] Dokument-Metadaten aktualisieren, damit Knoten-IDs/Rel-Informationen pro Collection versioniert abgelegt werden (`data/` + neuer Speicherort für Graph-Indizes).
- [ ] Automatische Validierung einbauen (z.B. `unit_tests/`), die prüft, ob Graph- und Vektor-Index synchron sind.

## Retrieval & Serving
- [ ] Eigenen Retriever (`app/retrievers/graphrag.py`) erstellen, der GraphRAG-Queries ausführt und Quellen/Citations strukturiert zurückgibt.
- [ ] FastAPI-Endpunkt `API_CONV_SEND` um Parameter `retrieval_mode={vector, graph, hybrid}` erweitern und Antwortaufbereitung anpassen.
- [ ] Hybrid-Logik implementieren, die Graph-Zusammenfassungen und Milvus-Kontext kombiniert, bevor der Generator (`VLLM_GEN_URL`) aufgerufen wird.

## CLI & Nutzerfluss
- [ ] CLI-Kommandos ergänzen (z.B. `chat graph`, `chat hybrid`) und Anzeigetext in `CLI.py` anpassen, inkl. Fallback, falls Graph-Index fehlt.
- [ ] Administrator-Workflow für Reindexierung (CLI-Option oder separates Script) bereitstellen.

## Observability & Tests
- [ ] Retrieval-Logging erweitern (`RETRIEVAL_LOG_PATH`), um Graph-Traversen, verwendete Knoten und Antwortqualität zu protokollieren.
- [ ] Integrationstests schreiben, die typische Konversationen je Modus abdecken (Graph-only, Hybrid, Vector-only).

## Dokumentation & Rollout
- [ ] README/`installation.md` um Setup-Schritte, Ports und Ressourcenbedarf des Graph-Backends erweitern.
- [ ] Deployment- und Backup-Strategie für GraphRAG-Indizes dokumentieren (z.B. Export/Import, Health-Checks).

# JWT Auth TODO
- [ ] `app/config.py`: neue Secrets/ENV-Variablen für `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` definieren und in `.env` dokumentieren.
- [ ] `app/auth.py`: Utility-Funktionen zum Signieren/Verifizieren von JWTs bereitstellen (`create_access_token`, `decode_token`) und Passworthash-Logik beibehalten.
- [ ] `app/main.py`: Login-Flow anpassen – `/validate_user` soll bei Erfolg ein JWT zurückgeben; `start_conversation` & weitere Protected-Routen über `Depends`-Security (`HTTPBearer`) absichern, Redis nur noch für Chat-Memory nutzen.
- [ ] `app/utils/utils_req_templates.py`: Request-/Response-Modelle für Token-Antwort und Auth-Header aktualisieren.
- [ ] `CLI.py`: Token nach erfolgreicher Validierung speichern, bei Folge-Requests als `Authorization: Bearer` senden.
- [ ] `frontend_gradio/`-API-Client (falls vorhanden) auf JWT umstellen und Refresh-Handling (optional) ergänzen.
- [ ] Rolle prüfen: Admin-Only-Endpunkte (`create_user`, `ingest_file`, `create_collection`, `internal_get_vectordb`) mit Claims (`roles`, `is_admin`) absichern.
- [ ] Logging & Fehler: 401/403-Responses vereinheitlichen, unautorisierte Zugriffe auditieren (`utils_logging`).
- [ ] Tests: Unit-Tests für Token-Erstellung/Verfall (`unit_tests/`), Integrationstest für geschützte Route mit/ohne gültigem Token.
- [ ] Doku: README/`installation.md` um Schritt zur Secret-Generierung und Token-Nutzung erweitern.
