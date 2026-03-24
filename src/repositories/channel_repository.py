"""
Repositorio de canales
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from .base import CRUDRepository
from ..models.channel import Channel, ChannelCreate, ChannelUpdate
from ..models.enums import ChannelType


class ChannelRepository(CRUDRepository):
    """Repositorio para manejar canales en SQLite"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de canales"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                topic TEXT,
                server_id TEXT NOT NULL,
                position INTEGER DEFAULT 0,
                is_private BOOLEAN DEFAULT 0,
                allowed_roles TEXT DEFAULT '[]',
                parent_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_at TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_channel(self, row: sqlite3.Row) -> Channel:
        """Convierte una fila a objeto Channel"""
        # Convertir explícitamente a enum
        if isinstance(row['type'], str):
            channel_type = ChannelType(row['type'])
        else:
            channel_type = row['type']
        
        return Channel(
            id=row['id'],
            name=row['name'],
            type=channel_type,
            topic=row['topic'],
            server_id=row['server_id'],
            position=row['position'],
            is_private=bool(row['is_private']),
            allowed_roles=json.loads(row['allowed_roles']) if row['allowed_roles'] else [],
            parent_id=row['parent_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            last_message_at=datetime.fromisoformat(row['last_message_at']) if row['last_message_at'] else None,
            message_count=row['message_count']
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea un nuevo canal"""
        channel_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('''
            INSERT INTO channels (
                id, name, type, topic, server_id,
                position, is_private, allowed_roles, parent_id,
                created_at, last_message_at, message_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            channel_id,
            data['name'],
            data['type'].value,
            data.get('topic'),
            data['server_id'],
            data.get('position', 0),
            data.get('is_private', False),
            json.dumps(data.get('allowed_roles', [])),
            data.get('parent_id'),
            datetime.now().isoformat(),
            None,
            0
        ))
        self.conn.commit()# type: ignore
        return channel_id
    
    def get_by_id(self, channel_id: str) -> Optional[Channel]:
        """Obtiene un canal por ID"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM channels WHERE id = ?', (channel_id,))
        row = cursor.fetchone()
        return self._row_to_channel(row) if row else None
    
    def get_by_server(self, server_id: str) -> List[Channel]:
        """Obtiene todos los canales de un servidor"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM channels WHERE server_id = ? ORDER BY position', (server_id,))
        rows = cursor.fetchall()
        return [self._row_to_channel(row) for row in rows]
    
    def get_all(self) -> List[Channel]:
        """Obtiene todos los canales"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM channels')
        rows = cursor.fetchall()
        return [self._row_to_channel(row) for row in rows]
    
    def update(self, channel_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un canal"""
        fields = []
        values = []
        for key, value in data.items():
            if key not in ['id', 'created_at']:
                if key == 'type':
                    value = value.value
                elif key == 'allowed_roles':
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(channel_id)
        
        cursor = self.conn.cursor() # type: ignore
        cursor.execute(f'''
            UPDATE channels SET {', '.join(fields)} WHERE id = ?
        ''', values)
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def delete(self, channel_id: str) -> bool:
        """Elimina un canal"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('DELETE FROM channels WHERE id = ?', (channel_id,))
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def update_message_count(self, channel_id: str, increment: int = 1):
        """Actualiza el contador de mensajes"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            UPDATE channels SET message_count = message_count + ? WHERE id = ?
        ''', (increment, channel_id))
        self.conn.commit()# type: ignore
    
    def update_last_message(self, channel_id: str):
        """Actualiza el último mensaje del canal"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            UPDATE channels SET last_message_at = ? WHERE id = ?
        ''', (datetime.now().isoformat(), channel_id))
        self.conn.commit()# type: ignore
