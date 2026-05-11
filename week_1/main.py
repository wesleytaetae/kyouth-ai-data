from pathlib import Path # Figure out why use Path?
# from src.ingestor import ingest_all_mhtml
# from src.processor import process_all_html
# from src.loader import load_all_jsons
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

# def run_gold():
#     input_dir = SILVER_DIR
#     output_dir = GOLD_DIR
#     load_all_jsons(input_dir, output_dir)

# def run_silver():
# 		input_dir = BRONZE_DIR
# 		output_dir = SILVER_DIR
#     process_all_html(input_dir, output_dir)


# def run_bronze():
#     input_dir = SOURCE_DIR
# 		output_dir = BRONZE_DIR
#     ingest_all_mhtml(input_dir, output_dir)
    
def main():
    print("This is the name of the program:", sys.argv[0])
    print("Argument List:", str(sys.argv))
    

if __name__ == "__main__":
    main()
