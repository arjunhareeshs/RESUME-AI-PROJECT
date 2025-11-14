from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import text
from ..database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    file_path = Column(String(512), nullable=True) # Path in S3/local storage
    file_type = Column(String(50), nullable=False) # 'pdf', 'docx', 'generated'
    
    extracted_data = Column(JSONB, nullable=True)
    ats_score = Column(Integer, default=0)
    role_match = Column(Integer, default=0)
    font_stats = Column(JSONB, nullable=True)
    bullet_used = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))