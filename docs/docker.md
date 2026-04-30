# Docker + Redis Integration Plan for Voice Chatbot

## 1) Goals
- Package the FastAPI service into a stable container for dev and prod.
- Use Redis to store chat history by `session_id`.
- Reduce model re-download time with HuggingFace/Torch cache volumes.

## 2) Current State (Summary)
- Entry point: `main.py` (FastAPI + startup/shutdown).
- Environment configuration via `.env` and `src/config.py`.
- MySQL is in use (via `src/database.py`).
- Chat history is stored in-memory at `src/api/session_history.py`.
- Cart is always taken from the request (`current_cart`), not stored by the AI service.

## 3) Scope
- Required: Docker + Docker Compose + Redis + MySQL.
- MySQL runs inside Docker Compose for consistent environments.
- Only change chat history storage to Redis; do not store carts in the AI service.

## 4) Deployment Architecture (Compose)
- `app`: FastAPI (uvicorn) on port 8000.
- `redis`: Redis 7 for chat history.
- `mysql`: MySQL 8 for application data.
- Volumes:
  - `redis-data`: Redis data.
  - `mysql-data`: MySQL data.
  - `hf-cache`, `torch-cache`: model cache.

## 5) Work Plan (Phases)
### Phase 1: Dockerize the App
1. Create `docker/Dockerfile`.
2. Create `.dockerignore` (exclude `.venv`, `__pycache__`, `.git`, `tests` if not needed).
3. Configure the `uvicorn` startup command in the container.

### Phase 2: Redis for Chat History
1. Add dependency `redis>=5`.
2. Create a Redis client module (for example `src/redis_client.py`).
3. Update `src/api/session_history.py` to read/write Redis by `session_id`.
4. Keep in-memory storage for local runs (Redis off by default).

### Phase 3: Full Docker Compose
1. Create `docker/docker-compose.yml` to run `app` + `mysql` + `redis`.
2. Update `.env` with `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
3. Configure volumes for MySQL, Redis, and model cache.
4. Add healthchecks for MySQL and Redis.
5. Docker Compose overrides `REDIS_ENABLED=true` to enable Redis automatically.

### Phase 4: Testing and Docs
1. Verify `docker compose --env-file .env -f docker/docker-compose.yml up --build` runs cleanly.
2. Update README Docker run instructions.
3. Verify `/health`, MySQL connectivity, and Redis-backed chat history.

## 6) Docker Design Details
### Dockerfile
- Base: `python:3.12-slim`.
- Install minimal system packages: `libsndfile1`, `build-essential`.
- Install `uv` and sync dependencies from `pyproject.toml`.
- Expose port `8000`.
- Entrypoint: `uvicorn main:app --host 0.0.0.0 --port 8000`.

### docker/docker-compose.yml
- `app`:
  - build from Dockerfile.
  - mount model cache: `HF_HOME` and `TORCH_HOME`.
  - `depends_on` redis and mysql (healthcheck).
- `redis`:
  - image `redis:7-alpine`.
  - healthcheck: `redis-cli ping`.
  - volume `redis-data`.
- `mysql`:
  - image `mysql:8`.
  - environment: `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`.
  - healthcheck: `mysqladmin ping`.
  - volume `mysql-data`.

## 7) Required Environment Variables
Update `.env`:
```
# MySQL
DB_HOST=mysql
DB_PORT=3306
DB_USER=app_user
DB_PASSWORD=app_password
DB_NAME=voice_chatbot

# MySQL Container
MYSQL_ROOT_PASSWORD=root_password
```

## 8) Completion Criteria
- `docker compose up --build` starts successfully.
- `/health` returns OK.
- App connects to MySQL successfully.
- Redis is stable and stores chat history by `session_id`.

## 9) Risks and Notes
- The image is large due to `torch/torchaudio` and models.
