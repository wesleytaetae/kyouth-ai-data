# Frontend Service

This frontend serves the chat UI for the resume helper app on `http://127.0.0.1:8000/`.

## Run with Docker Compose

From `week_3/`:

```bash
docker compose up --build frontend
```

Open `http://127.0.0.1:8000/`.

## Build and run manually

Build from the repository root:

```bash
docker build -f week_3/frontend/Dockerfile -t frontend week_3/frontend
```

Run it with the shared env file:

```bash
docker run --rm --env-file week_3/.env -p 8000:8000 frontend
```

## Required env values

The frontend reads `BACKEND_URL` from `week_3/.env`:

```env
BACKEND_URL=http://127.0.0.1:8001/chat
```

## Notes

- The upload input supports both `.pdf` and `.txt` files.
- When a file is attached, the frontend sends the extracted text to the backend as JSON.
