"""
Modelos de rol y permisos
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from .enums import Permission


class Role(BaseModel):
    """Modelo de rol dentro de un servidor"""
    id: str
    server_id: str
    name: str
    color: str = "#99AAB5"
    permissions: List[str] = []
    is_default: bool = False
    position: int = 0
    mentionable: bool = False
    hoisted: bool = False

    def has_permission(self, permission: Permission) -> bool:
        """Verifica si el rol tiene un permiso específico"""
        return permission.value in self.permissions

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'server_id': self.server_id,
            'name': self.name,
            'color': self.color,
            'permissions': self.permissions,
            'is_default': self.is_default,
            'position': self.position,
            'mentionable': self.mentionable,
            'hoisted': self.hoisted
        }


class RoleCreate(BaseModel):
    """Modelo para crear rol"""
    server_id: str
    name: str
    color: str = "#99AAB5"
    permissions: List[str] = []
    is_default: bool = False
    mentionable: bool = False
    hoisted: bool = False


class RoleUpdate(BaseModel):
    """Modelo para actualizar rol"""
    name: Optional[str] = None
    color: Optional[str] = None
    permissions: Optional[List[str]] = None
    mentionable: Optional[bool] = None
    hoisted: Optional[bool] = None
    position: Optional[int] = None
