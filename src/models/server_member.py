"""
Modelos de miembro de servidor
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from .enums import Permission
from .role import Role


class ServerMember(BaseModel):
    """Modelo para miembro de servidor"""
    user_id: str
    server_id: str
    role_ids: List[str] = []
    joined_at: datetime = field(default_factory=datetime.now)
    nickname: Optional[str] = None
    is_muted: bool = False
    is_deafened: bool = False
    is_baned: bool = False
    ban_reason: Optional[str] = None
    timeout_until: Optional[datetime] = None

    def has_role(self, role_id: str) -> bool:
        """Verifica si el miembro tiene un rol específico"""
        return role_id in self.role_ids

    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Verifica si el miembro tiene un permiso a través de sus roles"""
        if role.id in self.role_ids:
            return role.has_permission(permission)
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'server_id': self.server_id,
            'role_ids': self.role_ids,
            'joined_at': self.joined_at.isoformat(),
            'nickname': self.nickname,
            'is_muted': self.is_muted,
            'is_deafened': self.is_deafened,
            'is_baned': self.is_baned,
            'ban_reason': self.ban_reason,
            'timeout_until': self.timeout_until.isoformat() if self.timeout_until else None
        }


class ServerMemberUpdate(BaseModel):
    """Modelo para actualizar miembro de servidor"""
    nickname: Optional[str] = None
    role_ids: Optional[List[str]] = None
    is_muted: Optional[bool] = None
    is_deafened: Optional[bool] = None
    is_baned: Optional[bool] = None
    ban_reason: Optional[str] = None
    timeout_until: Optional[datetime] = None
