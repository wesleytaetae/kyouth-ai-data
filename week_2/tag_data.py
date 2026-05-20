import json
import os
import sqlite3
import sys
import time
from typing import Iterable, List, Tuple

from prompt_mode import prompt_model


DEFAULT_MODEL = "llama3.1"
DEFAULT_BATCH_SIZE = 5
MAX_RETRIES = 3
BACKOFF_SECONDS = [2, 4, 8]
MAX_DESC_CHARS = 2000
SELECTED_MODEL = DEFAULT_MODEL


def _chunk_rows(rows: List[Tuple[str, str]], size: int) -> Iterable[List[Tuple[str, str]]]:
    for idx in range(0, len(rows), size):
        yield rows[idx : idx + size]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _build_batch_prompt(batch: List[Tuple[str, str]]) -> str:
    lines = [
        "Extract the technical stack used in each job description.",
        "Return ONLY a JSON array of objects with keys: source_id, tech_stack.",
        "The tech_stack value must be a comma-separated string.",
        "If unsure, make a best-effort guess based on the description.",
        "",
    ]
    for source_id, description in batch:
        clean_desc = _truncate(description, MAX_DESC_CHARS)
        lines.append(f"SOURCE_ID: {source_id}")
        lines.append(f"DESCRIPTION: {clean_desc}")
        lines.append("")
    return "\n".join(lines)


def _extract_json_array(text: str) -> List[dict]:
    text = text.strip()
    if not text:
        return []

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found")

    payload = text[start : end + 1]
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("JSON payload is not a list")
    return data


def _normalize_stack(value: str) -> str:
    if not value:
        return ""
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return ", ".join(parts)


def _prompt_batch(model: str, batch: List[Tuple[str, str]], batch_index: int) -> List[Tuple[str, str]]:
    prompt = _build_batch_prompt(batch)
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
        response = prompt_model(model, prompt)
        try:
            data = _extract_json_array(response)
            if len(data) != len(batch):
                raise ValueError("Mismatch between batch size and response")

            result = []
            for item in data:
                source_id = str(item.get("source_id", "")).strip()
                tech_stack = _normalize_stack(str(item.get("tech_stack", "")).strip())
                if not source_id:
                    raise ValueError("Missing source_id in response")
                result.append((source_id, tech_stack))
            return result
        except Exception as exc:
            last_error = str(exc)
            print(f"[Batch {batch_index}] Attempt {attempt} failed: {last_error}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])

    return _prompt_batch_fallback(model, batch, batch_index, last_error)


def _prompt_batch_fallback(
    model: str,
    batch: List[Tuple[str, str]],
    batch_index: int,
    last_error: str,
) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    print(f"[Batch {batch_index}] Falling back to per-row prompts: {last_error}")

    for source_id, description in batch:
        prompt = (
            "Extract the technical stack from this job description. "
            "Return only a comma-separated list.\n\n"
            f"DESCRIPTION: {_truncate(description, MAX_DESC_CHARS)}"
        )
        response = prompt_model(model, prompt)
        tech_stack = _normalize_stack(response)
        if not tech_stack:
            tech_stack = "Unknown"
        results.append((source_id, tech_stack))

    return results


def tag_data(db_url: str):
    if not db_url:
        print("[Error] db_url is required.")
        return

    if not os.path.exists(db_url):
        print(f"[Error] Database not found: {db_url}")
        return

    try:
        connection = sqlite3.connect(db_url)
    except Exception as exc:
        print(f"[Error] Failed to connect to database: {exc}")
        return

    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        )
        if not cursor.fetchone():
            print("[Error] Table 'jobs' not found in database.")
            return

        cursor.execute(
            "SELECT source_id, description FROM jobs "
            "WHERE tech_stack IS NULL OR tech_stack = ''"
        )
        rows = cursor.fetchall()
        if not rows:
            print("No rows to update.")
            return

        batch_index = 0
        for batch in _chunk_rows(rows, DEFAULT_BATCH_SIZE):
            updates = _prompt_batch(SELECTED_MODEL, batch, batch_index)
            if updates:
                cursor.executemany(
                    "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                    [(tech_stack, source_id) for source_id, tech_stack in updates],
                )
                connection.commit()
                for source_id, tech_stack in updates:
                    print(f"Analyzed Job {source_id}: {tech_stack}")
            batch_index += 1
    except Exception as exc:
        print(f"[Error] {exc}")
    finally:
        try:
            connection.close()
        except Exception:
            pass


def main() -> None:
    global SELECTED_MODEL

    args = sys.argv[1:]
    db_path = "data/jobs_d1.db"

    if len(args) == 1:
        if os.path.exists(args[0]):
            db_path = args[0]
        else:
            SELECTED_MODEL = args[0]
    elif len(args) >= 2:
        SELECTED_MODEL = args[0]
        db_path = args[1]

    tag_data(db_path)


if __name__ == "__main__":
    main()
