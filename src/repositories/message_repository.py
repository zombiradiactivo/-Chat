"""
Repositorio de mensajes
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from .base import CRUDRepository
from ..models.message import Message, MessageCreate, MessageUpdate
from ..models.enums import MessageType


class MessageRepository(CRUDRepository):
    """Repositorio para manejar mensajes en SQLite"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de mensajes"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                message_type TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                author_id TEXT NOT NULL,
                reply_to TEXT,
                mentions TEXT DEFAULT '[]',
                attachments TEXT DEFAULT '[]',
                edited BOOLEAN DEFAULT 0,
                edited_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reactions TEXT DEFAULT '{}',
                pinned BOOLEAN DEFAULT 0,
                pinned_at TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id),
                FOREIGN KEY (author_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convierte una fila a objeto Message"""
        return Message(
            id=row['id'],
            content=row['content'],
            message_type=MessageType(row['message_type']),
            channel_id=row['channel_id'],
            author_id=row['author_id'],
            reply_to=row['reply_to'],
            mentions=json.loads(row['mentions']) if row['mentions'] else [],
            attachments=json.loads(row['attachments']) if row['attachments'] else [],
            edited=bool(row['edited']),
            edited_at=datetime.fromisoformat(row['edited_at']) if row['edited_at'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            reactions=json.loads(row['reactions']) if row['reactions'] else {},
            pinned=bool(row['pinned']),
            pinned_at=datetime.fromisoformat(row['pinned_at']) if row['pinned_at'] else None
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea un nuevo mensaje"""
        message_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            INSERT INTO messages (
                id, content, message_type, channel_id, author_id,
                reply_to, mentions, attachments, edited, edited_at,
                created_at, reactions, pinned, pinned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_id,
            data['content'],
            data['message_type'].value,
            data['channel_id'],
            data['author_id'],
            data.get('reply_to'),
            json.dumps(data.get('mentions', [])),
            json.dumps(data.get('attachments', [])),
            0,
            None,
            datetime.now().isoformat(),
            json.dumps({}),
            0,
            None
        ))
        self.conn.commit()# pyright: ignore[reportOptionalMemberAccess]
        return message_id
    
    def get_by_id(self, message_id: str) -> Optional[Message]:
        """Obtiene un mensaje por ID"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
        row = cursor.fetchone()
        return self._row_to_message(row) if row else None
    
    def get_by_channel(self, channel_id: str, limit: int = 50, before: Optional[str] = None) -> List[Message]:
        """Obtiene mensajes de un canal"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        if before:
            cursor.execute('''
                SELECT * FROM messages 
                WHERE channel_id = ? AND created_at < (
                    SELECT created_at FROM messages WHERE id = ?
                )
                ORDER BY created_at DESC LIMIT ?
            ''', (channel_id, before, limit))
        else:
            cursor.execute('''
                SELECT * FROM messages 
                WHERE channel_id = ? 
                ORDER BY created_at DESC LIMIT ?
            ''', (channel_id, limit))
        
        rows = cursor.fetchall()
        messages = [self._row_to_message(row) for row in rows]
        messages.reverse()  # Ordenar de más antiguo a más reciente
        return messages
    
    def get_all(self) -> List[Message]:
        """Obtiene todos los mensajes"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM messages ORDER BY created_at DESC LIMIT 1000')
        rows = cursor.fetchall()
        return [self._row_to_message(row) for row in rows]
    
    def update(self, message_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un mensaje"""
        fields = []
        values = []
        for key, value in data.items():
            if key not in ['id', 'created_at']:
                if key == 'message_type':
                    value = value.value
                elif key in ['mentions', 'attachments', 'reactions']:
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        if 'edited' not in data:
            fields.append('edited = ?')
            values.append(1)
        if 'edited_at' not in data:
            fields.append('edited_at = ?')
            values.append(datetime.now().isoformat())
        
        values.append(message_id)
        
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        cursor.execute(f'''
            UPDATE messages SET {', '.join(fields)} WHERE id = ?
        ''', values)
        self.conn.commit()# pyright: ignore[reportOptionalMemberAccess]
        return cursor.rowcount > 0
    
    def delete(self, message_id: str) -> bool:
        """Elimina un mensaje"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
        self.conn.commit()# pyright: ignore[reportOptionalMemberAccess]
        return cursor.rowcount > 0
    
    def add_reaction(self, message_id: str, emoji: str, user_id: str):
        """Añade una reacción a un mensaje"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT reactions FROM messages WHERE id = ?', (message_id,))
        row = cursor.fetchone()
        if row:
            reactions = json.loads(row['reactions']) if row['reactions'] else {}
            if emoji not in reactions:
                reactions[emoji] = []
            if user_id not in reactions[emoji]:
                reactions[emoji].append(user_id)
            cursor.execute('''
                UPDATE messages SET reactions = ? WHERE id = ?
            ''', (json.dumps(reactions), message_id))
            self.conn.commit()# pyright: ignore[reportOptionalMemberAccess]
    
    def remove_reaction(self, message_id: str, emoji: str, user_id: str):
        """Elimina una reacción de un mensaje"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT reactions FROM messages WHERE id = ?', (message_id,))
        row = cursor.fetchone()
        if row:
            reactions = json.loads(row['reactions']) if row['reactions'] else {}
            if emoji in reactions and user_id in reactions[emoji]:
                reactions[emoji].remove(user_id)
                if not reactions[emoji]:
                    del reactions[emoji]
                cursor.execute('''
                    UPDATE messages SET reactions = ? WHERE id = ?
                ''', (json.dumps(reactions), message_id))
                self.conn.commit()# pyright: ignore[reportOptionalMemberAccess]
    
    def pin_message(self, message_id: str, pin: bool = True):
        """Fija/desfija un mensaje"""
        cursor = self.conn.cursor()# pyright: ignore[reportOptionalMemberAccess]
        if pin:
            cursor.execute('''
                UPDATE messages SET pinned = 1, pinned_at = ? WHERE id = ?
            ''', (datetime.now().isoformat(), message_id))
        else:
            cursor.execute('''
                UPDATE messages SET pinned = 0, pinned_at = NULL WHERE id = ?
            ''', (message_id,))
        self.conn.commit()# pyright: ignore[reportOptionalMemberAccess]
