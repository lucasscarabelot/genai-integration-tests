from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str
    is_confidential: bool = False

class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    is_confidential: bool
    owner_id: int
    created_at: datetime

class AuditLogEntry(BaseModel):
    id: int
    timestamp: datetime
    username: str
    endpoint: str
    method: str
    status_code: int
