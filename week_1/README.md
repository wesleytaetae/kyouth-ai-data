## Project Description

This project builds a simple medallion-style ETL pipeline for job listings. It ingests MHTML files, extracts HTML with quopri, extracts and structures data into JSON with beautifulsoup with pydantic type validation, loads it into SQLite, and runs data quality profiling.

## Setup Instructions

### Prerequisites

- Python 3.14 (matches `pyproject.toml`)
- `uv` (Python package manager)
- Git (for cloning, optional if you already have the folder)
- bs4 (beautifulsoup, for processing data from html to json)
- ruff (linter)
- pydantic (enforce contracts, data valiadtion)

### Step-by-Step Local Setup

1. Clone the repo (or open the existing folder).
2. Create and activate a virtual environment (recommended).
3. Install dependencies with `uv`.
4. Run the pipeline commands.

### Install `uv`

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

Restart your shell so `uv` is on your PATH.

### Create Virtual Environment

```bash
cd week_1
uv venv
source .venv/bin/activate
```

### Install Dependencies

```bash
uv sync
```

## Usage

- uv run main.py ingest : converts `data/0_source/*.mhtml` to `data/1_bronze/*.html`
```bash
EXPECTED RESULTS:
📊 Bronze Summary:
Total: 100 | Extracted: 100 | Failed: 0
```

- uv run main.py process : parses `data/1_bronze/*.html` into `data/2_silver/*.json`
```bash
EXPECTED RESULTS:
📊 Silver Summary:
Total: 100 | Processed: 84 | Skipped: 16
```

- uv run main.py load : loads `data/2_silver/*.json` into `data/3_gold/jobs.db`
```bash
EXPECTED RESULTS:
📊 Gold Summary:
Total: 84 | Inserted: 84 | Skipped: 0
```

- uv run main.py profile : prints data quality metrics from `jobs.db`
```bash
EXPECTED RESULTS:
--- 🔍 DATA QUALITY REPORT ---
📈 Total Records: 84
❓ Missing Values -> job_title: 0, company: 0, description: 0
📝 Avg Description Length: 2654 chars
⚠️  Shortest Description: 32 chars
   ↳ source_id: 91647393 | job_title: Software Engineer
🚨 Longest Description: 6781 chars
   ↳ source_id: 91731564 | job_title: Automation Engineer
```

- uv run main.py all : runs full pipeline in order

## Technical Reflections

### Module 1: The Extractor (Medallion & Lakehouses)
Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?
- **Answer**: 1) Idempotency. Having the raw HTML files makes it so that if there is a critical bug that transforms and corrupts your database, you can just rerun the program and get everything back. 2) Flexibility. In the case where you decide to add one more data point to include in your database (e.g. salary range, location etc.), you do not have to rescrape the entire website, you can just update loader.py to include more tags.

### Module 2: Treatment Plant (ETL vs ELT & Scale)
Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?
- **Answer**: Cloud systems prefer loading raw data to allow for flexible re-processing of data and the same points discussed in Module 1. Today's cloud services provides cheap "cold storage" like AWS S3, hence there is next to no cost concerns. You will only pay more for compute power to transform the data on demand. There are a few issues that might happen when processing files sequentially, but the most prominent is Head-of-line blocking. Assuming you are processing through 1,000,000 data points, and file 100 is corrupted. It halts your entire processing pipeline. Distributed processing utilizes parallelism, where you have more worker processes that is in charge of a small percentage of the total data points (chunks). If one of the worker process gets caught up by a corrupted file, the rest of the workers can still continue with the processing.

### Module 3: The Blueprint & The Vault (Storage & Contracts)
What should happen if an important field like job_title disappears? Why fail early instead of silently inserting nulls into DB? How does INSERT OR IGNORE help prevent duplicate records?
- **Answer**: If an important field disappears, it should fail early instead of silently inserting nulls into DB due to data poisoning. Assuming a scenario where you keep track of the salary of the job in the database, if there are entries where salary = null, it might show up as 0 in your analytics processor, and drag the average salary down. INSERT OR IGNORE help prevent duplicate records by checking PRIMARY key values (source_id in this case), and returning an exception if there is already a duplicate.

### Module 4: The QA Inspector & Orchestrator (Orchestration & DAGs)
What happens if processor.py crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?
- **Answer**: If processor.py crashes halfway, depending on the reason it will throw/raise an error/exception. Automated orchestration tools are more reliable as in they help with state-persistence and observability. For example, if your python script is hosted in a docker container/server that reboots or kills the process during a retry, the state of the script on reboot is not tracked (the user won't know how many retries it made, where in the script did it crash previously etc). Orchestration tools like airflow back up the state with the database, and allows any restarts to immediately resume from the point of failure.