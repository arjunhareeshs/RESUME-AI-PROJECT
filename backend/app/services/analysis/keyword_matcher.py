def calculate_role_match(extracted_data: dict, job_description: str) -> dict:
    """
    Compares keywords in the resume to a job description.
    This should be upgraded to use NLP (e.g., spaCy) for real matching.
    """
    # Simple, naive keyword extraction
    jd_keywords = set([w.lower().strip(".,") for w in job_description.split() if len(w) > 3])
    resume_text = str(extracted_data).lower() # Dump all data to a string
    
    found = []
    missing = []
    
    if not jd_keywords:
        return {"percentage": 0, "found": [], "missing": []}

    for keyword in jd_keywords:
        if keyword in resume_text:
            found.append(keyword)
        else:
            missing.append(keyword)
            
    percentage = int((len(found) / len(jd_keywords)) * 100)
    
    return {"percentage": percentage, "found": list(set(found)), "missing": list(set(missing))}