"""
Modelos de transferencia de archivos
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class FileTransfer(BaseModel):
    """Modelo para transferencia de archivos"""
    id: str
    channel_id: str
    sender_id: str
    filename: str
    file_size: int  # en bytes
    file_type: str  # MIME type
    file_hash: str  # SHA-256 para verificar integridad
    encrypted: bool = False
    chunk_size: int = 8192
    total_chunks: int
    uploaded_chunks: int = 0
    download_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'sender_id': self.sender_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'file_hash': self.file_hash,
            'encrypted': self.encrypted,
            'chunk_size': self.chunk_size,
            'total_chunks': self.total_chunks,
            'uploaded_chunks': self.uploaded_chunks,
            'download_url': self.download_url,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class FileTransferCreate(BaseModel):
    """Modelo para crear transferencia de archivo"""
    channel_id: str
    sender_id: str
    filename: str
    file_size: int
    file_type: str
    file_hash: str
    encrypted: bool = False
    chunk_size: int = 8192
