# extractor/parser.py (Corrected and Simplified)

import json
import glob
import sys
import logging
import re
from pathlib import Path
from typing import Optional

# ---------------- Logger ----------------
logger = logging.getLogger("semantic_parser")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [Parser]: %(message)s"))
    logger.addHandler(handler)

# ---------------- Parser Logic ----------------

class Parser:
    def __init__(self, output_dir: str = "data/final_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Simplified Parser initialized. Will only copy raw text.")

    def parse_jsonl_file(self, jsonl_path: str) -> Optional[str]:
        """
        Reads one JSONL file from the extractor and saves it as the
        final structured JSON, without any extra parsing.
        """
        
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                data = json.loads(f.read())
        except Exception as e:
            logger.error(f"Could not load JSONL file {jsonl_path}: {e}")
            return None

        # --- This simplified logic copies all keys from the extractor ---
        final_json = {
            "source": data.get("source"),
            "pages": data.get("pages"),
            "metadata": data.get("metadata"),
            "column_texts": data.get("column_texts"),
            "style_analysis": data.get("style_analysis"),
            "links": data.get("links")  # <-- ADDED THIS LINE
        }
        # --- End of new logic ---

        # --- Save Final JSON ---
        output_path = self.output_dir / f"{Path(jsonl_path).stem}_final.json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # We save with indent=4 to make it readable
                json.dump(final_json, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Saved final raw JSON file: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Could not save final parsed JSON {output_path}: {e}")
            return None

# -------------- CLI Usage --------------
if __name__ == "__main__":
    INPUT_DIR = "data/downloads"
    OUTPUT_DIR = "data/final_output"

    jsonl_files = glob.glob(f"{INPUT_DIR}/*.jsonl")

    if not jsonl_files:
        print(f"No .jsonl files found in {INPUT_DIR}.")
        print(f"Please run extractor.py first.")
        sys.exit(1)

    parser = Parser(output_dir=OUTPUT_DIR)
    for file in jsonl_files:
        parser.parse_jsonl_file(file)