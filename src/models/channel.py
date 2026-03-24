"""
Modelos de canal
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator

from .enums import ChannelType


class ChannelBase(BaseModel):
    """Modelo base para canal"""
    name: str
    type: ChannelType
    topic: Optional[str] = None

    class Config:
        use_enum_values = False  # Mantener enums como enums, no convertir a strings

    @validator('name')
    def name_must_be_valid(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('El nombre debe tener entre 1 y 100 caracteres')
        if not all(c.isalnum() or c in '- _' for c in v):
            raise ValueError('Nombre inválido')
        return v


class ChannelCreate(ChannelBase):
    """Modelo para crear canal"""
    server_id: str
    position: int = 0
    is_private: bool = False
    allowed_roles: List[str] = []
    parent_id: Optional[str] = None


class Channel(ChannelBase):
    """Modelo completo de canal"""
    id: str
    server_id: str
    position: int
    is_private: bool
    allowed_roles: List[str]
    parent_id: Optional[str]
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: Optional[datetime] = None
    message_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'topic': self.topic,
            'server_id': self.server_id,
            'position': self.position,
            'is_private': self.is_private,
            'allowed_roles': self.allowed_roles,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat(),
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'message_count': self.message_count
        }


class ChannelUpdate(BaseModel):
    """Modelo para actualizar canal"""
    name: Optional[str] = None
    topic: Optional[str] = None
    position: Optional[int] = None
    is_private: Optional[bool] = None
    allowed_roles: Optional[List[str]] = None
    parent_id: Optional[str] = None
