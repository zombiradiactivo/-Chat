"""
Repositorio de transferencia de archivos
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import CRUDRepository
from ..models.file_transfer import FileTransfer, FileTransferCreate


class FileTransferRepository(CRUDRepository):
    """Repositorio para manejar transferencias de archivos"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de transferencias"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_transfers (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                encrypted BOOLEAN DEFAULT 0,
                chunk_size INTEGER DEFAULT 8192,
                total_chunks INTEGER NOT NULL,
                uploaded_chunks INTEGER DEFAULT 0,
                download_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_transfer(self, row: sqlite3.Row) -> FileTransfer:
        """Convierte una fila a objeto FileTransfer"""
        return FileTransfer(
            id=row['id'],
            channel_id=row['channel_id'],
            sender_id=row['sender_id'],
            filename=row['filename'],
            file_size=row['file_size'],
            file_type=row['file_type'],
            file_hash=row['file_hash'],
            encrypted=bool(row['encrypted']),
            chunk_size=row['chunk_size'],
            total_chunks=row['total_chunks'],
            uploaded_chunks=row['uploaded_chunks'],
            download_url=row['download_url'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea una nueva transferencia"""
        transfer_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('''
            INSERT INTO file_transfers (
                id, channel_id, sender_id, filename, file_size,
                file_type, file_hash, encrypted, chunk_size,
                total_chunks, uploaded_chunks, download_url, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transfer_id,
            data['channel_id'],
            data['sender_id'],
            data['filename'],
            data['file_size'],
            data['file_type'],
            data['file_hash'],
            data.get('encrypted', False),
            data.get('chunk_size', 8192),
            data['total_chunks'],
            0,
            data.get('download_url'),
            data.get('expires_at')
        ))
        self.conn.commit()# type: ignore
        return transfer_id
    
    def get_by_id(self, transfer_id: str) -> Optional[FileTransfer]:
        """Obtiene una transferencia por ID"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM file_transfers WHERE id = ?', (transfer_id,))
        row = cursor.fetchone()
        return self._row_to_transfer(row) if row else None
    
    def get_by_channel(self, channel_id: str) -> List[FileTransfer]:
        """Obtiene todas las transferencias de un canal"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM file_transfers WHERE channel_id = ?', (channel_id,))
        rows = cursor.fetchall()
        return [self._row_to_transfer(row) for row in rows]
    
    def get_by_sender(self, sender_id: str) -> List[FileTransfer]:
        """Obtiene todas las transferencias de un remitente"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM file_transfers WHERE sender_id = ?', (sender_id,))
        rows = cursor.fetchall()
        return [self._row_to_transfer(row) for row in rows]
    
    def get_all(self) -> List[FileTransfer]:
        """Obtiene todas las transferencias"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM file_transfers')
        rows = cursor.fetchall()
        return [self._row_to_transfer(row) for row in rows]
    
    def update_chunks(self, transfer_id: str, uploaded_chunks: int):
        """Actualiza el número de chunks subidos"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('''
            UPDATE file_transfers SET uploaded_chunks = ? WHERE id = ?
        ''', (uploaded_chunks, transfer_id))
        self.conn.commit()# type: ignore
    
    def set_download_url(self, transfer_id: str, download_url: str):
        """Establece la URL de descarga"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('''
            UPDATE file_transfers SET download_url = ? WHERE id = ?
        ''', (download_url, transfer_id))
        self.conn.commit()# type: ignore
    
    def delete(self, transfer_id: str) -> bool:
        """Elimina una transferencia"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('DELETE FROM file_transfers WHERE id = ?', (transfer_id,))
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def cleanup_expired(self):
        """Elimina transferencias expiradas"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            DELETE FROM file_transfers
            WHERE expires_at IS NOT NULL AND expires_at < ?
        ''', (datetime.now().isoformat(),))
        self.conn.commit()# type: ignore

    def update(self, transfer_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza una transferencia"""
        cursor = self.conn.cursor() # type: ignore

        # Construir la consulta UPDATE dinámicamente
        fields = []
        values = []

        for key, value in data.items():
            if key in ['uploaded_chunks', 'download_url', 'expires_at', 'file_hash']:
                fields.append(f"{key} = ?")
                if key == 'expires_at' and value:
                    values.append(value.isoformat() if isinstance(value, datetime) else value)
                else:
                    values.append(value)

        if not fields:
            return False

        values.append(transfer_id)
        query = f"UPDATE file_transfers SET {', '.join(fields)} WHERE id = ?"

        cursor.execute(query, values)
        self.conn.commit() # type: ignore
        return cursor.rowcount > 0
