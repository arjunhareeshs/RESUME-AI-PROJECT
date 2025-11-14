from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ... import models, schemas
from ..deps import get_db, get_current_user

router = APIRouter()

@router.get("/get_user_resumes", response_model=List[schemas.resume.Resume])
async def get_user_resumes_endpoint(
    db: Session = Depends(get_db),
    current_user: models.user.User = Depends(get_current_user),
):
    """
    Get all resumes for the currently authenticated user.
    """
    resumes = db.query(models.resume.Resume).filter(
        models.resume.Resume.user_id == current_user.id
    ).order_by(models.resume.Resume.created_at.desc()).all()
    
    return resumes