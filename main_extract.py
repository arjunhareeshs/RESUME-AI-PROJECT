# main.py (Updated for 2-step pipeline with Enhanced Parser)
import sys
import glob
import logging
from pathlib import Path

# Import the classes from your other files
try:
    from extractor.extractor import ResumeExtractor
    # Import the enhanced parser
    from extractor.parser import SemanticParser
except ImportError as e:
    print(f"FATAL: Failed to import necessary modules: {e}")
    print("Please ensure extractor/extractor.py and extractor/parser.py exist.")
    sys.exit(1)

# ---------------- Logger ----------------
logger = logging.getLogger("main_pipeline")
logger.setLevel(logging.INFO)
# Prevent duplicate handlers
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)


def run_pipeline(input_patterns: list, extractor_output_dir: str, final_parser_output_dir: str):
    """
    Runs the full 2-step extraction and detailed parsing pipeline.
    """

    # 1. Find all input files
    input_files = []
    for pattern in input_patterns:
        files_found = glob.glob(str(pattern))
        if not files_found:
            logger.warning(f"No files found for pattern: {pattern}. Skipping.")
        else:
            input_files.extend(files_found)

    if not input_files:
        logger.error("No valid input files found to process.")
        sys.exit(1)

    logger.info(f"Found {len(input_files)} files to process.")

    # 2. Initialize Extractor and the Enhanced Parser
    try:
        extractor = ResumeExtractor(output_dir=extractor_output_dir)
        # The enhanced parser now saves to the final directory
        parser = SemanticParser(output_dir=final_parser_output_dir)
    except Exception as e:
        logger.critical(f"Failed to initialize extractor or parser: {e}")
        sys.exit(1)

    # 3. Run the two-step process for each file
    for file_path in input_files:
        logger.info(f"--- Processing: {file_path} ---")

        saved_jsonl_path = None
        final_json_path = None

        try:
            # --- Step 1: Run Extractor ---
            logger.info("Step 1: Extracting raw data...")
            saved_jsonl_path = extractor.process_and_save(file_path)
            if not saved_jsonl_path: raise Exception("Extractor failed to save JSONL.")
            logger.info(f" -> Raw extraction saved to: {saved_jsonl_path}")

            # --- Step 2: Run Enhanced Parser ---
            logger.info("Step 2: Parsing details and saving final JSON...")
            final_json_path = parser.parse_file(saved_jsonl_path)
            if not final_json_path: raise Exception("Parser failed to save final JSON.")
            logger.info(f" -> Final structured JSON saved to: {final_json_path}")
            logger.info(" -> Processing complete.")

        except Exception as e:
            logger.error(f"   -> FAILED to process {file_path}: {e}")
            logger.exception(f"Full error for {file_path}:")


# -------------- CLI Usage --------------
if __name__ == "__main__":

    # --- Configuration ---
    SCRIPT_PATH = Path(__file__).resolve()
    PROJECT_ROOT = SCRIPT_PATH.parent

    DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "uploads" / "*"
    DEFAULT_EXTRACTOR_OUTPUT_DIR = PROJECT_ROOT / "data" / "downloads" # Intermediate JSONL
    DEFAULT_FINAL_OUTPUT_DIR = PROJECT_ROOT / "data" / "final_output" # Final JSON

    if len(sys.argv) > 1:
        patterns = sys.argv[1:]
    else:
        patterns = [DEFAULT_INPUT_DIR]
        logger.info(f"No input pattern provided. Using default: {DEFAULT_INPUT_DIR}")

    run_pipeline(
        input_patterns=patterns,
        extractor_output_dir=str(DEFAULT_EXTRACTOR_OUTPUT_DIR),
        final_parser_output_dir=str(DEFAULT_FINAL_OUTPUT_DIR)
    )

    logger.info("--- Pipeline finished ---")