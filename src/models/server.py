"""
Modelos de servidor
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator

from .enums import ConnectionType, SecurityLevel


class ServerBase(BaseModel):
    """Modelo base para servidor"""
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None

    @validator('name')
    def name_must_be_valid(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('El nombre debe tener entre 1 y 100 caracteres')
        return v


class ServerCreate(ServerBase):
    """Modelo para crear servidor"""
    connection_type: ConnectionType = ConnectionType.CLIENT_SERVER
    security_level: SecurityLevel = SecurityLevel.BASIC
    max_members: int = 100
    allow_file_transfer: bool = True
    allow_video_streaming: bool = True
    require_verification: bool = False


class Server(ServerBase):
    """Modelo completo de servidor"""
    id: str
    owner_id: str
    connection_type: ConnectionType
    security_level: SecurityLevel
    max_members: int
    allow_file_transfer: bool
    allow_video_streaming: bool
    require_verification: bool
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    member_count: int = 0
    channels: List[str] = []
    roles: List[str] = []
    invites: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'owner_id': self.owner_id,
            'connection_type': self.connection_type.value,
            'security_level': self.security_level.value,
            'max_members': self.max_members,
            'allow_file_transfer': self.allow_file_transfer,
            'allow_video_streaming': self.allow_video_streaming,
            'require_verification': self.require_verification,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'member_count': self.member_count,
            'channels': self.channels,
            'roles': self.roles,
            'invites': self.invites
        }


class ServerUpdate(BaseModel):
    """Modelo para actualizar servidor"""
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    connection_type: Optional[ConnectionType] = None
    security_level: Optional[SecurityLevel] = None
    max_members: Optional[int] = None
    allow_file_transfer: Optional[bool] = None
    allow_video_streaming: Optional[bool] = None
    require_verification: Optional[bool] = None
