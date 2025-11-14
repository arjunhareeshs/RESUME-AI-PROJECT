from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import models
from ...schemas.improvement import Improvement
from ..deps import get_db, get_current_user
from ...services.llm import improver

router = APIRouter()

@router.post("/improve_resume", response_model=List[Improvement])
async def improve_resume_endpoint(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.user.User = Depends(get_current_user),
):
    """
    Generate LLM-assisted improvements for an extracted resume.
    """
    # 1. Get resume
    resume = db.query(models.resume.Resume).filter(
        models.resume.Resume.id == resume_id,
        models.resume.Resume.user_id == current_user.id
    ).first()

    if not resume or not resume.extracted_data:
        raise HTTPException(status_code=404, detail="Extracted resume not found")

    # 2. Call LLM improver service
    suggestions = await improver.get_section_suggestions(resume.extracted_data)
    
    # 3. Save suggestions to DB
    db_improvements = []
    for s in suggestions:
        imp = models.improvement.Improvement(
            resume_id=resume_id,
            section=s["section"],
            suggestion=s["suggestion"],
            old_text=s["old_text"]
        )
        db_improvements.append(imp)
    
    db.add_all(db_improvements)
    db.commit()
    
    return db_improvements