from pathlib import Path
from src.ingestor import ingest_all_mhtml
from src.processor import process_all_html
from src.loader import load_all_jsons
# from src.run_data_profile import run_data_profile

import sys


# we're using pathlib library here primarily due to:
# #1. compatibility issues, like backspace/frontspace between dif os
# #2. os.path requires string manip, passing the path string into other functions,
# while Pathlib library gives you a Path object, that you can use methods.
SOURCE_DIR = Path("data/0_source")
BRONZE_DIR = Path("data/1_bronze")
SILVER_DIR = Path("data/2_silver")
GOLD_DIR = Path("data/3_gold")
DB_NAME = "jobs.db"

# def run_profiler():
#     db_path = GOLD_DIR/DB_NAME
#     run_data_profile(db_path)

def run_gold():
    input_dir = SILVER_DIR
    output_dir = GOLD_DIR
    load_all_jsons(input_dir, output_dir)

def run_silver():
    input_dir = BRONZE_DIR
    output_dir = SILVER_DIR
    process_all_html(input_dir, output_dir)


def run_bronze():
    input_dir = SOURCE_DIR
    output_dir = BRONZE_DIR
    ingest_all_mhtml(input_dir, output_dir)


def main():
    if len(sys.argv) == 1:
        print("No command provided.")
        return

    for arg in sys.argv[1:]:
        match arg:
            case "ingest":
                print("🥉 Bronze: ingesting MHTML to HTML")
                run_bronze()
            case "process":
                print("🥈 Silver: processing HTML to JSON")
                run_silver()
            case "load":
                print("🥇 Gold: loading JSON to SQLite")
                run_gold()
            case _:
                print(f"Unknown command: {arg}")

    return


if __name__ == "__main__":
    main()
