from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parents[1]
ENV_PATH = PROJECT_DIR / ".env"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
load_dotenv(ENV_PATH)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    # Render the chat page and inject the configured backend URL.
    return templates.TemplateResponse(
        request=request,
        name="chat_page.html",
        context={
            "backend_url": os.getenv("BACKEND_URL", ""),
        },
    )
