# extractor/parser.py (Enhanced V2 - Improved Logic & Structure)
import json
import glob
import sys
import logging
import re
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
from fuzzywuzzy import fuzz
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc # For type hinting

# ---------------- Logger ----------------
logger = logging.getLogger("semantic_parser")
logger.setLevel(logging.INFO)
# Prevent duplicate handlers if script is re-run in same session
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [Parser]: %(message)s"))
    logger.addHandler(handler)

# ---------------- Keywords & Patterns (Expanded) ----------------
# Using tuples for keys to handle variations like C++/C#
SKILL_KEYWORDS = {
    # Programming Languages
    ("PYTHON",): ["python"], ("JAVA",): ["java"], ("C++", "CPP"): ["c++", "cpp"], ("C#", "CSHARP"): ["c#"],
    ("JAVASCRIPT", "JS"): ["javascript", "js"], ("TYPESCRIPT", "TS"): ["typescript", "ts"],
    ("HTML",): ["html"], ("CSS",): ["css"], ("SQL",): ["sql"], ("NOSQL",): ["nosql"], ("PHP",): ["php"],
    ("GO",): ["go", "golang"], ("RUST",): ["rust"], ("KOTLIN",): ["kotlin"], ("SWIFT",): ["swift"],
    ("C_LANG",): ["c programming", "c language", " c,"], # Note space before c,
    # Frameworks/Libraries (Web)
    ("REACT",): ["react", "react.js"], ("ANGULAR",): ["angular", "angular.js"], ("VUE",): ["vue", "vue.js"],
    ("NODEJS",): ["node.js", "nodejs"], ("DJANGO",): ["django"], ("FLASK",): ["flask"], ("FASTAPI",): ["fastapi"],
    ("SPRING",): ["spring", "spring boot"], ("DOTNET",): [".net", "dotnet"], ("RUBY_ON_RAILS",): ["ruby on rails"],
    # Databases
    ("MYSQL",): ["mysql"], ("POSTGRESQL",): ["postgresql", "postgres"], ("MONGODB",): ["mongodb"],
    ("REDIS",): ["redis"], ("SQLITE",): ["sqlite"], ("ORACLE",): ["oracle"], ("MS_SQL_SERVER",): ["ms sql server"],
    # DevOps/Cloud
    ("DOCKER",): ["docker"], ("KUBERNETES", "K8S"): ["kubernetes", "k8s"],
    ("AWS",): ["aws", "amazon web services"], ("AZURE",): ["azure", "microsoft azure"],
    ("GCP",): ["gcp", "google cloud platform"], ("TERRAFORM",): ["terraform"], ("ANSIBLE",): ["ansible"],
    # Tools/Platforms
    ("GIT",): ["git"], ("JENKINS",): ["jenkins"], ("JIRA",): ["jira"], ("GITHUB",): ["github"], ("GITLAB",): ["gitlab"],
    # Methodologies
    ("AGILE",): ["agile"], ("SCRUM",): ["scrum"],
    # ML/AI/Data Science
    ("MACHINE_LEARNING", "ML"): ["machine learning", "ml"], ("DEEP_LEARNING", "DL"): ["deep learning", "dl"],
    ("NLP",): ["nlp", "natural language processing"], ("COMPUTER_VISION", "CV"): ["computer vision", "cv"],
    ("GENERATIVE_AI",): ["generative ai"], ("DATA_SCIENCE",): ["data science"],
    ("TENSORFLOW", "TF"): ["tensorflow", "tf"], ("PYTORCH",): ["pytorch", "torch"], ("KERAS",): ["keras"],
    ("SCIKIT_LEARN",): ["scikit-learn", "sklearn"], ("PANDAS",): ["pandas"], ("NUMPY",): ["numpy"],
    ("OPENCV",): ["opencv"], ("SPACY",): ["spacy"], ("NLTK",): ["nltk"],
    ("TRANSFORMER",): ["transformer", "transformers"], ("CNN",): ["cnn", "convolutional neural network"],
    ("RNN",): ["rnn"], ("LSTM",): ["lstm"], ("YOLO", "YOLOV8"): ["yolo", "yolov8"],
    ("MISTRAL", "MISTRAL_7B"): ["mistral", "mistral-7b"],
    # Data Analysis/Visualization
    ("DATA_ANALYSIS",): ["data analysis"], ("DATA_VISUALIZATION",): ["data visualization"],
    ("POWER_BI",): ["power bi"], ("TABLEAU",): ["tableau"], ("EXCEL",): ["excel", "ms excel"],
    ("POWERPOINT",): ["powerpoint", "ms powerpoint"], ("MATPLOTLIB",): ["matplotlib"], ("SEABORN",): ["seaborn"],
    # Other
    ("UI_UX",): ["ui/ux", "ui", "ux"], ("GRADIO",): ["gradio"], ("STREAMLIT",): ["streamlit"],
    ("LINUX",): ["linux"], ("WINDOWS",): ["windows"], ("BASH",): ["bash"], ("API",): ["api", "apis"],
    ("REST",): ["rest", "restful"], ("MICROSERVICES",): ["microservices"],
    # Soft Skills (Keep separate if needed, less reliable with Matcher)
    ("TEAMWORK",): ["teamwork"], ("COMMUNICATION",): ["communication"], ("PROBLEM_SOLVING",): ["problem solving"],
    ("LEADERSHIP",): ["leadership"], ("TIME_MANAGEMENT",): ["time management"], ("CRITICAL_THINKING",): ["critical thinking"],
    ("CREATIVITY",): ["creativity"],
}

class SemanticParser:
    """Enhanced parser for detailed structure."""

    SECTION_KEYWORDS = {
        # ... (keep SECTION_KEYWORDS as before, add more synonyms)
        "PROFILE": ["PROFILE", "ABOUT ME", "SUMMARY", "PROFESSIONAL SUMMARY", "CAREER PROFILE"],
        "CONTACT": ["CONTACT", "CONTACT ME", "CONTACT INFO", "PERSONAL DETAILS"],
        "TECH_SKILLS": ["TECH SKILLS", "TECHNICAL SKILLS", "SKILLS", "SKILL AND EXPERTISE", "TECHNICAL EXPERTISE", "CORE COMPETENCIES"],
        "SOFT_SKILLS": ["SOFT SKILLS", "PROFESSIONAL SKILLS", "INTERPERSONAL SKILLS"],
        "LANGUAGES": ["LANGUAGES", "LANGUAGE PROFICIENCY"],
        "PROJECTS": ["PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"],
        "CERTIFICATIONS": ["CERTIFICATIONS", "AWARDS", "ACCOLADES", "LICENSES & CERTIFICATIONS", "HONORS"],
        "EDUCATION": ["EDUCATION", "ACADEMIC BACKGROUND", "ACADEMICS", "EDUCATIONAL QUALIFICATION"],
        "CAREER_OBJECTIVE": ["CAREER OBJECTIVE", "OBJECTIVE"],
        "EXPERIENCE": ["EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "INTERNSHIPS", "EMPLOYMENT HISTORY"],
        "REFERENCE": ["REFERENCE", "REFERENCES"], # To identify and potentially ignore/handle separately
        "HOBBIES": ["HOBBIES", "INTERESTS"],
        "ACHIEVEMENTS": ["ACHIEVEMENTS", "ACCOMPLISHMENTS"],
    }

    DESCRIPTION_START_WORDS = {"it", "built", "developed", "created", "implemented", "used", "leveraged", "trained", "evaluated", "webframeworks", "this", "the", "responsible", "managed", "coordinated", "assisted", "supported"}
    BULLET_POINTS = {"•", "-", "*", "➢", "◦"}

    DEGREE_KEYWORDS = r'B\.?Tech|M\.?S\.?|B\.?E\.?|Ph\.?D\.?|M\.?B\.?A|Associate(?:s)?|Bachelor(?:s)?|Master(?:s)?|Diploma|High School|HSC|SSLC|10th|12th|Xth|XIIth'
    # Simplified Year Regex
    YEAR_REGEX = r'(?:19|20)\d{2}'
    YEAR_RANGE_REGEX = rf'\b({YEAR_REGEX})\s*[-\u2013to]+\s*({YEAR_REGEX}|Present|Current)\b'
    MONTH_YEAR_REGEX = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Spring|Fall|Summer|Winter)\.?\s+({YEAR_REGEX})\b'

    def __init__(self, output_dir: str = "data/final_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Parser output directory set to: {self.output_dir.resolve()}")

        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model 'en_core_web_sm' loaded.")
        except OSError:
            logger.error("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
            raise

        self.matcher = Matcher(self.nlp.vocab)
        self._build_skill_matcher()

    def _build_skill_matcher(self):
        """Builds spaCy Matcher patterns for skills from SKILL_KEYWORDS."""
        skill_count = 0
        for key_tuple, patterns in SKILL_KEYWORDS.items():
            # Use the first key in the tuple as the primary ID
            skill_id = key_tuple[0]
            matcher_patterns = []
            for pattern_text in patterns:
                matcher_patterns.append([{"LOWER": word.lower()} for word in pattern_text.split()])
            self.matcher.add(skill_id, matcher_patterns)
            skill_count += len(patterns)
        logger.info(f"Built skill matcher with {skill_count} patterns for {len(SKILL_KEYWORDS)} skill concepts.")


    def _find_header_match(self, line_text: str) -> Optional[str]:
        cleaned_line = line_text.strip().upper().replace(":", "") # Remove trailing colons
        if not cleaned_line: return None
        # Exact match first
        for key, keywords in self.SECTION_KEYWORDS.items():
            if cleaned_line in keywords: return key
        # Fuzzy match (more lenient)
        best_match_key = None
        best_score = 75 # Require a decent score
        for key, keywords in self.SECTION_KEYWORDS.items():
            for keyword in keywords:
                 score = fuzz.token_set_ratio(cleaned_line, keyword)
                 if score > best_score:
                      best_score = score
                      best_match_key = key
        # Avoid matching short lines fuzzily unless score is very high
        if best_match_key and (len(cleaned_line.split()) > 3 or best_score > 90):
             return best_match_key
        return None

    def _is_project_title(self, line_text: str) -> bool:
        # (Keep previous logic, maybe make slightly stricter)
        line_text = line_text.strip()
        if not line_text: return False
        if len(line_text.split()) > 9 or len(line_text) > 80: return False # Adjusted length
        if line_text[0] in self.BULLET_POINTS: return False
        first_word = line_text.split()[0].lower().strip(':') if line_text.split() else ""
        if first_word in self.DESCRIPTION_START_WORDS: return False
        # If it contains a clear date range, less likely a title
        if re.search(self.YEAR_RANGE_REGEX, line_text): return False
        # More likely if title case or all caps
        if line_text.istitle() or line_text.isupper(): return True
        if line_text.endswith('.'): return False
        # If the line above was empty or a header, this is more likely a title
        # (Needs context from main loop, harder to implement here cleanly)
        # Default true if passes initial checks
        return True


    def _clean_key(self, text: str) -> str:
        key = re.sub(r'[^\w\s-]', '', text).strip()
        key = re.sub(r'[-\s]+', '_', key)
        return key.upper()

    # --- ENHANCED DETAILED PARSING FUNCTIONS ---

    def _extract_contact_info(self, texts: List[str], links: List[Dict]) -> Dict:
        """Searches combined text and extracted links for contact details."""
        full_text = "\n".join(texts)
        contact = {"email": None, "phone": None, "linkedin": None, "github": None, "location": None, "other_links": []}

        # Regex extractions from text
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text)
        if email_match: contact["email"] = email_match.group(0)
        phone_match = re.search(r'(\+?\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}', full_text)
        if phone_match: contact["phone"] = re.sub(r'[()\-\.\s]', '', phone_match.group(0))

        # Link extraction (prioritize links from fitz, then regex)
        found_linkedin = False
        found_github = False
        for link in links:
            url = link.get('url', '').lower()
            if 'linkedin.com/in/' in url and not found_linkedin:
                contact["linkedin"] = link['url']
                found_linkedin = True
            elif 'github.com/' in url and not found_github:
                 # Avoid generic github.com link if specific one exists
                 if len(url.split('/')) > 3:
                      contact["github"] = link['url']
                      found_github = True
            else:
                contact["other_links"].append(link['url'])

        # Regex fallback for links if not found by fitz
        if not found_linkedin:
            linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?', full_text, re.IGNORECASE)
            if linkedin_match: contact["linkedin"] = linkedin_match.group(0)
        if not found_github:
            github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[\w-]+/?', full_text, re.IGNORECASE)
            # Check length again to avoid generic github.com
            if github_match and len(github_match.group(0).split('/')) > 3:
                contact["github"] = github_match.group(0)

        # Location using spaCy NER on combined text
        doc = self.nlp(full_text)
        locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
        if locations: contact["location"] = locations[0]
        else:
             loc_match = re.search(r'\b[A-Z][a-zA-Z\s-]+,\s*[A-Z][a-zA-Z\s]+\b', full_text) # City, State/Country
             if loc_match: contact["location"] = loc_match.group(0).strip()

        if not contact["other_links"]: del contact["other_links"] # Clean up empty list
        return contact


    def _extract_name(self, texts: List[str]) -> Optional[str]:
        """Looks for name, prioritizing early lines and PERSON entities."""
        full_text = "\n".join(texts)
        doc = self.nlp(full_text)
        # Look near the beginning for PERSON entities
        for ent in doc.ents:
             if ent.label_ == "PERSON" and ent.start_char < 100: # Heuristic: Name usually near top
                  name_text = ent.text.strip()
                  # Basic checks: multiple words, not a known header
                  if len(name_text.split()) > 1 and len(name_text) > 3 and self._find_header_match(name_text) is None:
                       return name_text

        # Fallback: Capitalized words at the very beginning
        first_lines = "\n".join(full_text.split('\n')[:3]) # Check first 3 lines
        name_match = re.match(r'^\s*([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+)+)\b', first_lines)
        if name_match:
             potential_name = name_match.group(1).strip()
             if self._find_header_match(potential_name) is None:
                  return potential_name
        return None

    def _parse_skills(self, tech_text: str, soft_text: str) -> Dict[str, List[str]]:
        """Extracts technical and soft skills separately."""
        skills = {"technical": [], "soft": []}

        # Technical skills using Matcher + splitting
        if tech_text:
            doc_tech = self.nlp(tech_text)
            matches = self.matcher(doc_tech)
            tech_set = set()
            for match_id, start, end in matches:
                 skill_name = self.nlp.vocab.strings[match_id]
                 # Filter out potential soft skills matched in tech section
                 if "SOFT_" not in skill_name: # Check against SECTION_KEYWORDS if needed
                      tech_set.add(doc_tech[start:end].text.lower())

            # Add skills from splitting lines as fallback
            for line in tech_text.split('\n'):
                cleaned_line = line.strip().lower().lstrip('-•*➢ ').strip()
                if cleaned_line and len(cleaned_line.split()) <= 4 and len(cleaned_line) > 1:
                     is_sub = any(cleaned_line in s for s in tech_set)
                     # Avoid adding lines that look like category headers
                     if not is_sub and "interest" not in cleaned_line and "expertise" not in cleaned_line:
                          tech_set.add(cleaned_line)
            skills["technical"] = sorted(list(tech_set))

        # Soft skills primarily by splitting
        if soft_text:
            soft_set = set()
            for line in soft_text.split('\n'):
                cleaned_line = line.strip().lower().lstrip('-•*➢ ').strip()
                if cleaned_line and len(cleaned_line.split()) <= 3 and len(cleaned_line) > 2:
                     soft_set.add(cleaned_line.capitalize()) # Capitalize for consistency
            skills["soft"] = sorted(list(soft_set))

        return skills

    def _parse_education_details(self, text: str) -> List[Dict]:
        """Enhanced parsing for structured education entries."""
        entries = []
        # Split logic remains the same - adjust regex if needed
        blocks = re.split(r'\n(?=\s*[A-Z][A-Za-z\s.,&-]+(?:institute|university|school|college|matriculation|technology)\b)', text, flags=re.IGNORECASE)

        for block in blocks:
            block = block.strip()
            if not block: continue

            entry = {"institution": None, "degree": None, "field_of_study": None,
                     "years": None, "gpa": None, "percentage_10th": None,
                     "percentage_12th": None, "details": []}
            lines = block.split('\n')
            processed_lines = set() # Track lines used

            # 1. Institution
            if lines:
                entry["institution"] = lines[0].replace("school :", "").replace("college :", "").strip()
                processed_lines.add(0)

            # --- Iterate through lines for details ---
            for i, line in enumerate(lines):
                 if i in processed_lines: continue
                 line_strip = line.strip()
                 line_lower = line_strip.lower()

                 # 2. Years
                 year_match = re.search(self.YEAR_RANGE_REGEX, line_strip)
                 if year_match and entry["years"] is None:
                      entry["years"] = year_match.group(0)
                      processed_lines.add(i)
                      continue

                 # 3. Degree and Field
                 degree_match = re.search(rf'(degree\s*[:\-]?\s*)?\b({self.DEGREE_KEYWORDS})\b(?:[\s\-:]+([\w\s,&-]+))?', line_strip, re.IGNORECASE)
                 if degree_match and entry["degree"] is None:
                      degree_raw = degree_match.group(2).strip().replace('.','').upper()
                      # Standardize common degrees
                      if degree_raw in ["BTECH", "BE"]: entry["degree"] = "Bachelor"
                      elif degree_raw in ["MS", "MSC"]: entry["degree"] = "Master"
                      elif degree_raw in ["10TH", "SSLC", "XTH"]: entry["degree"] = "10th Grade / SSLC"
                      elif degree_raw in ["12TH", "HSC", "XIITH"]: entry["degree"] = "12th Grade / HSC"
                      else: entry["degree"] = degree_match.group(2).strip() # Keep original if not standard

                      if degree_match.group(3):
                           entry["field_of_study"] = degree_match.group(3).strip()
                      processed_lines.add(i)
                      continue

                 # 4. Scores (Handle 10th/12th specifically)
                 perc_10_match = re.search(r'(?:percentage|marks|score)\s*[:\-]?\s*([\d\.]+%?)\s*(?:\((?:10th|Xth|sslc)[^\)]*\))', line_lower)
                 if perc_10_match and entry["percentage_10th"] is None:
                      entry["percentage_10th"] = perc_10_match.group(1).strip()
                      processed_lines.add(i)
                      continue

                 perc_12_match = re.search(r'(?:percentage|marks|score)\s*[:\-]?\s*([\d\.]+%?)\s*(?:\((?:12th|XIIth|hsc)[^\)]*\))', line_lower)
                 if perc_12_match and entry["percentage_12th"] is None:
                      entry["percentage_12th"] = perc_12_match.group(1).strip()
                      processed_lines.add(i)
                      continue

                 gpa_match = re.search(r'(cgpa|gpa)\s*[:\-]?\s*([\d\.]+)', line_lower)
                 if gpa_match and entry["gpa"] is None:
                      entry["gpa"] = gpa_match.group(2).strip()
                      processed_lines.add(i)
                      continue

                 # If line wasn't processed, add to details
                 if i not in processed_lines and line_strip:
                    entry["details"].append(line_strip)


            # Clean up entry
            entry["details"] = "\n".join(entry["details"]).strip()
            if not entry["details"]: del entry["details"]
            # Remove keys with None values
            entry = {k: v for k, v in entry.items() if v is not None}

            if len(entry) > 1: # Only add if more than just details were found
                 entries.append(entry)

        return entries


    def _parse_certifications(self, text: str) -> List[str]:
        return [line.strip().lstrip('•-*➢ ').strip() for line in text.split('\n') if line.strip()]

    def _parse_projects(self, text: str) -> Dict[str, Dict]:
        """Splits project section into structured dictionaries."""
        projects_dict = {}
        project_lines = text.split('\n')
        current_project_key = None
        current_project_data = None

        for line in project_lines:
            line = line.strip()
            if not line: continue

            # Check if line looks like a new title
            if self._is_project_title(line):
                # If we were already building a project, store it first
                # (This check isn't strictly needed with the current logic but good practice)
                # if current_project_key and current_project_data:
                #    projects_dict[current_project_key] = current_project_data

                project_key_base = self._clean_key(line)
                if not project_key_base: project_key_base = f"UNTITLED_{len(projects_dict)}"
                current_project_key = project_key_base
                current_project_data = {"title": line, "description": []}
                projects_dict[current_project_key] = current_project_data

            elif current_project_data is not None:
                # If we have an active project, add this line to its description
                current_project_data["description"].append(line)
            # else: # Line before the first detected title - ignore for now or add to misc

        # Join description lists for final output
        for key, data in projects_dict.items():
            data["description"] = "\n".join(data["description"])

        return projects_dict

    # --- Main Parsing Method ---

    def parse_file(self, jsonl_path: str) -> Optional[str]: # Return path or None
        """
        Reads JSONL, performs section splitting AND detailed parsing, saves final JSON.
        """
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                extractor_data = json.load(f) # Use json.load
        except Exception as e:
            logger.error(f"Could not read or parse JSONL file {jsonl_path}: {e}")
            return None

        column_texts: List[str] = extractor_data.get('column_texts', [])
        links: List[Dict] = extractor_data.get('links', []) # Get links

        # --- Stage 1: Initial Section Splitting ---
        raw_sections = defaultdict(list)
        current_header_key = "HEADER_INFO"

        # Combine text from all columns before splitting
        full_doc_text = "\n".join(column_texts)
        lines = full_doc_text.split('\n')

        for line_text in lines:
            line_text = line_text.strip()
            if not line_text or line_text.startswith("--- Page") or line_text.startswith("--- Column Break"): continue # Skip separators

            header_key = self._find_header_match(line_text)
            if header_key:
                current_header_key = header_key
                # Initialize section if first time seen
                if not raw_sections[current_header_key]:
                     raw_sections[current_header_key] = []
            else:
                 # Ensure list exists before appending
                 if not raw_sections[current_header_key]:
                      raw_sections[current_header_key] = []
                 raw_sections[current_header_key].append(line_text)

        # Join lines within each raw section
        section_texts = {key: "\n".join(lines) for key, lines in raw_sections.items()}

        # --- Stage 2: Detailed Parsing of Sections ---
        final_json = {
            "source": extractor_data.get("source"),
            "metadata": extractor_data.get("metadata"),
            "personal_info": {"name": None, "contact": {}},
            "summary": None,
            "skills": {"technical": [], "soft": []},
            "education": [],
            "projects": {},
            "certifications": [],
            "languages": [],
            "achievements": [], # Added achievements
            "hobbies": [],      # Added hobbies
            "misc": {}
        }

        # Extract Name and Contact (search across header + contact + reference + links)
        contact_search_text_list = [
             section_texts.get("HEADER_INFO", ""),
             section_texts.get("CONTACT", ""),
             section_texts.get("REFERENCE", "") # Include Reference section text
        ]
        final_json["personal_info"]["name"] = self._extract_name(contact_search_text_list)
        final_json["personal_info"]["contact"] = self._extract_contact_info(contact_search_text_list, links) # Pass links here

        # Process known sections using dedicated functions
        if section_texts.get("PROFILE"): final_json["summary"] = section_texts["PROFILE"]
        elif section_texts.get("CAREER_OBJECTIVE"): final_json["summary"] = section_texts["CAREER_OBJECTIVE"]

        final_json["skills"] = self._parse_skills(section_texts.get("TECH_SKILLS", ""), section_texts.get("SOFT_SKILLS", ""))

        if section_texts.get("EDUCATION"): final_json["education"] = self._parse_education_details(section_texts["EDUCATION"])
        if section_texts.get("CERTIFICATIONS"): final_json["certifications"] = self._parse_certifications(section_texts["CERTIFICATIONS"])
        if section_texts.get("LANGUAGES"): final_json["languages"] = [s.strip().lstrip('-•*➢ ') for s in section_texts["LANGUAGES"].split('\n') if s.strip()]
        if section_texts.get("ACHIEVEMENTS"): final_json["achievements"] = self._parse_certifications(section_texts["ACHIEVEMENTS"]) # Reuse cert logic for splitting
        if section_texts.get("HOBBIES"): final_json["hobbies"] = [s.strip().lstrip('-•*➢ ') for s in section_texts["HOBBIES"].split('\n') if s.strip()]

        if section_texts.get("PROJECTS"): final_json["projects"] = self._parse_projects(section_texts["PROJECTS"])

        # Collect miscellaneous sections
        processed_keys = set(final_json.keys()) | {"HEADER_INFO", "CONTACT", "CAREER_OBJECTIVE", "REFERENCE"} # Add REFERENCE here
        for key, text in section_texts.items():
            if key not in processed_keys and text:
                final_json["misc"][key] = text
        if not final_json["misc"]: del final_json["misc"]

        # --- Stage 3: Save Final JSON ---
        output_path = self.output_dir / f"{Path(jsonl_path).stem}_final.json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Saved final parsed file: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Could not save final parsed JSON {output_path}: {e}")
            return None

# -------------- CLI Usage --------------
if __name__ == "__main__":
    INPUT_DIR = "data/downloads"
    OUTPUT_DIR = "data/final_output" # Consistent output dir name

    jsonl_files = glob.glob(f"{INPUT_DIR}/*.jsonl")

    if not jsonl_files:
        print(f"No .jsonl files found in {INPUT_DIR}.")
        print(f"Please run extractor.py first.")
        sys.exit(1)

    parser = SemanticParser(output_dir=OUTPUT_DIR)

    for file_path in jsonl_files:
        print(f"Parsing: {file_path}...")
        try:
            parser.parse_file(file_path)
        except Exception as e:
            print(f"   -> FAILED: {e}")