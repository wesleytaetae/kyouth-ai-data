import json
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError


class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str


def process_all_html(input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    html_files = sorted([f for f in input_dir.iterdir() if f.suffix == ".html"])
    if not html_files:
        raise FileNotFoundError(f"No .html files found in: {input_dir}")

    total = len(html_files)
    processed = 0
    skipped = 0

    for file in html_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            og_url_tag = soup.find("meta", attrs={"property": "og:url"})
            og_url = og_url_tag.get("content", "").strip() if og_url_tag else ""
            source_id = og_url.rstrip("/").split("/")[-1] if og_url else ""

            job_title = ""
            company = ""
            description = ""

            title_tag = soup.find(attrs={"data-automation": "job-detail-title"})
            if title_tag:
                job_title = title_tag.get_text(separator=" ", strip=True)

            company_tag = soup.find(attrs={"data-automation": "advertiser-name"})
            if company_tag:
                company = company_tag.get_text(separator=" ", strip=True)

            desc_tag = soup.find(attrs={"data-automation": "jobAdDetails"})
            if desc_tag:
                description = desc_tag.get_text(separator=" ", strip=True)

            source_id = " ".join(source_id.split())
            job_title = " ".join(job_title.split())
            company = " ".join(company.split())
            description = " ".join(description.split())

            if not source_id:
                skipped += 1
                print(f"⚠️ Missing source_id in: {file.name}")
                continue
            if not job_title:
                skipped += 1
                print(f"⚠️ Missing job_title in: {file.name}")
                continue
            if not company:
                skipped += 1
                print(f"⚠️ Missing company in: {file.name}")
                continue
            if not description:
                skipped += 1
                print(f"⚠️ Missing description in: {file.name}")
                continue

            listing = JobListing(
                source_id=source_id,
                job_title=job_title,
                company=company,
                description=description,
            )

            output_file = output_dir / (file.stem + ".json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(listing.model_dump(), f, ensure_ascii=False, indent=2)

            processed += 1
            print(f"✅ Processed: {file.name}")

        except ValidationError:
            skipped += 1
            print(f"⚠️ Validation failed in: {file.name}")
        except Exception:
            skipped += 1
            print(f"⚠️ Skipped: {file.name}")

    print("\n📊 Silver Summary:")
    print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")
