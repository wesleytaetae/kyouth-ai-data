import json
import sqlite3


def load_all_jsons(input_dir, output_dir):
	output_dir.mkdir(parents=True, exist_ok=True)

	db_path = output_dir / "jobs.db"
	connection = sqlite3.connect(db_path)
	cursor = connection.cursor()

	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS jobs (
			source_id TEXT PRIMARY KEY,
			job_title TEXT,
			company TEXT,
			description TEXT,
			tech_stack TEXT
		)
		"""
	)
	connection.commit()

	json_files = sorted([f for f in input_dir.iterdir() if f.suffix == ".json"])
	total = len(json_files)
	inserted = 0
	skipped = 0

	for file in json_files:
		try:
			with open(file, "r", encoding="utf-8") as f:
				data = json.load(f)

			cursor.execute(
				"""
				INSERT OR IGNORE INTO jobs (source_id, job_title, company, description, tech_stack)
				VALUES (?, ?, ?, ?, ?)
				""",
				(
					data.get("source_id", ""),
					data.get("job_title", ""),
					data.get("company", ""),
					data.get("description", ""),
					data.get("tech_stack", ""),
				),
			)
			connection.commit()

			if cursor.rowcount == 1:
				inserted += 1
				print(f"✅ Inserted: {file.name}")
			else:
				skipped += 1
				print(f"⏭️ Skipped (duplicate): {file.name}")

		except Exception:
			skipped += 1
			print(f"⚠️ Failed: {file.name}")

	connection.close()

	print("\n📊 Gold Summary:")
	print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped}")
