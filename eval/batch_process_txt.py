# eval/batch_process_txt.py

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

# Import from 'extractor' folder
from extractor.extractor import ResumeExtractor
from extractor.parser import ResumeParser  # We use this just for its ._clean_text() method

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_all_pdfs_to_txt(input_dir: str, output_dir: str):
    """
    Extracts and cleans all PDFs in an input directory and saves
    them as individual .txt files in an output directory.
    """
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Create the output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all PDF files in the input directory
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDFs to process.")

    # Instantiate your tools once
    extractor = ResumeExtractor()
    parser = ResumeParser()

    # Use tqdm for a progress bar
    for pdf_file in tqdm(pdf_files, desc="Processing Resumes to TXT"):
        try:
            # 1. Extract raw text
            extraction_result = extractor.extract(str(pdf_file))
            
            if not extraction_result.text or extraction_result.text.isspace():
                logger.warning(f"No text extracted from {pdf_file.name}")
                continue

            # 2. Clean the raw text using the parser's internal method
            # This fixes typos, broken links, and spacing issues
            cleaned_text = parser._clean_text(extraction_result.text)
            
            # 3. Define the output .txt file path
            # (e.g., "data/processed_texts/resume1.txt")
            output_txt_path = output_path / (pdf_file.stem + ".txt")
            
            # 4. Write the cleaned text to the new file
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
                
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {e}")

    logger.info(f"✅ Batch processing complete. Output .txt files saved to {output_path}")

if __name__ == "__main__":
    # This allows you to run the script from the command line
    parser = argparse.ArgumentParser(description="Batch process resumes from PDF to .txt files.")
    
    parser.add_argument(
        "--input-dir", 
        type=str, 
        default="data/uploads",  # Default input
        help="Directory containing the PDF resume files."
    )
    
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="data/processed_texts", # New output directory
        help="Directory to save the output .txt files."
    )
    
    args = parser.parse_args()
    
    process_all_pdfs_to_txt(args.input_dir, args.output_dir)
    
    