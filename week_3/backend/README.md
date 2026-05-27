# Backend Service

This backend exposes `POST /chat` with FastAPI and reuses `week_2` code for both prompt mode and skill-gap analysis.

## Endpoint

Request body:

```json
{
  "message": "Improve this resume summary",
  "pdf_filename": "resume.pdf",
  "pdf_text": "Extracted resume text",
  "model": "llama3.1"
}
```

Response body:

```json
{
  "reply": "Model output here",
  "model": "llama3.1"
}
```

If `pdf_text` is present, the backend ignores the user message and runs `week_2/find_skil_gaps.py`.

## Run with Docker Compose

From `week_3/`:

```bash
docker compose up --build backend
```

The backend is available at `http://127.0.0.1:8001/chat`.

## Build and run manually

Because this image needs `week_2`, build it from the repository root:

```bash
docker build -f week_3/backend/Dockerfile -t backend .
```

Run it with the shared env file and host Ollama access:

```bash
docker run --rm \
  --env-file week_3/.env \
  --add-host host.docker.internal:host-gateway \
  -p 8001:8001 \
  backend
```

## Required env values

Typical `week_3/.env` values:

```env
DEFAULT_MODEL=llama3.1
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_TIMEOUT=240
SKILL_GAP_DB_PATH=data/jobs_d3_eval.db
```

`SKILL_GAP_DB_PATH` is resolved relative to `week_2/` unless you provide an absolute path.
