from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ... import models, schemas
from ..deps import get_db, get_current_user
from ...services.analysis import ats_scorer, keyword_matcher

router = APIRouter()

@router.post("/analyze_resume")
async def analyze_resume_endpoint(
    resume_id: int,
    request: schemas.resume.ResumeAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: models.user.User = Depends(get_current_user),
):
    """
    Analyze an extracted resume against a job description.
    """
    # 1. Get the resume
    resume = db.query(models.resume.Resume).filter(
        models.resume.Resume.id == resume_id,
        models.resume.Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if not resume.extracted_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume has not been extracted yet")

    # 2. Calculate ATS Score
    ats_result = ats_scorer.calculate_ats_score(
        resume.extracted_data, resume.font_stats, resume.bullet_used
    )
    
    # 3. Calculate Role Match
    role_match_result = keyword_matcher.calculate_role_match(
        resume.extracted_data, request.job_description
    )

    # 4. Save scores to DB
    resume.ats_score = ats_result["score"]
    resume.role_match = role_match_result["percentage"]
    db.commit()
    
    return {
        "ats_compliance_score": ats_result["score"],
        "ats_feedback": ats_result["feedback"],
        "role_match_percentage": role_match_result["percentage"],
        "keyword_coverage": {
            "found_keywords": role_match_result["found"],
            "missing_keywords": role_match_result["missing"]
        }
    }