from pathlib import Path
from fastapi import UploadFile
import aiofiles
import uuid

# Define a base upload directory (make this configurable)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def save_upload_file(file: UploadFile, user_id: int) -> Path:
    """
    Saves an uploaded file to a user-specific directory.
    In production, this should upload to S3.
    """
    # Create a unique filename to avoid conflicts
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Create user-specific dir
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    
    file_path = user_dir / unique_filename
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await out_file.write(content)
    except Exception as e:
        # Handle write error
        raise e
        
    return file_path