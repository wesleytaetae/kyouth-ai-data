from pathlib import Path
from src.ingestor import ingest_all_mhtml
from src.processor import process_all_html
from src.loader import load_all_jsons
from src.profiler import run_data_profile

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

def run_profiler():
    db_path = GOLD_DIR / DB_NAME
    run_data_profile(db_path)

def run_gold():
    input_dir = SILVER_DIR
    output_dir = GOLD_DIR
    print("🥇 Gold: loading JSON to SQLite")
    load_all_jsons(input_dir, output_dir)

def run_silver():
    input_dir = BRONZE_DIR
    output_dir = SILVER_DIR
    print("🥈 Silver: processing HTML to JSON")
    process_all_html(input_dir, output_dir)


def run_bronze():
    input_dir = SOURCE_DIR
    output_dir = BRONZE_DIR
    print("🥉 Bronze: ingesting MHTML to HTML")
    ingest_all_mhtml(input_dir, output_dir)


def main():
    if len(sys.argv) == 1:
        print("Usage: python main.py [ingest/process/load/profile/all]")
        return

    for arg in sys.argv[1:]:
        match arg:
            case "ingest":
                run_bronze()
            case "process":
                run_silver()
            case "load":
                run_gold()
            case "profile":
                run_profiler()
            case "all":
                run_bronze()
                run_silver()
                run_gold()
                run_profiler()
            case _:
                print(f"Unknown command: {arg}, Usage: python main.py [ingest/process/load/profile/all]")

    return


if __name__ == "__main__":
    main()
