# eval/evaluator.py
import re
import json
from pathlib import Path
from typing import Dict
from rapidfuzz.distance import Levenshtein
import pdfplumber
import docx2txt

# -----------------------------
# TEXT NORMALIZATION & METRICS
# -----------------------------
def normalize_text(t: str) -> str:
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def char_error_rate(ref: str, hyp: str) -> float:
    r = normalize_text(ref)
    h = normalize_text(hyp)
    dist = Levenshtein.distance(r, h)
    denom = max(1, len(r))
    return dist / denom

def word_error_rate(ref: str, hyp: str) -> float:
    r = normalize_text(ref).split()
    h = normalize_text(hyp).split()
    m, n = len(r), len(h)
    if m == 0:
        return 0.0 if n == 0 else 1.0
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1):
        dp[i][0] = i
    for j in range(n+1):
        dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    return dp[m][n] / m

def normalized_levenshtein(ref: str, hyp: str) -> float:
    r = normalize_text(ref)
    h = normalize_text(hyp)
    dist = Levenshtein.distance(r, h)
    max_len = max(1, len(r), len(h))
    return 1.0 - (dist / max_len)

def token_overlap(ref: str, hyp: str) -> float:
    r = set(normalize_text(ref).split())
    h = set(normalize_text(hyp).split())
    if not r:
        return 0.0
    return len(r.intersection(h)) / len(r)

def evaluate_pair(ref_text: str, hyp_text: str) -> dict:
    return {
        "CER": char_error_rate(ref_text, hyp_text),
        "WER": word_error_rate(ref_text, hyp_text),
        "Normalized_Levenshtein": normalized_levenshtein(ref_text, hyp_text),
        "Token_Overlap": token_overlap(ref_text, hyp_text)
    }

# -----------------------------
# RESUME EXTRACTION
# -----------------------------
def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using multiple methods for better accuracy"""
    text = ""
    
    # Method 1: Try pdfplumber first (better for tables and layout)
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    
    # Method 2: Fallback to PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(file_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text() + "\n"
        doc.close()
        if text.strip():
            return text
    except Exception as e:
        print(f"PyMuPDF failed: {e}")
    
    # Method 3: Try pdfminer as last resort
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(file_path)
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfminer failed: {e}")
    
    raise ValueError(f"Could not extract text from {file_path} using any method")

def extract_text_from_docx(file_path: str) -> str:
    return docx2txt.process(file_path)

# -----------------------------
# CLEANING & SEGMENTATION
# -----------------------------
def clean_resume_text(raw_text: str) -> str:
    """Clean and normalize resume text"""
    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\n+', '\n', raw_text)
    
    # Fix broken words at line breaks (common in PDF extraction)
    text = re.sub(r'\n([a-z])', r' \1', text)
    
    # Remove excessive spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove special characters that might interfere with parsing
    text = re.sub(r'[^\w\s@\.\+\-\(\)\/\:]', ' ', text)
    
    # Clean up email patterns
    text = re.sub(r'\s+@\s+', '@', text)
    
    # Clean up phone number patterns
    text = re.sub(r'\s+\+\s+', '+', text)
    
    return text.strip()

def segment_resume(text: str) -> dict:
    """Segment resume text into structured sections"""
    # Expanded list of common resume headers
    headers = [
        "PROFILE", "SUMMARY", "OBJECTIVE", "ABOUT", "ABOUT ME",
        "CONTACT", "CONTACT INFORMATION", "CONTACT DETAILS",
        "PROJECTS", "PROJECT EXPERIENCE", "PERSONAL PROJECTS",
        "TECH SKILLS", "TECHNICAL SKILLS", "SKILLS", "TECHNOLOGIES",
        "CERTIFICATIONS", "CERTIFICATES", "CERTIFICATE",
        "SOFT SKILLS", "INTERPERSONAL SKILLS", "PERSONAL SKILLS",
        "EDUCATION", "ACADEMIC BACKGROUND", "QUALIFICATIONS",
        "LANGUAGES", "LANGUAGE SKILLS", "LANGUAGE PROFICIENCY",
        "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE",
        "INTERNSHIP", "INTERNSHIPS", "INTERNSHIP EXPERIENCE",
        "ACHIEVEMENTS", "ACCOMPLISHMENTS", "AWARDS",
        "HOBBIES", "INTERESTS", "PERSONAL INTERESTS"
    ]
    
    # Create pattern that matches headers with optional punctuation
    header_pattern = re.compile(r'^(' + '|'.join(headers) + r')[:\s]*$', re.I)

    sections = {}
    current_section = None
    other_content = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
            
        # Check if this line is a header
        if header_pattern.match(line):
            current_section = line.upper().rstrip(' :')
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)
        else:
            # Content before any section header
            other_content.append(line)

    # Join content for each section
    for k in sections:
        sections[k] = " ".join(sections[k]).strip()
    
    # Add any content that didn't fit into sections
    if other_content:
        sections["OTHER"] = " ".join(other_content).strip()
    
    # Remove empty sections
    sections = {k: v for k, v in sections.items() if v}
    
    return sections

# -----------------------------
# PROCESS RESUME TO JSON
# -----------------------------
def process_resume(file_path: str, output_json_path: str, reference_json_path: str = None):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        raw_text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Only PDF and DOCX allowed.")

    cleaned_text = clean_resume_text(raw_text)
    segmented = segment_resume(cleaned_text)

    metrics = {}
    if reference_json_path:
        with open(reference_json_path, "r", encoding="utf-8") as f:
            reference = json.load(f)
        for section, content in segmented.items():
            ref_content = reference.get(section, "")
            metrics[section] = evaluate_pair(ref_content, content)

    output_data = {
        "file_name": Path(file_path).name,
        "segmented_text": segmented,
        "evaluation_metrics": metrics
    }

    Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)

    print(f"✅ JSON saved to: {output_json_path}")
    return output_data

# -----------------------------
# EXAMPLE USAGE
# -----------------------------
if __name__ == "__main__":
    resume_file = "data/uploads/resume1.pdf"
    output_json = "examples/resumes/resume1.json"
    reference_json = None  # Optional

    data = process_resume(resume_file, output_json, reference_json)
    print("Preview of segmented text:\n", json.dumps(data["segmented_text"], indent=2)[:500])
