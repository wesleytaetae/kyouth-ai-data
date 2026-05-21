import json
import os
import re
import sqlite3
import sys
import time
from typing import Iterable, List, Set

from pydantic import BaseModel, Field
from pypdf import PdfReader

from prompt_mode import prompt_model


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


_load_env_file()

DEFAULT_MODEL = "llama3.1"
SELECTED_MODEL = DEFAULT_MODEL
DEFAULT_RESUME_PATH = os.getenv("RESUME_PATH", "data/resume_d3_eval.pdf")
DEFAULT_DB_PATH = os.getenv("DB_PATH", "data/jobs_d3_eval.db")

SKILL_BATCH_SIZE = 200
MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]


class SkillGapResult(BaseModel):
	gaps: List[str] = Field(default_factory=list)
	resume_skills: List[str] = Field(default_factory=list)
	total_skills: int = 0
	model_used: str = DEFAULT_MODEL
	llm_matches: int = 0
	elapsed_seconds: float = 0.0
	token_estimate: int = 0


def _safe_read_text(path: str) -> str:
	if path.lower().endswith(".pdf"):
		return _extract_pdf_text(path)
	try:
		with open(path, "r", encoding="utf-8", errors="replace") as handle:
			return handle.read()
	except OSError as exc:
		print(f"[Error] Failed to read resume: {exc}")
		return ""


def _extract_pdf_text(path: str) -> str:
	try:
		reader = PdfReader(path)
		parts: List[str] = []
		for page in reader.pages:
			parts.append(page.extract_text() or "")
		return "\n".join(parts)
	except Exception as exc:
		print(f"[Error] Failed to read PDF resume: {exc}")
		return ""


def _chunk_items(items: List[str], size: int) -> Iterable[List[str]]:
	for idx in range(0, len(items), size):
		yield items[idx : idx + size]


def _normalize_skill(value: str) -> str:
	return " ".join(value.strip().lower().split())


def _load_skills_from_db(db_url: str) -> List[str]:
	if not db_url:
		print("[Error] db_url is required.")
		return []

	if not os.path.exists(db_url):
		print(f"[Error] Database not found: {db_url}")
		return []

	try:
		connection = sqlite3.connect(db_url)
	except Exception as exc:
		print(f"[Error] Failed to connect to database: {exc}")
		return []

	try:
		cursor = connection.cursor()
		cursor.execute(
			"SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
		)
		if not cursor.fetchone():
			print("[Error] Table 'jobs' not found in database.")
			return []

		cursor.execute(
			"SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != ''"
		)
		rows = cursor.fetchall()
	except Exception as exc:
		print(f"[Error] Failed to load tech_stack: {exc}")
		return []
	finally:
		try:
			connection.close()
		except Exception:
			pass

	blacklist = {
		"communication",
		"leadership",
		"management",
		"teamwork",
		"problem solving",
		"critical thinking",
	}

	skills: Set[str] = set()
	for (tech_stack,) in rows:
		for part in str(tech_stack).split(","):
			skill = _normalize_skill(part)
			if not skill or skill in blacklist:
				continue
			skills.add(skill)

	return sorted(skills)


def _build_skill_regex(skill: str) -> re.Pattern:
	escaped = re.escape(skill)
	boundary = r"[a-z0-9+./-]"
	return re.compile(rf"(?<!{boundary}){escaped}(?!{boundary})", re.IGNORECASE)


def _extract_resume_skills(resume_text: str, skills: List[str]) -> Set[str]:
	resume_skills: Set[str] = set()
	for skill in skills:
		pattern = _build_skill_regex(skill)
		if pattern.search(resume_text):
			resume_skills.add(skill)
	return resume_skills


def _prompt_llm_gaps(model: str, resume_text: str, skills: List[str]) -> Set[str]:
	if not skills or not resume_text:
		return set()

	all_gaps: Set[str] = set()
	for batch in _chunk_items(skills, SKILL_BATCH_SIZE):
		prompt = (
			"You will receive a resume and a list of skills. "
			"Start with the full skills list, remove any skills that appear in the resume, "
			"and return ONLY the remaining skills as a JSON array. "
			"Choose ONLY from the provided skills list. "
			"Do not infer synonyms unless the exact skill appears in the resume text. "
			"If none are missing, return an empty JSON array. "
			"Return JSON only: no prose, no Markdown, no code fences, no extra keys.\n\n"
			f"RESUME:\n{resume_text}\n\n"
			f"SKILLS:\n{json.dumps(batch, ensure_ascii=False)}"
		)

		last_error = ""
		response = ""
		for attempt in range(1, MAX_RETRIES + 1):
			response = prompt_model(model, prompt)
			try:
				if response.startswith("[Gemini Error]") or response.startswith(
					"[Ollama Error]"
				) or response.startswith("[Error]"):
					raise ValueError(response)

				start = response.find("[")
				end = response.rfind("]")
				if start == -1 or end == -1 or end <= start:
					raise ValueError("No JSON array found")
				payload = response[start : end + 1]
				data = json.loads(payload)
				if not isinstance(data, list):
					raise ValueError("Response is not a list")
				for item in data:
					value = _normalize_skill(str(item))
					if value:
						all_gaps.add(value)
				break
			except Exception as exc:
				last_error = str(exc)
				if last_error.startswith("[Gemini Error]") or last_error.startswith(
					"[Ollama Error]"
				) or last_error.startswith("[Error]"):
					break
				cleaned = " ".join(response.split())
				preview = cleaned[:1200] + ("..." if len(cleaned) > 1200 else "")
				print("Malformed JSON response preview:")
				print(preview)
				print(f"Attempt {attempt} failed: {exc}")
				if attempt < MAX_RETRIES:
					wait_time = BACKOFF_SECONDS[
						min(attempt - 1, len(BACKOFF_SECONDS) - 1)
					]
					print(f"Retrying in {wait_time}s...")
					time.sleep(wait_time)
				else:
					raise

		if last_error.startswith("[Gemini Error]") or last_error.startswith(
			"[Ollama Error]"
		) or last_error.startswith("[Error]"):
			raise ValueError(last_error)

	return all_gaps


def _estimate_tokens(text: str) -> int:
	return max(1, len(text.split()))


def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
	start_time = time.time()

	resume_text = _safe_read_text(input_file_path)
	if not resume_text:
		return SkillGapResult(
			gaps=[],
			resume_skills=[],
			total_skills=0,
			model_used=SELECTED_MODEL,
			elapsed_seconds=0.0,
			token_estimate=0,
		)

	resume_text_normalized = " ".join(resume_text.lower().split())

	skills = _load_skills_from_db(db_url)
	if not skills:
		return SkillGapResult(
			gaps=[],
			resume_skills=[],
			total_skills=0,
			model_used=SELECTED_MODEL,
			elapsed_seconds=0.0,
			token_estimate=_estimate_tokens(resume_text_normalized),
		)

	resume_skills = _extract_resume_skills(resume_text_normalized, skills)
	candidate_skills = [skill for skill in skills if skill not in resume_skills]
	if not candidate_skills:
		return SkillGapResult(
			gaps=[],
			resume_skills=sorted(resume_skills),
			total_skills=len(skills),
			model_used=SELECTED_MODEL,
			llm_matches=0,
			elapsed_seconds=round(time.time() - start_time, 2),
			token_estimate=_estimate_tokens(resume_text_normalized) + len(skills),
		)

	try:
		llm_gap_skills = _prompt_llm_gaps(
			SELECTED_MODEL, resume_text_normalized, candidate_skills
		)
	except Exception as exc:
		print(exc)
		return SkillGapResult(
			gaps=[],
			resume_skills=sorted(resume_skills),
			total_skills=len(skills),
			model_used=SELECTED_MODEL,
			llm_matches=0,
			elapsed_seconds=round(time.time() - start_time, 2),
			token_estimate=_estimate_tokens(resume_text_normalized) + len(skills),
		)
	canonical_skills = set(candidate_skills)
	llm_gap_skills = {skill for skill in llm_gap_skills if skill in canonical_skills}
	llm_gap_skills = {skill for skill in llm_gap_skills if skill not in resume_skills}

	if llm_gap_skills:
		gap_list = sorted(llm_gap_skills)
	else:
		gap_list = sorted(candidate_skills)

	elapsed = round(time.time() - start_time, 2)
	token_estimate = _estimate_tokens(resume_text_normalized) + len(skills)

	return SkillGapResult(
		gaps=gap_list,
		resume_skills=sorted(resume_skills),
		total_skills=len(skills),
		model_used=SELECTED_MODEL,
		llm_matches=len(llm_gap_skills),
		elapsed_seconds=elapsed,
		token_estimate=token_estimate,
	)


def main() -> None:
	global SELECTED_MODEL

	model = DEFAULT_MODEL
	resume_path = DEFAULT_RESUME_PATH
	db_path = DEFAULT_DB_PATH

	args = sys.argv[1:]
	if len(args) == 1:
		if os.path.exists(args[0]):
			resume_path = args[0]
		else:
			model = args[0]
	elif len(args) == 2:
		model = args[0]
		if os.path.exists(args[1]):
			if args[1].lower().endswith(".txt"):
				resume_path = args[1]
			else:
				db_path = args[1]
	elif len(args) >= 3:
		model = args[0]
		resume_path = args[1]
		db_path = args[2]

	SELECTED_MODEL = model

	result = find_skill_gaps(resume_path, db_path)
	print(
		f"gaps={result.gaps} time={result.elapsed_seconds} tokens={result.token_estimate}"
	)


if __name__ == "__main__":
	main()
