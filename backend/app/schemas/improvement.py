from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class Improvement(BaseModel):
    id: int
    resume_id: int
    section: str
    suggestion: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)