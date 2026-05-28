# Week 3

## Documentation

### Project Overview

This project builds and containerizes a full-stack chat application with three main parts:

- a FastAPI frontend that serves the chat UI
- a FastAPI backend that exposes a JSON chat API
- an AI integration layer that reuses the Week 2 model utilities for Ollama, Gemini, and skill-gap analysis

The frontend runs on `http://127.0.0.1:8000/`. The backend runs on `http://127.0.0.1:8001/chat`. Regular chat messages are sent to the Week 2 `prompt_mode.py` module. When a resume is uploaded, the backend can either run Week 2 `find_skil_gaps.py` or summarize the uploaded resume, depending on the user’s text instruction.

### Setup Instructions

Prerequisites:

- Docker
- Docker Compose
- Optional for manual local setup: `uv` and Python 3.14
- Optional for Ollama usage: a running Ollama server on the host machine

Create the environment file in `week_3/`:

```bash
cp .env.example .env
```

Example `week_3/.env`:

```env
BACKEND_URL=http://127.0.0.1:8001/chat
DEFAULT_MODEL=llama3.1
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_TIMEOUT=240
SKILL_GAP_DB_PATH=data/jobs_d3_eval.db
# GEMINI_API_KEY=your_key_here
```

Notes on environment variables:

- `BACKEND_URL` is read by the frontend and injected into the HTML template.
- `DEFAULT_MODEL` is the backend fallback model when the request does not specify one.
- `OLLAMA_BASE_URL` points the backend container to Ollama running on the host machine.
- `OLLAMA_TIMEOUT` controls how long the backend waits for Ollama responses.
- `SKILL_GAP_DB_PATH` points to the Week 2 database used by `find_skil_gaps.py`.
- Secrets such as `GEMINI_API_KEY` should stay in `.env` and must not be committed.

Run locally with Docker Compose from `week_3/`:

```bash
docker compose up --build
```

If you need a clean rebuild:

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

Manual setup is also supported.

Important:

- `docker compose` reads `week_3/.env` and passes those values into the containers.
- For manual `uv` runs, export the same environment variables in your shell first, or place equivalent `.env` files where each service expects them.

Frontend:

```bash
cd frontend
uv sync
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000
```

Backend:

```bash
cd backend
uv sync
uv run uvicorn src.app:app --host 0.0.0.0 --port 8001
```

Example manual shell exports:

```bash
export BACKEND_URL=http://127.0.0.1:8001/chat
export DEFAULT_MODEL=llama3.1
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_TIMEOUT=240
export SKILL_GAP_DB_PATH=data/jobs_d3_eval.db
```

For manual non-Docker runs, make sure these values are available in the shell and make sure the Week 2 dependencies and data are present in the repository.

### Usage

Start the application:

```bash
cd week_3
docker compose up --build
```

Access the frontend at:

```text
http://127.0.0.1:8000/
```

Expected inputs:

- a normal user message in the chat textbox
- an optional model selection from:
  - `llama3.1`
  - `phi3`
  - `deepseek-r1:1.5b`
  - `gemini-2.5-flash`
  - `gemini-2.5-flash-lite`
  - `gemini-3-flash-preview`
- an optional `.pdf` or `.txt` resume upload

Expected outputs:

- for plain chat: a model-generated response returned by the backend
- for resume upload with `find skill gap`: a skill-gap summary containing missing skills, resume skill count, total checked skills, LLM-confirmed matches, elapsed time, and token estimate
- for resume upload with `summarize this resume`: a model-generated summary of the uploaded resume text

Behavior:

- If no file is uploaded, the backend uses Week 2 `prompt_mode.py`.
- If a file is uploaded and the message contains `find skill gap`, the backend runs Week 2 `find_skil_gaps.py`.
- If a file is uploaded and the message contains `summarize this resume`, the backend sends the uploaded resume text through the normal AI prompt flow.
- If a file is uploaded and neither phrase is present, the backend currently defaults to skill-gap analysis.

### API / Function Reference

Backend endpoints:

- `GET /health`
  - Returns `{"status": "ok"}`
- `POST /chat`
  - Accepts JSON
  - Used for normal chat, resume skill-gap analysis, and resume summarization

Example `POST /chat` payload:

```json
{
  "message": "Help me improve my resume summary",
  "model": "llama3.1",
  "pdf_filename": "resume.pdf",
  "pdf_text": "Extracted text from the uploaded file"
}
```

Response format:

```json
{
  "reply": "Backend response text",
  "model": "llama3.1"
}
```

Status behavior:

- `200` for successful responses
- `400` for request or local validation errors
- `502` for upstream Ollama or Gemini failures

Key frontend JavaScript functions in `frontend/src/templates/chat_page.html`:

- `extractPdfText(file)`
  - extracts text from uploaded PDFs using `pdfjs`
- `extractFileText(file)`
  - routes file handling to PDF extraction or plain text reading
- `addMessage(role, content, variant)`
  - renders messages into the chat history panel
- `resetComposer()`
  - clears the message box, file input, and file state after submission
- `chatForm.addEventListener("submit", ...)`
  - builds the JSON payload and sends the request to the backend with `fetch`

Service interaction:

- The frontend container serves HTML on port `8000`.
- The backend container serves the API on port `8001`.
- The frontend reads `BACKEND_URL` from `.env` and sends JSON requests to the backend.
- In Docker Compose, both services are started together and the backend is additionally configured with `extra_hosts` so it can reach Ollama on the host via `host.docker.internal`.

### Data / Assumptions

Primary request data between frontend and backend:

```json
{
  "message": "string",
  "model": "string",
  "pdf_filename": "string or null",
  "pdf_text": "string or null"
}
```

Assumptions:

- Uploaded files are either `.pdf` or `.txt`.
- PDF text extraction happens in the browser before the request is sent.
- Resume analysis depends on the Week 2 database file configured by `SKILL_GAP_DB_PATH`.
- The backend expects JSON and does not accept multipart file uploads directly.
- If a file is uploaded, the typed user message is used as an instruction to decide whether to summarize the resume or find skill gaps.

Data flow:

1. The user opens the frontend in the browser.
2. The frontend loads `BACKEND_URL` from the FastAPI template context.
3. The user enters a message, optionally selects a model, and may upload a PDF or TXT file.
4. The browser extracts file text locally and sends a JSON payload to `POST /chat`.
5. The backend checks whether `pdf_text` is present.
6. If `pdf_text` is absent, the backend builds a prompt and calls Week 2 `prompt_mode.py`.
7. If `pdf_text` is present and the message contains `summarize this resume`, the backend builds a prompt and summarizes the uploaded resume with the selected model.
8. If `pdf_text` is present and the message contains `find skill gap`, the backend writes the text to a temporary file and calls Week 2 `find_skil_gaps.py`.
9. If `pdf_text` is present and neither phrase is present, the backend currently defaults to skill-gap analysis.
10. The backend returns JSON with `reply` and `model`.
11. The frontend renders the response in the chat history and resets the composer state.

### Testing

Frontend testing:

- Open `http://127.0.0.1:8000/`
- Send a normal chat message and verify an assistant response appears
- Upload a `.pdf` resume, type `find skill gap`, and verify the backend returns a skill-gap summary
- Upload a `.txt` resume, type `find skill gap`, and verify the same skill-gap flow works
- Upload a `.pdf` or `.txt` resume, type `summarize this resume`, and verify the backend returns a resume summary
- Verify the message box and file input reset after every submission

Backend testing:

- Health check:

```bash
curl http://127.0.0.1:8001/health
```

- Plain chat request:

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Say hello","model":"llama3.1","pdf_filename":null,"pdf_text":null}'
```

- Resume skill-gap request:

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"find skill gap","model":"llama3.1","pdf_filename":"resume.txt","pdf_text":"Python SQL Docker"}'
```

- Resume summary request:

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"summarize this resume","model":"llama3.1","pdf_filename":"resume.txt","pdf_text":"Python SQL Docker"}'
```

Docker communication checks:

- Start both services with `docker compose up --build`
- Confirm the frontend loads on port `8000`
- Confirm the frontend can successfully call the backend on port `8001`
- Confirm Ollama-backed chat works when `OLLAMA_BASE_URL` points to `host.docker.internal`

### Limitations
- No persistence when it comes to chat history or uploaded files. The UI only shows the current session and the backend processes each request statelessly.
- Resume upload routing depends on simple phrase matching such as `find skill gap` and `summarize this resume`, so unsupported wording may not trigger the intended branch.


### Architecture Reflection

**Design Choices**
I separated the frontend and backend to keep concerns clean: the UI can evolve independently from the API and model orchestration. This also makes it easier to reuse Week 2 logic from the backend without coupling it to presentation code. Containerizing each service with Docker keeps dependencies isolated and makes local setup consistent across machines; Docker Compose then provides a single, repeatable way to run both services together.

**Trade-offs**
I prioritized ease of deployment and clarity over raw performance and feature depth. A simple HTML/JS frontend is faster to build and easier to debug, but it limits advanced UX features like streaming responses, rich state management, or offline storage. Using Compose over a single monolith improves modularity, but adds some overhead and cross-service configuration complexity.

**Improvements**
With more time, I would add persistent storage for chat history and uploads, plus user authentication. I would also consider a more robust frontend framework for better UI state, file handling, and error recovery. Finally, I would add cloud deployment with environment-specific configuration, observability (logging/metrics), and scaling for higher traffic.
