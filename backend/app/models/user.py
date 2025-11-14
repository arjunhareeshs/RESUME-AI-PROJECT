from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    github_link = Column(String(255), nullable=True)
    leetcode_link = Column(String(255), nullable=True)
    
    github_stats = Column(JSONB, nullable=True)
    leetcode_stats = Column(JSONB, nullable=True)