from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ... import models, schemas
from ..deps import get_db, get_current_user
from ...services.extraction import pdf_extractor, docx_extractor, image_extractor, layout_detector

router = APIRouter()

@router.post("/extract_resume", response_model=schemas.resume.Resume)
async def extract_resume_endpoint(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.user.User = Depends(get_current_user),
):
    """
    Trigger the extraction pipeline for a previously uploaded resume.
    """
    # 1. Get the resume from DB
    resume = db.query(models.resume.Resume).filter(
        models.resume.Resume.id == resume_id,
        models.resume.Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if not resume.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot extract from generated resume")

    # 2. Route to correct extractor
    blocks = []
    if resume.file_type == "application/pdf":
        # This now uses your advanced pdf_extractor
        blocks = pdf_extractor.extract(resume.file_path)
    elif resume.file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        blocks = docx_extractor.extract(resume.file_path)
    elif resume.file_type in ["image/jpeg", "image/png"]:
        blocks = await image_extractor.extract(resume.file_path)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type for extraction")

    # 3. Detect layout
    layout_data = layout_detector.detect_layout(blocks)
    
    # 4. Parse sections based on layout
    # This is complex. You'll build a parser here.
    extracted_data = {"sections": "...", "metadata": "...", "layout": layout_data}
    font_stats = {"fonts": ["Arial"], "sizes": [10, 12]} # You'll get this from the blocks
    bullet_used = True

    # 5. Save results to DB
    resume.extracted_data = extracted_data
    resume.font_stats = font_stats
    resume.bullet_used = bullet_used
    db.commit()
    db.refresh(resume)
    
    return resume