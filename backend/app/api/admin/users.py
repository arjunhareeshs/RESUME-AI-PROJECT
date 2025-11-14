from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import models, schemas
from ..deps import get_db, get_current_admin_user

router = APIRouter()

@router.get("/users", response_model=List[schemas.user.User])
async def get_all_users_endpoint(
    db: Session = Depends(get_db),
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Get a list of all users.
    """
    users = db.query(models.user.User).all()
    return users

@router.get("/user/{user_id}")
async def get_user_details_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Get detailed info for one user, including their resumes.
    """
    user = db.query(models.user.User).filter(models.user.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    resumes = db.query(models.resume.Resume).filter(
        models.resume.Resume.user_id == user_id
    ).all()
    
    return {"user_info": user, "resumes": resumes}