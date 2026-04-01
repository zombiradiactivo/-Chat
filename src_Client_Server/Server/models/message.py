"""
Modelos de mensaje
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator

from .enums import MessageType


class MessageBase(BaseModel):
    """Modelo base para mensaje"""
    content: str
    message_type: MessageType = MessageType.TEXT

    @validator('content')
    def content_must_have_text(cls, v):
        if not v or not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return v.strip()


class MessageCreate(MessageBase):
    """Modelo para crear mensaje"""
    channel_id: str
    author_id: str
    reply_to: Optional[str] = None
    mentions: List[str] = []
    attachments: List[Dict[str, Any]] = []


class Message(MessageBase):
    """Modelo completo de mensaje"""
    id: str
    channel_id: str
    author_id: str
    reply_to: Optional[str]
    mentions: List[str]
    attachments: List[Dict[str, Any]] = []
    edited: bool = False
    edited_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    reactions: Dict[str, List[str]] = {}
    pinned: bool = False
    pinned_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'message_type': self.message_type.value,
            'channel_id': self.channel_id,
            'author_id': self.author_id,
            'reply_to': self.reply_to,
            'mentions': self.mentions,
            'attachments': self.attachments,
            'edited': self.edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'created_at': self.created_at.isoformat(),
            'reactions': self.reactions,
            'pinned': self.pinned,
            'pinned_at': self.pinned_at.isoformat() if self.pinned_at else None
        }


class MessageUpdate(BaseModel):
    """Modelo para actualizar mensaje"""
    content: Optional[str] = None
