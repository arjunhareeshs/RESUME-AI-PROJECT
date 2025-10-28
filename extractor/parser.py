# parser.py (Simplified - Text Only + Project Sub-Structure + No Project Prefix)
import json
import glob
import sys
import logging
import re
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional
from fuzzywuzzy import fuzz

# ---------------- Logger ----------------
logger = logging.getLogger("semantic_parser")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
logger.addHandler(handler)

class SemanticParser:
    """
    Reads the JSONL output from the extractor and parses it into
    semantically-chunked blocks, including sub-structure for projects.
    Outputs project descriptions as a list of strings.
    Uses cleaned project titles as keys directly.
    """

    SECTION_KEYWORDS = {
        "PROFILE": ["PROFILE", "ABOUT ME", "SUMMARY", "PROFESSIONAL SUMMARY"],
        "CONTACT": ["CONTACT", "CONTACT ME", "CONTACT INFO"],
        "TECH_SKILLS": ["TECH SKILLS", "TECHNICAL SKILLS", "SKILLS", "SKILL AND EXPERTISE"],
        "SOFT_SKILLS": ["SOFT SKILLS", "PROFESSIONAL SKILLS"],
        "LANGUAGES": ["LANGUAGES"],
        "PROJECTS": ["PROJECTS", "PERSONAL PROJECTS"],
        "CERTIFICATIONS": ["CERTIFICATIONS", "AWARDS", "ACCOLADES"],
        "EDUCATION": ["EDUCATION", "ACADEMIC BACKGROUND"],
        "CAREER_OBJECTIVE": ["CAREER OBJECTIVE", "OBJECTIVE"],
    }

    DESCRIPTION_START_WORDS = {"it", "built", "developed", "created", "implemented", "used", "leveraged", "trained", "evaluated", "webframeworks"}
    BULLET_POINTS = {"•", "-", "*", "➢"}

    def __init__(self, output_dir: str = "data/parsed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Parser output directory set to: {self.output_dir.resolve()}")

    def _find_header_match(self, line_text: str) -> Optional[str]:
        cleaned_line = line_text.strip().upper()
        if not cleaned_line:
            return None
        for key, keywords in self.SECTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in cleaned_line and len(cleaned_line) <= len(keyword) + 5:
                     return key
                if fuzz.token_set_ratio(cleaned_line, keyword) > 85:
                    return key
        return None

    def _is_project_title(self, line_text: str) -> bool:
        line_text = line_text.strip()
        if not line_text: return False
        if len(line_text.split()) > 7 or len(line_text) > 60: return False
        if line_text and line_text[0] in self.BULLET_POINTS: return False
        first_word = line_text.split()[0].lower().strip(':') if line_text.split() else ""
        if first_word in self.DESCRIPTION_START_WORDS: return False
        return True

    def _clean_key(self, text: str) -> str:
        key = re.sub(r'[^\w\s-]', '', text).strip()
        key = re.sub(r'[-\s]+', '_', key)
        return key.upper()

    def parse_file(self, jsonl_path: str):
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                data = json.loads(f.read())
        except Exception as e:
            logger.error(f"Could not read or parse JSONL file {jsonl_path}: {e}")
            return

        column_texts: List[str] = data.get('column_texts', [])

        structured_output = defaultdict(lambda: None) # Use None as default

        for i, column_text_block in enumerate(column_texts):
            lines = column_text_block.split('\n')

            current_header_key = f"UNKNOWN_COL_{i}"
            current_project_key = None

            for line_text in lines:
                line_text = line_text.strip()
                if not line_text: continue

                header_key = self._find_header_match(line_text)

                if header_key:
                    current_header_key = header_key
                    current_project_key = None
                    if structured_output[current_header_key] is None:
                        # For PROJECTS section, initialize differently if needed later
                        if header_key == "PROJECTS":
                             # We might not need a list if all projects become dicts
                             structured_output[header_key] = {} # Initialize as dict
                        else:
                             structured_output[current_header_key] = []


                elif current_header_key == "PROJECTS":
                    if self._is_project_title(line_text):
                        project_key_base = self._clean_key(line_text)
                        if not project_key_base:
                             project_key_base = f"UNTITLED_PROJECT_{len(structured_output)}"
                        # --- THIS IS THE CHANGE ---
                        # Remove the "PROJECT_" prefix
                        current_project_key = project_key_base
                        # --- End of Change ---

                        # Ensure the main PROJECTS entry exists as a dict
                        if not isinstance(structured_output["PROJECTS"], dict):
                             structured_output["PROJECTS"] = {}

                        structured_output["PROJECTS"][current_project_key] = {
                            "title": line_text,
                            "description": []
                        }
                    elif current_project_key and isinstance(structured_output.get("PROJECTS"), dict) and isinstance(structured_output["PROJECTS"].get(current_project_key), dict):
                        # Append to description only if the structure is correct
                        structured_output["PROJECTS"][current_project_key]["description"].append(line_text)
                    else:
                         # Lines before the first project title in the PROJECTS section
                         if structured_output.get("PROJECTS_HEADER_INFO") is None:
                              structured_output["PROJECTS_HEADER_INFO"] = []
                         structured_output["PROJECTS_HEADER_INFO"].append(line_text)

                else: # For sections other than PROJECTS
                    if structured_output[current_header_key] is None:
                        structured_output[current_header_key] = []
                    # Ensure it's a list before appending
                    if isinstance(structured_output[current_header_key], list):
                         structured_output[current_header_key].append(line_text)
                    # If it somehow became a dict (shouldn't happen now), log error or handle
                    else:
                         logger.warning(f"Unexpected data type for section '{current_header_key}'. Expected list, got {type(structured_output[current_header_key])}. Line ignored: {line_text}")


        # Post-process: Join lists into strings, keep project dicts/lists as they are
        final_json = {
            "source": data.get("source"),
            "metadata": data.get("metadata")
        }
        for key, value in structured_output.items():
            if value is None: continue

            if isinstance(value, list):
                # Join lines for non-project sections (like PROFILE, CONTACT, etc.)
                # Also join PROJECTS_HEADER_INFO if it exists
                final_json[key] = "\n".join(value)
            elif isinstance(value, dict) and key == "PROJECTS":
                 # Keep the PROJECTS dictionary as is (descriptions are already lists)
                 final_json[key] = value
            elif isinstance(value, dict): # Should only be project dicts now if logic changed
                 # If somehow a project dict ended up at the top level, keep its structure
                 final_json[key] = value
            else:
                 final_json[key] = str(value)

        output_path = self.output_dir / f"{Path(jsonl_path).stem}_parsed.json"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Saved parsed file: {output_path}")
        except Exception as e:
            logger.error(f"Could not save parsed JSON {output_path}: {e}")

# -------------- CLI Usage --------------
if __name__ == "__main__":
    INPUT_DIR = "data/downloads"
    OUTPUT_DIR = "data/parsed_json"

    jsonl_files = glob.glob(f"{INPUT_DIR}/*.jsonl")

    if not jsonl_files:
        print(f"No .jsonl files found in {INPUT_DIR}.")
        print(f"Please run extractor.py first to generate them.")
        sys.exit(1)

    parser = SemanticParser(output_dir=OUTPUT_DIR)

    for file_path in jsonl_files:
        print(f"Parsing: {file_path}...")
        try:
            parser.parse_file(file_path)
        except Exception as e:
            print(f"   -> FAILED: {e}")