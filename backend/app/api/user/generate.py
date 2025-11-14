from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import models, schemas
from ..deps import get_db, get_current_user
from ...services.llm import generator

router = APIRouter()

@router.post("/generate_resume", response_model=schemas.resume.Resume)
async def generate_resume_endpoint(
    request: schemas.resume.ResumeGenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.user.User = Depends(get_current_user),
):
    """
    Generate a new resume using the LLM and save it to the database.
    """
    # 1. Call LLM service to generate resume text
    resume_text, extracted_data = await generator.generate_resume_from_data(request)
    
    # 2. Save the new resume to the DB
    new_resume = models.resume.Resume(
        user_id=current_user.id,
        file_type='generated',
        extracted_data=extracted_data, # Store the structured data that *generated* it
        # You might also want to save the raw 'resume_text' somewhere
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    return new_resume