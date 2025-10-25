# eval/checker.py

import sys
import os
import json  # <-- Import the JSON module

# --- Add this code to fix ModuleNotFoundError ---
# Add the project root (one level up from 'eval') to the system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# -----------------------------------------------

from extractor.extractor import ResumeExtractor
from extractor.parser import ResumeParser  # Your new file

# Define the input and output filenames
INPUT_FILE = "data/uploads/resume1.pdf"
OUTPUT_FILE = ""

print(f"Starting extraction from {INPUT_FILE}...")

# 1. Extract
extractor = ResumeExtractor()
extraction_result = extractor.extract(INPUT_FILE)
raw_text = extraction_result.text

print("Extraction complete. Starting parsing...")

# 2. Parse
parser = ResumeParser()
structured_data = parser.parse(raw_text)

print("Parsing complete.")

# 3. Save to JSON file
try:
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Use json.dump() to write the dictionary to the file
        # indent=4 makes the JSON file human-readable
        json.dump(structured_data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Successfully saved structured data to {OUTPUT_FILE}")

except Exception as e:
    print(f"❌ Error saving to JSON file: {e}")

# Optional: You can still print it to the console if you want
# print("\n--- Parsed Data ---")
# print(structured_data)