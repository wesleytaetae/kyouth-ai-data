import json
import os
import sys
import urllib.error
import urllib.request


OLLAMA_MODELS = {"llama3.1", "phi3", "deepseek-r1", "deepseek-r1:1.5b"}
GEMINI_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
}
_ENV_LOADED = False


def _load_env_file() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


def _post_json(url: str, payload: dict, timeout: float = 60.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def _get_ollama_timeout() -> float:
    raw_timeout = os.getenv("OLLAMA_TIMEOUT", "60")
    try:
        return max(float(raw_timeout), 1.0)
    except ValueError:
        return 60.0


def _prompt_ollama(model: str, prompt: str) -> str:
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    url = f"{ollama_base_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "top_k": 1,
            "top_p": 1,
            "seed": 0,
        },
    }
    try:
        data = _post_json(url, payload, timeout=_get_ollama_timeout())
        return data.get("response", "").strip()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        return f"[Ollama Error] {exc.code} {exc.reason}. {detail}".strip()
    except Exception as exc:
        return f"[Ollama Error] {exc}"


def _prompt_gemini(model: str, prompt: str) -> str:
    _load_env_file()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "[Gemini Error] Missing GOOGLE_API_KEY or GEMINI_API_KEY env var."

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent?key="
        + api_key
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "topP": 1, "topK": 1},
    }
    try:
        data = _post_json(url, payload, timeout=10.0)
        candidates = data.get("candidates") or []
        if not candidates:
            return f"[Gemini Error] Empty response. {data}"
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return f"[Gemini Error] No text parts. {data}"
        return str(parts[0].get("text", "")).strip()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        return f"[Gemini Error] {exc.code} {exc.reason}. {detail}".strip()
    except Exception as exc:
        return f"[Gemini Error] {exc}"


def prompt_model(model: str, prompt: str) -> str:
    model = (model or "").strip()
    prompt = (prompt or "").strip()
    if not model:
        return "[Error] Model is required."
    if not prompt:
        return "[Error] Prompt is required."

    if model in GEMINI_MODELS or model.startswith("gemini-"):
        return _prompt_gemini(model, prompt)
    if model in OLLAMA_MODELS or model:
        return _prompt_ollama(model, prompt)

    return "[Error] Unsupported model."


def main() -> None:
    if len(sys.argv) >= 3:
        model = sys.argv[1]
        prompt = " ".join(sys.argv[2:])
    else:
        print("[Error] Usage: uv run prompt_mode.py [model] [prompt]")
        return

    response = prompt_model(model, prompt)
    print("\n--- RESPONSE ---\n")
    print(response)


if __name__ == "__main__":
    main()
