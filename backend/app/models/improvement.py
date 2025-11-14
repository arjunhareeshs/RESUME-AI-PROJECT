from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.sql.expression import text
from ..database import Base

class Improvement(Base):
    __tablename__ = "improvements"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    
    section = Column(String(100), nullable=False)
    old_text = Column(Text, nullable=True)
    new_text = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))