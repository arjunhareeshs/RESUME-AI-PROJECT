# eval/batch_process.py

import json
import argparse
from pathlib import Path
from tqdm import tqdm
import logging
import sys
import os

# --- Add this code to fix ModuleNotFoundError ---
# Add the project root (one level up from 'eval') to the system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# -----------------------------------------------

# Import from 'extractor' folder (based on your screenshot)
from extractor.extractor import ResumeExtractor
from extractor.parser import ResumeParser  # Corrected import path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_all_pdfs(input_dir: str, output_file: str):
    """
    Extracts and parses all PDFs in an input directory and saves 
    them to a single .jsonl file.
    """
    
    input_path = Path(input_dir)
    output_path = Path(output_file)

    # Find all PDF files in the input directory
    # Use .glob('*.pdf') to find files in the directory
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDFs to process.")

    # Instantiate your tools once
    extractor = ResumeExtractor()
    parser = ResumeParser()

    # Open the output file in 'w' (write) mode to create a new file each time.
    # Use 'a' (append) mode if you want to add to an existing file.
    with open(output_path, 'w', encoding='utf-8') as f:
        
        # Use tqdm for a progress bar
        for pdf_file in tqdm(pdf_files, desc="Processing Resumes"):
            try:
                # 1. Extract raw text
                extraction_result = extractor.extract(str(pdf_file))
                
                if not extraction_result.text or extraction_result.text.isspace():
                    logger.warning(f"No text extracted from {pdf_file.name}")
                    continue

                # 2. Parse into structured JSON
                structured_data = parser.parse(extraction_result.text)
                
                # 3. Create the final record for the JSONL file
                record = {
                    "source_file": pdf_file.name,
                    "parsed_data": structured_data
                }
                
                # 4. Convert dictionary to a JSON string
                json_line = json.dumps(record, ensure_ascii=False)
                
                # 5. Write the JSON string as a new line
                f.write(json_line + '\n')
                
            except Exception as e:
                logger.error(f"Failed to process {pdf_file.name}: {e}")

    logger.info(f"✅ Batch processing complete. Output saved to {output_path}")

if __name__ == "__main__":
    # This allows you to run the script from the command line
    parser = argparse.ArgumentParser(description="Batch process resumes from PDF to JSONL.")
    
    parser.add_argument(
        "--input-dir", 
        type=str, 
        default="data/uploads",  # Set default based on your structure
        help="Directory containing the PDF resume files."
    )
    
    parser.add_argument(
        "--output-file", 
        type=str, 
        default="data/resumes_output.jsonl", # Example output file
        help="Path to the output .jsonl file."
    )
    
    args = parser.parse_args()

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    process_all_pdfs(args.input_dir, args.output_file)