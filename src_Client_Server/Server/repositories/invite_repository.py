"""
Repositorio de invitaciones
"""
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .base import CRUDRepository
from ..models.invite import Invite, InviteCreate


class InviteRepository(CRUDRepository):
    """Repositorio para manejar invitaciones en SQLite"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de invitaciones"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                creator_id TEXT NOT NULL,
                max_uses INTEGER,
                uses INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_temporary BOOLEAN DEFAULT 0,
                FOREIGN KEY (server_id) REFERENCES servers(id),
                FOREIGN KEY (creator_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_invite(self, row: sqlite3.Row) -> Invite:
        """Convierte una fila a objeto Invite"""
        return Invite(
            id=row['id'],
            server_id=row['server_id'],
            code=row['code'],
            creator_id=row['creator_id'],
            max_uses=row['max_uses'],
            uses=row['uses'],
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            is_temporary=bool(row['is_temporary'])
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea una nueva invitación"""
        invite_id = str(uuid.uuid4())
        code = data['code']
        
        expires_at = None
        if data.get('expires_in'):
            expires_at = datetime.now() + timedelta(hours=data['expires_in'])
        
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            INSERT INTO invites (
                id, server_id, code, creator_id, max_uses,
                uses, expires_at, is_temporary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invite_id,
            data['server_id'],
            code,
            data['creator_id'],
            data.get('max_uses'),
            0,
            expires_at.isoformat() if expires_at else None,
            data.get('is_temporary', False)
        ))
        self.conn.commit() # type: ignore
        return invite_id
    
    def get_by_id(self, invite_id: str) -> Optional[Invite]:
        """Obtiene una invitación por ID"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM invites WHERE id = ?', (invite_id,))
        row = cursor.fetchone()
        return self._row_to_invite(row) if row else None
    
    def get_by_code(self, code: str) -> Optional[Invite]:
        """Obtiene una invitación por código"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM invites WHERE code = ?', (code,))
        row = cursor.fetchone()
        return self._row_to_invite(row) if row else None
    
    def get_by_server(self, server_id: str) -> List[Invite]:
        """Obtiene todas las invitaciones de un servidor"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM invites WHERE server_id = ?', (server_id,))
        rows = cursor.fetchall()
        return [self._row_to_invite(row) for row in rows]
    
    def get_all(self) -> List[Invite]:
        """Obtiene todas las invitaciones"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM invites')
        rows = cursor.fetchall()
        return [self._row_to_invite(row) for row in rows]
    
    def increment_uses(self, invite_id: str):
        """Incrementa el contador de usos de una invitación"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            UPDATE invites SET uses = uses + 1 WHERE id = ?
        ''', (invite_id,))
        self.conn.commit() # type: ignore
    
    def delete(self, invite_id: str) -> bool:
        """Elimina una invitación"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('DELETE FROM invites WHERE id = ?', (invite_id,))
        self.conn.commit() # type: ignore
        return cursor.rowcount > 0
    
    def delete_by_server(self, server_id: str):
        """Elimina todas las invitaciones de un servidor"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('DELETE FROM invites WHERE server_id = ?', (server_id,))
        self.conn.commit() # type: ignore

    def update(self, invite_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza una invitación"""
        cursor = self.conn.cursor() # type: ignore

        # Construir la consulta UPDATE dinámicamente
        fields = []
        values = []

        for key, value in data.items():
            if key in ['max_uses', 'expires_at', 'is_temporary']:
                fields.append(f"{key} = ?")
                if key == 'expires_at' and value:
                    values.append(value.isoformat() if isinstance(value, datetime) else value)
                else:
                    values.append(value)

        if not fields:
            return False

        values.append(invite_id)
        query = f"UPDATE invites SET {', '.join(fields)} WHERE id = ?"

        cursor.execute(query, values)
        self.conn.commit() # type: ignore
        return cursor.rowcount > 0
