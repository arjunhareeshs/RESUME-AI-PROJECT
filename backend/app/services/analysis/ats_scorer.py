import re
from typing import Dict, List, Iterable

CORE_SECTIONS = [
    ("summary", "Add a concise professional summary near the top."),
    ("experience", "Ensure an 'Experience' section with role details is present."),
    ("education", "Include an 'Education' section with degrees or certifications."),
    ("skills", "List relevant skills under a dedicated 'Skills' section."),
    ("projects", "Highlight key projects in a 'Projects' or 'Portfolio' section."),
]


def _gather_text(extracted_data: Dict) -> str:
    """
    Attempt to gather raw text from the extracted structure.
    """
    text_chunks: List[str] = []
    sections = extracted_data.get("sections")

    if isinstance(sections, dict):
        for value in sections.values():
            if isinstance(value, str):
                text_chunks.append(value)
            elif isinstance(value, Iterable):
                text_chunks.extend([str(item) for item in value if item])

    if not text_chunks:
        raw = extracted_data.get("raw_text") or extracted_data.get("text")
        if isinstance(raw, str):
            text_chunks.append(raw)

    metadata = extracted_data.get("metadata", {})
    if isinstance(metadata, dict):
        body = metadata.get("full_text")
        if isinstance(body, str):
            text_chunks.append(body)

    return "\n".join(text_chunks).lower()


def _has_section(name: str, extracted_data: Dict, text: str) -> bool:
    """
    Determine whether a section exists either by structured data or by heading search.
    """
    sections = extracted_data.get("sections")
    if isinstance(sections, dict):
        for key in sections.keys():
            if name in key.lower():
                return True

    # Fallback to heading detection in raw text
    heading_pattern = re.compile(rf"^\s*{name}s?:", re.IGNORECASE | re.MULTILINE)
    if heading_pattern.search(text):
        return True

    # Additional heuristic: look for the word as a standalone heading
    words_pattern = re.compile(rf"\b{name}\b", re.IGNORECASE)
    return bool(words_pattern.search(text))


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _contains_quantified_metrics(text: str) -> bool:
    patterns = [
        r"\b\d{1,3}%\b",
        r"\b\d{1,3}\s?(?:k|m|million|billion)\b",
        r"\b\d+\s?(?:years?|projects?|people|users|clients)\b",
        r"\b\d+\+\b",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _has_contact_info(text: str) -> Dict[str, bool]:
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    phone_pattern = r"\+?\d[\d\s\-()]{8,}"
    linkedin_pattern = r"linkedin\.com"

    return {
        "email": bool(re.search(email_pattern, text)),
        "phone": bool(re.search(phone_pattern, text)),
        "linkedin": bool(re.search(linkedin_pattern, text)),
    }


def _skills_count(extracted_data: Dict, text: str) -> int:
    skills = extracted_data.get("skills")
    if isinstance(skills, list):
        return len([skill for skill in skills if isinstance(skill, str) and skill.strip()])

    skills_section = extracted_data.get("sections", {}).get("skills")
    if isinstance(skills_section, list):
        return len([skill for skill in skills_section if isinstance(skill, str) and skill.strip()])
    if isinstance(skills_section, str):
        return len(re.findall(r"\b\w+\b", skills_section))

    # fallback: heuristically parse a skills line from text
    match = re.search(r"skills?:\s*(.+)", text, re.IGNORECASE)
    if match:
        return len([item.strip() for item in match.group(1).split(",") if item.strip()])

    return 0


def calculate_ats_score(extracted_data: dict, font_stats: dict, bullet_used: bool) -> dict:
    """
    Calculates an ATS-friendly score based on structural, content, and formatting heuristics.
    """
    score = 0
    feedback: List[str] = []

    aggregated_text = _gather_text(extracted_data)

    # SECTION COVERAGE (35 points total, 7 each for core sections)
    for section_name, guidance in CORE_SECTIONS:
        if _has_section(section_name, extracted_data, aggregated_text):
            score += 7
        else:
            feedback.append(guidance)

    # CONTACT INFORMATION (15 points: email 7, phone 5, LinkedIn 3)
    contact_hits = _has_contact_info(aggregated_text)
    if contact_hits["email"]:
        score += 7
    else:
        feedback.append("Include a professional email address in your contact details.")

    if contact_hits["phone"]:
        score += 5
    else:
        feedback.append("Add a reachable phone number for recruiters to contact you.")

    if contact_hits["linkedin"]:
        score += 3
    else:
        feedback.append("Link to your LinkedIn profile to bolster credibility.")

    # QUANTIFIED IMPACT (10 points)
    if _contains_quantified_metrics(aggregated_text):
        score += 10
    else:
        feedback.append("Add quantified achievements (e.g., “Improved efficiency by 20%”).")

    # SKILLS DEPTH (10 points)
    skills_count = _skills_count(extracted_data, aggregated_text)
    if skills_count >= 5:
        score += 10
    elif skills_count >= 1:
        score += 5
        feedback.append("Expand your skills section with more role-specific keywords.")
    else:
        feedback.append("Include a dedicated skills section listing your core competencies.")

    # FORMATTING CONSISTENCY (10 points)
    fonts = font_stats.get("fonts") or []
    unique_fonts = len(set(fonts))
    if unique_fonts == 0:
        # no font data; neutral outcome
        score += 5
    elif unique_fonts <= 2:
        score += 10
    else:
        score += 5
        feedback.append(f"Reduce the number of font families used (currently {unique_fonts}). Stick to 1–2.")

    # BULLET POINT USAGE (10 points)
    if bullet_used:
        score += 10
    else:
        feedback.append("Use bullet points to highlight achievements and responsibilities for better ATS parsing.")

    # LENGTH & DENSITY (10 points)
    word_count = _word_count(aggregated_text)
    if 250 <= word_count <= 750:
        score += 10
    elif word_count < 250:
        score += 5
        feedback.append("Resume appears short; consider expanding experience and accomplishments.")
    else:
        score += 5
        feedback.append("Resume is lengthy; keep it concise (ideally 1–2 pages for most roles).")

    # Clamp final score between 0 and 100
    score = max(0, min(100, score))

    return {
        "score": score,
        "feedback": feedback,
        "metadata": {
            "word_count": word_count,
            "skills_detected": skills_count,
            "contact": contact_hits,
        },
    }