from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Dict, Any

class UserBase(BaseModel):
    email: EmailStr
    name: str
    github_link: Optional[str] = None
    leetcode_link: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    github_stats: Optional[Dict[str, Any]] = None
    leetcode_stats: Optional[Dict[str, Any]] = None
    
    # Pydantic v2 configuration
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None