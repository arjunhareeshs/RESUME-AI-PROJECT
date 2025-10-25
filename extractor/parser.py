import re
from typing import Dict, Any, List

class ResumeParser:
    """
    Takes raw, messy text from the extractor and parses it
    into a structured dictionary.
    """

    def __init__(self):
        # Dictionary for fixing common typos
        self.TYPO_MAP = {
            "data strucutres": "Data Structures",
            "tennsorflow": "tensorflow",
            "buisness": "Business",
            "prediector": "predictor", # Typo from your sample
            "bannri amman": "Bannari Amman", # Typo from your sample
        }
        
        # Regex for finding section headers
        # This looks for headers (like 'EDUCATION') that are likely on their own line
        self.SECTION_HEADERS = [
            "PROFILE", "CONTACT", "TECH SKILLS", "SOFT SKILLS", 
            "LANGUAGES", "PROJECTS", "EDUCATION", "CERTIFICATIONS"
        ]
        self.SECTION_REGEX = re.compile(
            r"^\s*(" + "|".join(self.SECTION_HEADERS) + r")\s*$",
            re.MULTILINE | re.IGNORECASE
        )

    def _clean_text(self, text: str) -> str:
        """Fixes low-level text errors."""
        
        # 1. Fix broken LinkedIn/GitHub links
        # (e.g., "github.com/arjunha\nreeshs" -> "github.com/arjunhareeshs")
        text = re.sub(
            r'(\b(?:linkedin\.com/in|github\.com)/[a-zA-Z0-9_-]+)\n([a-zA-Z0-9_-]+)',
            r'\1\2',
            text
        )
        
        # 2. Fix known typos
        for bad, good in self.TYPO_MAP.items():
            text = re.sub(rf'\b{bad}\b', good, text, flags=re.IGNORECASE)
            
        # 3. Collapse excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 4. Remove form feed character (often at end of PDF page)
        text = text.replace('\f', '')
        
        return text.strip()

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Splits the full text into a dictionary of sections."""
        sections = {}
        
        # Find all section headers
        matches = list(self.SECTION_REGEX.finditer(text))
        
        if not matches:
            # If no headers found, return all text under a 'general' key
            return {"GENERAL": text}

        for i, match in enumerate(matches):
            section_name = match.group(1).upper()
            
            # Start position of the section content
            start_pos = match.end()
            
            # End position of the section content
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            section_content = text[start_pos:end_pos].strip()
            
            # Clean up content (remove leading/trailing newlines)
            section_content = re.sub(r'^\n+|\n+$', '', section_content)
            
            sections[section_name] = section_content
            
        return sections

    def _extract_entities(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """Extracts specific data points from the section text."""
        parsed_data = {}
        
        if "CONTACT" in sections:
            contact_text = sections["CONTACT"]
            parsed_data["contact"] = {
                "email": re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', contact_text),
                "phone": re.search(r'(\+91[\s-]?\d{10})', contact_text),
                "linkedin": re.search(r'(linkedin\.com/in/[^\s]+)', contact_text),
                "github": re.search(r'(github\.com/[^\s]+)', contact_text)
            }
            # Convert match objects to strings, or None if not found
            for key, match in parsed_data["contact"].items():
                parsed_data["contact"][key] = match.group(1) if match else None
        
        if "EDUCATION" in sections:
            edu_text = sections["EDUCATION"]
            parsed_data["education"] = {
                "cgpa": re.search(r'cGPA:\s*([0-9.]+)', edu_text),
                "10th_perc": re.search(r'(\d+)[\s%]+.*?10th', edu_text),
                "12th_perc": re.search(r'(\d+)[\s%]+.*?12th', edu_text)
            }
            for key, match in parsed_data["education"].items():
                parsed_data["education"][key] = match.group(1) if match else None
        
        # You can add extractors for "PROJECTS", "SKILLS", etc.
        
        return parsed_data

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """Main method to clean, parse, and structure the resume text."""
        
        # 1. Clean the text
        cleaned_text = self._clean_text(raw_text)
        
        # 2. Split into sections
        sections = self._parse_sections(cleaned_text)
        
        # 3. Extract specific entities
        structured_data = self._extract_entities(sections)
        
        # Add the raw sections for context
        structured_data["_raw_sections"] = sections
        
        return structured_data