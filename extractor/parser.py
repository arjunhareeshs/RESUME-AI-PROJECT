# extractor/parser.py

import re
from typing import Dict, Any, List

class ResumeParser:
    """
    Takes raw, messy text from the extractor and parses it
    into a structured dictionary.
    """

    def __init__(self):
        """Initializes typo maps and section regex."""
        self.TYPO_MAP = {
            "data strucutres": "Data Structures",
            "tennsorflow": "tensorflow",
            "buisness": "Business",
            "prediector": "predictor",
            "bannri amman": "Bannari Amman",
            "entrepeuners": "entrepreneurs",
        }
        
        self.SECTION_HEADERS = [
            "PROFILE", "CONTACT", "TECH SKILLS", "SOFT SKILLS", 
            "LANGUAGES", "PROJECTS", "EDUCATION", "CERTIFICATIONS"
        ]
        
        # This regex finds headers to split the text on
        self.SECTION_REGEX = re.compile(
            r'\b(' + '|'.join(self.SECTION_HEADERS) + r')\b',
            re.IGNORECASE
        )

    def _clean_text(self, text: str) -> str:
        """Fixes low-level text errors like missing spaces and typos."""
        
        # 1. Fix broken LinkedIn/GitHub links
        text = re.sub(
            r'(\b(?:linkedin\.com/in|github\.com)/[a-zA-Z0-9_-]+)\n([a-zA-Z0-9_-]+)',
            r'\1\2',
            text
        )
        
        # 2. Insert missing spaces
        text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'(\.(?:com|in|org|net))([a-zA-Z])', r'\1 \2', text, flags=re.IGNORECASE)
        text = re.sub(r'([a-zA-Z])(https?|www)', r'\1 \2', text, flags=re.IGNORECASE)
        
        # 3. Fix known typos
        for bad, good in self.TYPO_MAP.items():
            text = re.sub(rf'\b{bad}\b', good, text, flags=re.IGNORECASE)
            
        # 4. Forcibly add newlines around headers to separate sections
        for header in self.SECTION_HEADERS:
            text = re.sub(
                rf'\b({header})\b',
                r'\n\n\1\n\n',
                text,
                flags=re.IGNORECASE
            )
            
        # 5. Collapse excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 6. Remove form feed character
        text = text.replace('\f', '')
        
        return text.strip()

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Splits the full text into a dictionary of sections."""
        sections = {}
        
        # This regex looks for headers on their own line
        section_regex = re.compile(
            r"^\s*(" + "|".join(self.SECTION_HEADERS) + r")\s*$",
            re.MULTILINE | re.IGNORECASE
        )

        matches = list(section_regex.finditer(text))
        
        if not matches:
            sections["GENERAL"] = text
            return sections

        # Extract content between headers
        for i, match in enumerate(matches):
            section_name = match.group(1).upper()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_content = text[start_pos:end_pos].strip()
            
            if section_content:
                sections[section_name] = section_content
        
        # Capture text before the first header
        first_header_start = matches[0].start()
        header_content = text[:first_header_start].strip()
        if header_content:
            sections["HEADER"] = header_content
            
        return sections

    def _extract_entities(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """Extracts specific data points from the section text."""
        parsed_data = {}
        
        # Join all text with newlines to find contact info
        all_text = "\n".join(sections.values())
        
        # --- Precise Regex Patterns ---
        email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov|io|in))\b'
        phone_pattern = r'(\+91[\s-]?\d{10})\b'
        linkedin_pattern = r'\b((?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)\b'
        github_pattern = r'\b((?:https?://)?github\.com/[a-zA-Z0-9_-]+)\b'

        parsed_data["contact"] = {
            "email": self._find_entity(email_pattern, all_text),
            "phone": self._find_entity(phone_pattern, all_text),
            "linkedin": self._find_entity(linkedin_pattern, all_text),
            "github": self._find_entity(github_pattern, all_text)
        }
        
        if "EDUCATION" in sections:
            edu_text = sections["EDUCATION"]
            parsed_data["education"] = {
                "cgpa": self._find_entity(r'cGPA:\s*([0-9.]+)', edu_text),
                "10th_perc": self._find_entity(r'(\d+)[\s%]+.*?10th', edu_text),
                "12th_perc": self._find_entity(r'(\d+)[\s%]+.*?12th', edu_text)
            }
        
        # Add other sections as lists or single strings
        for section in ["PROFILE", "PROJECTS", "TECH SKILLS", "SOFT SKILLS", "CERTIFICATIONS", "LANGUAGES"]:
            if section in sections:
                content = sections[section].strip()
                items = [item.strip() for item in content.split('\n') if item.strip()]
                
                if len(items) <= 1:
                    parsed_data[section.lower()] = content
                else:
                    parsed_data[section.lower()] = items

        return parsed_data

    def _find_entity(self, pattern: str, text: str) -> str | None:
        """Helper to find regex match or return None (case-insensitive)."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """
        Main method to clean, parse, and structure the resume text.
        """
        cleaned_text = self._clean_text(raw_text)
        sections = self._parse_sections(cleaned_text)
        structured_data = self._extract_entities(sections)
        structured_data["_raw_sections"] = sections
        
        return structured_data