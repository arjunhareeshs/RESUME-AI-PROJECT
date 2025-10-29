# main.py (Updated to find all supported file types)

import sys
import os
import glob
from pathlib import Path
import logging

# --- Configuration & Logging Setup ---
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Define I/O directories
INPUT_DIR_NAME = "data/uploads"
DOWNLOADS_DIR_NAME = "data/downloads"       
FINAL_OUTPUT_DIR_NAME = "data/final_output" 

INPUT_DIR = PROJECT_ROOT / INPUT_DIR_NAME
DOWNLOADS_DIR = PROJECT_ROOT / DOWNLOADS_DIR_NAME
FINAL_OUTPUT_DIR = PROJECT_ROOT / FINAL_OUTPUT_DIR_NAME

# Set up logging for main script
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - [MAIN]: %(message)s")
logger = logging.getLogger("main_orchestrator")


# --- Imports ---
try:
    from extractor.extractor import Extractor 
    from extractor.parser import Parser
    logger.info("Successfully imported Extractor and Parser modules.")
except ImportError as e:
    logger.error(f"FATAL: Failed to import modules: {e}")
    logger.error("Ensure 'extractor' directory is set up with all necessary files and __init__.py.")
    sys.exit(1)


# --- Pipeline Functions ---

def setup_directories():
    """Ensures all necessary data directories exist."""
    logger.info("Setting up directories...")
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Input/Output directories ensured: {INPUT_DIR}, {DOWNLOADS_DIR}, {FINAL_OUTPUT_DIR}")


def run_extraction_stage(input_path: Path, output_path: Path):
    """Initializes and runs the Extractor on all supported files."""
    logger.info("\n--- STARTING EXTRACTION STAGE (PDF/DOCX/IMG -> JSONL) ---")
    
    # --- MODIFIED: Search for all supported extensions ---
    supported_extensions = [
        "*.pdf", "*.docx", "*.doc", 
        "*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff"
    ]
    input_files = []
    for ext in supported_extensions:
        # Use recursive=True if you want to search in subfolders
        input_files.extend(glob.glob(str(input_path / ext), recursive=False))
    # --- END OF MODIFICATION ---
    
    if not input_files:
        logger.warning(f"No supported files found in {input_path}.")
        return []

    extractor = Extractor(output_dir=str(output_path))
    processed_files = []
    
    for file in input_files:
        logger.info(f"Processing file: {Path(file).name}")
        try:
            output_jsonl_path = extractor.process_and_save(file)
            processed_files.append(output_jsonl_path)
        except Exception as e:
            logger.error(f"Critical error during extraction of {file}: {e}")
            
    logger.info("--- EXTRACTION STAGE COMPLETE ---")
    return processed_files


def run_parsing_stage(input_path: Path, output_path: Path):
    """Initializes and runs the Parser on all .jsonl files."""
    logger.info("\n--- STARTING PARSING STAGE (JSONL -> Final Structured JSON) ---")
    
    jsonl_files = glob.glob(str(input_path / "*.jsonl"))
    
    if not jsonl_files:
        logger.warning(f"No .jsonl files found in {input_path}. Parsing stage skipped.")
        return

    # Use the simple "pass-through" parser
    parser = Parser(output_dir=str(output_path))
    
    for file in jsonl_files:
        logger.info(f"Parsing file: {Path(file).name}")
        try:
            parser.parse_jsonl_file(file)
        except Exception as e:
            logger.error(f"Critical error during parsing of {file}: {e}")
            
    logger.info("--- PARSING STAGE COMPLETE ---")


def main():
    """Main execution entry point for the resume processing pipeline."""
    logger.info("--- Starting Resume Processing Pipeline ---")
    setup_directories()
    
    # 1. Extraction: (PDF/DOCX/IMG) -> JSONL
    run_extraction_stage(INPUT_DIR, DOWNLOADS_DIR)
    
    # 2. Parsing: JSONL -> Final Structured JSON
    run_parsing_stage(DOWNLOADS_DIR, FINAL_OUTPUT_DIR)
    
    logger.info("\n--- PIPELINE EXECUTION FINISHED Successfully ---")


if __name__ == "__main__":
    main()