"""
Modelos de usuario
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, validator

from .enums import UserStatus


class UserBase(BaseModel):
    """Modelo base para usuario"""
    username: str
    email: EmailStr
    discriminator: str = "0000"

    @validator('username')
    def username_must_be_valid(cls, v):
        if len(v) < 2 or len(v) > 32:
            raise ValueError('Username debe tener entre 2 y 32 caracteres')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username solo puede contener letras, números, guiones y guiones bajos')
        return v


class UserCreate(UserBase):
    """Modelo para crear usuario"""
    password: str

    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password debe tener al menos 8 caracteres')
        return v


class User(UserBase):
    """Modelo completo de usuario"""
    id: str
    profile_picture: Optional[str] = None
    banner: Optional[str] = None
    description: Optional[str] = None
    status: UserStatus = UserStatus.OFFLINE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    last_seen: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'discriminator': self.discriminator,
            'profile_picture': self.profile_picture,
            'banner': self.banner,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }


class UserUpdate(BaseModel):
    """Modelo para actualizar usuario"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_picture: Optional[str] = None
    banner: Optional[str] = None
    description: Optional[str] = None
