### Project Overview

- This project builds a small, end-to-end LLM-driven workflow for skill gap analysis.
- It starts by taking job listings stored in a sqlite database and tagging each listing with a clean, comma-separated tech stack using either a local Ollama model or a Gemini model.
- The tagged database is then compared against a resume text file/pdf file (extract text with pypdf) to produce a deterministic gap list, with retries and error handling around LLM calls.
- The output is a structured list of missing skills, along with lightweight metadata (timing and token estimates), so the results can be validated and compared across multiple runs.

### Setup Instructions
- Prerequisites: Python 3.14+, uv, access to a tagged sqlite DB, and Ollama or a (optional) Gemini API key.
- Install uv (if needed):

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

- Create and activate a venv:

```bash
cd week_2
uv venv
source .venv/bin/activate
```

- Install dependencies:

```bash
uv sync
```

- Environment variables (to use Gemini models):

Create a .env file in week_2 with:

```
GEMINI_API_KEY=your_key_here
```

### Usage

Supported models:

- Ollama: llama3.1, phi3, deepseek-r1:1.5b
- Gemini: gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3-flash-preview

#### Prompt Mode

Send a one-off prompt to a chosen model:

```bash
uv run prompt_mode.py llama3.1 "tell me one malaysian joke"
```

Gemini example (requires GEMINI_API_KEY in .env):

```bash
uv run prompt_mode.py gemini-2.5-flash "summarize this job in 1 sentence"
```

#### Tag Data

Tag job listings with tech stacks using the default model:

```bash
uv run tag_data.py
```

Use a specific model:

```bash
uv run tag_data.py gemini-2.5-flash-lite
```

#### Find Skill Gaps

Compute gaps using the default resume and DB:

```bash
uv run find_skil_gaps.py
```

Use a specific model:

```bash
uv run find_skil_gaps.py gemini-2.5-flash
```

Run multiple trials and compare outputs (auto-edits resume text slightly):

```bash
bash run_tag_tests.sh
```

Example output:

```
gaps=['aws', 'docker', 'sql', 'tensorflow', ...] time=4.12 tokens=102
```

---

### API / Function Reference

Module interactions:
- prompt_mode.py is the shared LLM client used by tag_data.py and find_skil_gaps.py.
- tag_data.py reads raw job descriptions from the sqlite DB and writes tech_stack back into the same DB.
- find_skil_gaps.py reads the tagged tech_stack from the DB, compares against the resume text/PDF, and outputs gaps.

- tag_data(db_url: str)
	- Purpose: Read jobs from the sqlite DB and populate tech_stack for rows with missing values.
	- Inputs: db_url is a path to the sqlite database file.
	- Outputs: Updates the database in batches and logs each analyzed job to stdout.

- find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult
	- Purpose: Compute skill gaps between a resume and the tagged job database.
	- Inputs: input_file_path (resume text), db_url (sqlite database path).
	- Outputs: SkillGapResult with gaps list and metadata (timing, token estimate).

- prompt_model(model: str, prompt: str) -> str
	- Purpose: Send a prompt to either Ollama or Gemini and return the text response or an error string.
	- Inputs: model name and prompt text.
	- Outputs: Response string or error string prefixed with [Ollama Error] / [Gemini Error].

---

### Data / Assumptions

- Database schema: jobs table with columns source_id, job_title, company, description, tech_stack.
- Input files:
	- data/resume_d3.txt is the resume text input.
	- data/jobs_d1.db is the tagged sqlite DB.
- Assumptions:
	- tech_stack values are comma-separated skills.
	- Non-technical skills are filtered with a small blacklist.
	- Skill matching is based on exact tokens or LLM-selected gaps from the provided list.
- Data flow:
	- tag_data.py writes tech_stack -> find_skil_gaps.py reads tech_stack -> compares to resume.

---

### Testing

- Manual testing with multiple LLM models (Ollama and Gemini).
- Scripted consistency checks via run_tag_tests.sh:
	- Runs find_skil_gaps.py multiple times while making minor non-technical edits to the resume.
	- Compares outputs and reports SAME/DIFFERENT.
- Validation focuses on deterministic outputs and correct parsing of the LLM JSON format.

---

### Limitations

- LLM responses may still vary across providers, even with low-temperature settings.
- Skill extraction depends on tech_stack quality; noisy tags can affect gap results.
- Token limits or long resumes can reduce accuracy or increase retries.
- No advanced alias mapping (e.g., cpp vs c++) beyond exact matches in the skills list.

---

### Architecture Reflection

- Design Choices
	- Separate modules for prompting, tagging, and gap analysis to keep concerns isolated.
	- Use batch processing to reduce token usage and control retries.

- Trade-offs
	- Prioritized reliability and debuggability over maximum accuracy.
	- Kept deterministic fallbacks to avoid full dependence on LLM variability.

- Improvements
	- Add structured logging and metrics for retry rates and token usage (basically stuff in the bonus).
	- Introduce better schema validation and automated tests.
