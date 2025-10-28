# main.py (Corrected with absolute paths)
import sys
import glob
import logging
from pathlib import Path

# --- 1. SET UP BULLETPROOF PATHS ---
# Get the absolute path of this script file (e.g., .../RESUME-AI-PROJECT/main.py)
SCRIPT_PATH = Path(__file__).resolve()
# Get the root directory of the project (e.g., .../RESUME-AI-PROJECT/)
PROJECT_ROOT = SCRIPT_PATH.parent

# Import the classes from your other files
try:
    from extractor.extractor import ResumeExtractor
    from extractor.parser import SemanticParser 
except ImportError as e:
    print(f"FATAL: Failed to import necessary modules: {e}")
    print(f"Project root is: {PROJECT_ROOT}")
    print("Please ensure your folder structure is correct.")
    sys.exit(1)

# ---------------- Logger ----------------
logger = logging.getLogger("main_pipeline")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
logger.addHandler(handler)

def run_pipeline(input_patterns: list, extractor_output_dir: str, parser_output_dir: str):
    """
    Runs the full extraction and parsing pipeline.
    """
    
    # 1. Find all input files
    input_files = []
    for pattern in input_patterns:
        # We use str(pattern) because glob works best with strings
        files_found = glob.glob(str(pattern))
        if not files_found:
            logger.warning(f"No files found for pattern: {pattern}. Skipping.")
        else:
            input_files.extend(files_found)
    
    if not input_files:
        logger.error("No valid input files found to process.")
        sys.exit(1)
        
    logger.info(f"Found {len(input_files)} files to process.")

    # 2. Initialize the Extractor and Parser
    try:
        extractor = ResumeExtractor(output_dir=extractor_output_dir)
        parser = SemanticParser(output_dir=parser_output_dir)
    except Exception as e:
        logger.critical(f"Failed to initialize extractor or parser: {e}")
        sys.exit(1)

    # 3. Run the two-step process for each file
    for file_path in input_files:
        logger.info(f"--- Processing: {file_path} ---")
        
        try:
            # --- Step 1: Run Extractor ---
            logger.info("Step 1: Extracting raw data...")
            saved_jsonl_path = extractor.process_and_save(file_path)
            logger.info(f" -> Raw extraction saved to: {saved_jsonl_path}")

            # --- Step 2: Run Parser ---
            logger.info("Step 2: Parsing semantic blocks...")
            parser.parse_file(saved_jsonl_path)
            logger.info(" -> Parsing complete.")

        except Exception as e:
            logger.error(f"   -> FAILED to process {file_path}: {e}")
            logger.exception(f"Full error for {file_path}:")


# -------------- CLI Usage --------------
if __name__ == "__main__":
    
    # --- 2. CONFIGURATION (Now uses bulletproof paths) ---
    DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "uploads" / "*"
    DEFAULT_EXTRACTOR_OUTPUT_DIR = PROJECT_ROOT / "data" / "downloads"
    DEFAULT_PARSER_OUTPUT_DIR = PROJECT_ROOT / "data" / "parsed_json"
    
    if len(sys.argv) > 1:
        # If user provides a path, use it
        patterns = sys.argv[1:]
    else:
        # Otherwise, use the default
        patterns = [DEFAULT_INPUT_DIR]
        logger.info(f"No input pattern provided. Using default: {DEFAULT_INPUT_DIR}")

    run_pipeline(
        input_patterns=patterns,
        extractor_output_dir=str(DEFAULT_EXTRACTOR_OUTPUT_DIR),
        parser_output_dir=str(DEFAULT_PARSER_OUTPUT_DIR)
    )
    
    logger.info("--- Pipeline finished ---")