"""
Repositorio de miembros de servidor
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from .base import CRUDRepository
from ..models.server_member import ServerMember, ServerMemberUpdate


class ServerMemberRepository(CRUDRepository):
    """Repositorio para manejar miembros de servidor"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de miembros de servidor"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_members (
                user_id TEXT NOT NULL,
                server_id TEXT NOT NULL,
                role_ids TEXT DEFAULT '[]',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                nickname TEXT,
                is_muted BOOLEAN DEFAULT 0,
                is_deafened BOOLEAN DEFAULT 0,
                is_baned BOOLEAN DEFAULT 0,
                ban_reason TEXT,
                timeout_until TIMESTAMP,
                PRIMARY KEY (user_id, server_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        ''')
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_member(self, row: sqlite3.Row) -> ServerMember:
        """Convierte una fila a objeto ServerMember"""
        return ServerMember(
            user_id=row['user_id'],
            server_id=row['server_id'],
            role_ids=json.loads(row['role_ids']) if row['role_ids'] else [],
            joined_at=datetime.fromisoformat(row['joined_at']) if row['joined_at'] else datetime.now(),
            nickname=row['nickname'],
            is_muted=bool(row['is_muted']),
            is_deafened=bool(row['is_deafened']),
            is_baned=bool(row['is_baned']),
            ban_reason=row['ban_reason'],
            timeout_until=datetime.fromisoformat(row['timeout_until']) if row['timeout_until'] else None
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Añade un miembro a un servidor"""
        member_id = f"{data['user_id']}_{data['server_id']}"
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            INSERT INTO server_members (
                user_id, server_id, role_ids, joined_at,
                nickname, is_muted, is_deafened, is_baned, ban_reason, timeout_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['user_id'],
            data['server_id'],
            json.dumps(data.get('role_ids', [])),
            datetime.now().isoformat(),
            data.get('nickname'),
            data.get('is_muted', False),
            data.get('is_deafened', False),
            data.get('is_baned', False),
            data.get('ban_reason'),
            data.get('timeout_until')
        ))
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
        return member_id
    
    def get_by_id(self, user_id: str, server_id: str) -> Optional[ServerMember]:
        """Obtiene un miembro por IDs de usuario y servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            SELECT * FROM server_members 
            WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        row = cursor.fetchone()
        return self._row_to_member(row) if row else None
    
    def get_by_user(self, user_id: str) -> List[ServerMember]:
        """Obtiene todos los servidores donde un usuario es miembro"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM server_members WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        return [self._row_to_member(row) for row in rows]
    
    def get_by_server(self, server_id: str, include_banned: bool = False) -> List[ServerMember]:
        """Obtiene todos los miembros de un servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        if include_banned:
            cursor.execute('SELECT * FROM server_members WHERE server_id = ?', (server_id,))
        else:
            cursor.execute('SELECT * FROM server_members WHERE server_id = ? AND is_baned = 0', (server_id,))
        rows = cursor.fetchall()
        return [self._row_to_member(row) for row in rows]
    
    def get_all(self) -> List[ServerMember]:
        """Obtiene todos los miembros"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM server_members')
        rows = cursor.fetchall()
        return [self._row_to_member(row) for row in rows]
    
    def update(self, user_id: str, server_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un miembro"""
        fields = []
        values = []
        for key, value in data.items():
            if key not in ['user_id', 'server_id']:
                if key == 'role_ids':
                    value = json.dumps(value)
                elif key == 'timeout_until' and value:
                    value = value.isoformat()
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(user_id)
        values.append(server_id)
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute(f'''
            UPDATE server_members SET {', '.join(fields)}
            WHERE user_id = ? AND server_id = ?
        ''', values)
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
        return cursor.rowcount > 0
    
    def delete(self, user_id: str, server_id: str) -> bool:
        """Elimina un miembro de un servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            DELETE FROM server_members WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
        return cursor.rowcount > 0
    
    def is_member(self, user_id: str, server_id: str) -> bool:
        """Verifica si un usuario es miembro de un servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            SELECT 1 FROM server_members 
            WHERE user_id = ? AND server_id = ? AND is_baned = 0
        ''', (user_id, server_id))
        return cursor.fetchone() is not None
    
    def is_baned(self, user_id: str, server_id: str) -> bool:
        """Verifica si un usuario está baneado de un servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            SELECT is_baned FROM server_members 
            WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        row = cursor.fetchone()
        return row and bool(row['is_baned'])
