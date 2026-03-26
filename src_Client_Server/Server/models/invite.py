"""
Modelos de invitación
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class Invite(BaseModel):
    """Modelo para invitación a servidor"""
    id: str
    server_id: str
    code: str
    creator_id: str
    max_uses: Optional[int] = None
    uses: int = 0
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    is_temporary: bool = False

    def is_valid(self) -> bool:
        """Verifica si la invitación es válida"""
        if self.uses >= (self.max_uses or float('inf')):
            return False
        if self.expires_at and self.expires_at < datetime.now():
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'server_id': self.server_id,
            'code': self.code,
            'creator_id': self.creator_id,
            'max_uses': self.max_uses,
            'uses': self.uses,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'is_temporary': self.is_temporary
        }


class InviteCreate(BaseModel):
    """Modelo para crear invitación"""
    server_id: str
    creator_id: str
    max_uses: Optional[int] = None
    expires_in: Optional[int] = None  # horas hasta expirar
    is_temporary: bool = False
