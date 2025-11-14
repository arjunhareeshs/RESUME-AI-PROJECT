from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from ... import models, schemas
from ..deps import get_db
from ...utils.auth import get_password_hash
from ...utils import file_handler

router = APIRouter()

@router.post("/upload_resume")
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a resume file (.pdf, .docx, .png, .jpg), save it,
    and create a database record.
    """
    # 1. Validate file type
    allowed_types = [
        "application/pdf", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # 2. Resolve user (temporary auth bypass: use or create a guest user)
    guest = db.query(models.user.User).filter(models.user.User.email == "guest@local").first()
    if not guest:
        guest = models.user.User(
            email="guest@local",
            name="Guest",
            password_hash=get_password_hash("guest")
        )
        db.add(guest)
        db.commit()
        db.refresh(guest)

    # 3. Save the file (e.g., to S3 or local storage)
    file_path = await file_handler.save_upload_file(file, guest.id)
    
    # 4. Create resume record in DB
    new_resume = models.resume.Resume(
        user_id=guest.id,
        file_path=str(file_path),
        file_type=file.content_type
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    return {"resume_id": new_resume.id, "file_path": file_path}