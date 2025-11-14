from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List

from ... import models, schemas
from ..deps import get_db, get_current_admin_user

router = APIRouter()

@router.get("/top_resumes", response_model=List[schemas.resume.Resume])
async def get_top_resumes_endpoint(
    n: int = Query(10, gt=0, le=100),
    db: Session = Depends(get_db),
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Get top N resumes, ranked by a combined score.
    """
    # Define the combined score (ats_score + role_match)
    combined_score = (models.resume.Resume.ats_score + models.resume.Resume.role_match).label("combined_score")
    
    top_resumes = db.query(models.resume.Resume).order_by(
        combined_score.desc()
    ).limit(n).all()
    
    return top_resumes