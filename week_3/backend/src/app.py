import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import find_skil_gaps
from prompt_mode import prompt_model


CURRENT_FILE = Path(__file__).resolve()
PROJECT_DIR = CURRENT_FILE.parents[1]
ENV_PATH = PROJECT_DIR / ".env"
load_dotenv(ENV_PATH)

WEEK_2_DIR = next(
    (
        candidate
        for candidate in (
            PROJECT_DIR / "week_2",
            CURRENT_FILE.parent.parent / "week_2",
            Path.cwd() / "week_2",
            *[parent / "week_2" for parent in CURRENT_FILE.parents],
        )
        if candidate.exists()
    ),
    None,
)
if WEEK_2_DIR is None:
    raise RuntimeError(
        "Could not locate the week_2 directory needed for prompt_mode.py"
    )

if str(WEEK_2_DIR) not in sys.path:
    sys.path.insert(0, str(WEEK_2_DIR))


def _parse_origins(value: str) -> list[str]:
    # Parse the comma-separated CORS origins from configuration.
    return [origin.strip() for origin in value.split(",") if origin.strip()]


app = FastAPI(title="Resume Helper Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(
        os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000",
        )
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    pdf_filename: str | None = None
    pdf_text: str | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str


def _wants_skill_gap(message: str) -> bool:
    # Check whether the user asked for skill-gap analysis.
    return "find skill gap" in message.lower()


def _wants_resume_summary(message: str) -> bool:
    # Check whether the user asked for a resume summary.
    return "summarize this resume" in message.lower()


def _resolve_db_path() -> str:
    # Resolve the Week 2 database path for both local and container runs.
    raw_path = os.getenv("SKILL_GAP_DB_PATH") or os.getenv(
        "DB_PATH", "data/jobs_d3_eval.db"
    )
    path = Path(raw_path)
    if path.is_absolute():
        return str(path)

    candidate_paths = [
        WEEK_2_DIR / path,
        PROJECT_DIR / path,
        CURRENT_FILE.parent / path,
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            return str(candidate)

    return str(WEEK_2_DIR / path)


def _build_prompt(payload: ChatRequest) -> str:
    # Build the prompt used for normal chat and resume summarization.
    sections = [f"User message:\n{payload.message.strip()}"]

    pdf_text = (payload.pdf_text or "").strip()
    if pdf_text:
        pdf_name = payload.pdf_filename or "uploaded.pdf"
        sections.append(f"Attached PDF ({pdf_name}):\n{pdf_text}")

    sections.append("Respond helpfully and clearly.")
    return "\n\n".join(sections)


def _format_skill_gap_reply(result: find_skil_gaps.SkillGapResult) -> str:
    # Convert the structured gap result into a readable text response.
    if result.gaps:
        gaps_text = ", ".join(result.gaps)
    else:
        gaps_text = "No missing skills found."

    return (
        f"Skill gaps: {gaps_text}\n"
        f"Resume skills found: {len(result.resume_skills)}\n"
        f"Total skills checked: {result.total_skills}\n"
        f"LLM-confirmed matches: {result.llm_matches}\n"
        f"Elapsed seconds: {result.elapsed_seconds}\n"
        f"Token estimate: {result.token_estimate}"
    )


def _run_skill_gap_analysis(payload: ChatRequest, model: str) -> str:
    # Run the Week 2 skill-gap pipeline against uploaded resume text.
    pdf_text = (payload.pdf_text or "").strip()
    if not pdf_text:
        return "[Error] Resume text is required for skill gap analysis."

    db_path = _resolve_db_path()
    if not Path(db_path).exists():
        return f"[Error] Skill gap database not found: {db_path}"

    find_skil_gaps.SELECTED_MODEL = model
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    ) as handle:
        handle.write(pdf_text)
        temp_resume_path = handle.name

    try:
        result = find_skil_gaps.find_skill_gaps(temp_resume_path, db_path)
    finally:
        try:
            os.unlink(temp_resume_path)
        except OSError:
            pass

    return _format_skill_gap_reply(result)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    # Expose a simple status endpoint for checks and debugging.
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> JSONResponse:
    # Route each request to chat, resume summary, or skill-gap analysis.
    model = (payload.model or os.getenv("DEFAULT_MODEL", "llama3.1")).strip()
    pdf_text = (payload.pdf_text or "").strip()
    if pdf_text:
        if _wants_resume_summary(payload.message):
            prompt = _build_prompt(payload)
            reply = prompt_model(model, prompt)
        elif _wants_skill_gap(payload.message):
            reply = _run_skill_gap_analysis(payload, model)
        else:
            reply = _run_skill_gap_analysis(payload, model)
    else:
        prompt = _build_prompt(payload)
        reply = prompt_model(model, prompt)

    status_code = 200
    if reply.startswith("[Error]"):
        status_code = 400
    elif reply.startswith("[Ollama Error]") or reply.startswith("[Gemini Error]"):
        status_code = 502

    return JSONResponse(
        status_code=status_code,
        content=ChatResponse(reply=reply, model=model).model_dump(),
    )
