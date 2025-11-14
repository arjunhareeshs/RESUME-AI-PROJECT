from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# For POST /generate_resume
class ResumeGenerationRequest(BaseModel):
    name: str
    role: str
    education: List[Dict[str, str]]
    projects: List[Dict[str, str]]
    skills: List[str]
    experience: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    awards: Optional[List[str]] = None
    volunteer: Optional[List[Dict[str, Any]]] = None
    interests: Optional[List[str]] = None
    summary: Optional[str] = None
    target_role: Optional[str] = None

# For POST /analyze_resume
class ResumeAnalysisRequest(BaseModel):
    job_description: str

# Base response model
class Resume(BaseModel):
    id: int
    user_id: int
    file_type: str
    ats_score: int
    role_match: int
    created_at: datetime
    extracted_data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)