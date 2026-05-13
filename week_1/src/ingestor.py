from email import message_from_bytes
import quopri


def ingest_all_mhtml(input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    mhtml_files = sorted([f for f in input_dir.iterdir() if f.suffix == ".mhtml"])
    total = len(mhtml_files)
    extracted = 0
    failed = 0

    for file in mhtml_files:
        try:
            with open(file, "rb") as f:
                msg = message_from_bytes(f.read())

            html_content = None
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if part.get("content-transfer-encoding") == "quoted-printable":
                        payload = quopri.decodestring(payload)
                    html_content = payload.decode("utf-8", errors="replace")
                    break

            if html_content:
                output_file = output_dir / (file.stem + ".html")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                extracted += 1
                print(f"✅ Extracted: {file.name}")
            else:
                failed += 1
                print(f"⚠️ No HTML content found in: {file.name}")

        except Exception:
            failed += 1
            print(f"⚠️ No HTML content found in: {file.name}")

    print("\n📊 Bronze Summary:")
    print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")
