import sqlite3


def run_data_profile(db_path):
    if not db_path.exists() or not db_path.is_file():
        raise FileNotFoundError(f"Database not found at {db_path}")

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_records = cursor.fetchone()[0]

    cursor.execute(
        """
		SELECT
			SUM(CASE WHEN job_title IS NULL OR job_title = '' THEN 1 ELSE 0 END),
			SUM(CASE WHEN company IS NULL OR company = '' THEN 1 ELSE 0 END),
			SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END)
		FROM jobs
		"""
    )
    missing_job_title, missing_company, missing_description = cursor.fetchone()

    cursor.execute(
        "SELECT AVG(LENGTH(description)) FROM jobs WHERE description IS NOT NULL"
    )
    avg_description_length = cursor.fetchone()[0]

    cursor.execute(
        """
		SELECT source_id, job_title, LENGTH(description)
		FROM jobs
		WHERE description IS NOT NULL
		ORDER BY LENGTH(description) ASC
		LIMIT 1
		"""
    )
    shortest_row = cursor.fetchone()

    cursor.execute(
        """
		SELECT source_id, job_title, LENGTH(description)
		FROM jobs
		WHERE description IS NOT NULL
		ORDER BY LENGTH(description) DESC
		LIMIT 1
		"""
    )
    longest_row = cursor.fetchone()

    connection.close()

    avg_description_length = (
        int(avg_description_length) if avg_description_length else 0
    )
    shortest_length = shortest_row[2] if shortest_row else 0
    shortest_source_id = shortest_row[0] if shortest_row else ""
    shortest_job_title = shortest_row[1] if shortest_row else ""
    longest_length = longest_row[2] if longest_row else 0
    longest_source_id = longest_row[0] if longest_row else ""
    longest_job_title = longest_row[1] if longest_row else ""

    print("--- 🔍 DATA QUALITY REPORT ---")
    print(f"📈 Total Records: {total_records}")
    print(
        "❓ Missing Values -> "
        f"job_title: {missing_job_title}, "
        f"company: {missing_company}, "
        f"description: {missing_description}"
    )
    print(f"📝 Avg Description Length: {avg_description_length} chars")
    print(f"⚠️ Shortest Description: {shortest_length} chars")
    print(f"   ↳ source_id: {shortest_source_id} | job_title: {shortest_job_title}")
    print(f"🚨 Longest Description: {longest_length} chars")
    print(f"   ↳ source_id: {longest_source_id} | job_title: {longest_job_title}")
