"""
Repositorio de roles
"""
import sqlite3
import uuid
from typing import List, Optional, Dict, Any
import json

from .base import CRUDRepository
from ..models.role import Role, RoleCreate, RoleUpdate


class RoleRepository(CRUDRepository):
    """Repositorio para manejar roles en SQLite"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de roles"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#99AAB5',
                permissions TEXT DEFAULT '[]',
                is_default BOOLEAN DEFAULT 0,
                position INTEGER DEFAULT 0,
                mentionable BOOLEAN DEFAULT 0,
                hoisted BOOLEAN DEFAULT 0,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        ''')
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_role(self, row: sqlite3.Row) -> Role:
        """Convierte una fila a objeto Role"""
        return Role(
            id=row['id'],
            server_id=row['server_id'],
            name=row['name'],
            color=row['color'],
            permissions=json.loads(row['permissions']) if row['permissions'] else [],
            is_default=bool(row['is_default']),
            position=row['position'],
            mentionable=bool(row['mentionable']),
            hoisted=bool(row['hoisted'])
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea un nuevo rol"""
        role_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('''
            INSERT INTO roles (
                id, server_id, name, color, permissions,
                is_default, position, mentionable, hoisted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            role_id,
            data['server_id'],
            data['name'],
            data.get('color', '#99AAB5'),
            json.dumps(data.get('permissions', [])),
            data.get('is_default', False),
            data.get('position', 0),
            data.get('mentionable', False),
            data.get('hoisted', False)
        ))
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
        return role_id
    
    def get_by_id(self, role_id: str) -> Optional[Role]:
        """Obtiene un rol por ID"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM roles WHERE id = ?', (role_id,))
        row = cursor.fetchone()
        return self._row_to_role(row) if row else None
    
    def get_by_server(self, server_id: str) -> List[Role]:
        """Obtiene todos los roles de un servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM roles WHERE server_id = ? ORDER BY position', (server_id,))
        rows = cursor.fetchall()
        return [self._row_to_role(row) for row in rows]
    
    def get_default_role(self, server_id: str) -> Optional[Role]:
        """Obtiene el rol por defecto (@everyone) de un servidor"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM roles WHERE server_id = ? AND is_default = 1', (server_id,))
        row = cursor.fetchone()
        return self._row_to_role(row) if row else None
    
    def get_all(self) -> List[Role]:
        """Obtiene todos los roles"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('SELECT * FROM roles')
        rows = cursor.fetchall()
        return [self._row_to_role(row) for row in rows]
    
    def update(self, role_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un rol"""
        fields = []
        values = []
        for key, value in data.items():
            if key not in ['id']:
                if key == 'permissions':
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(role_id)
        
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute(f'''
            UPDATE roles SET {', '.join(fields)} WHERE id = ?
        ''', values)
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
        return cursor.rowcount > 0
    
    def delete(self, role_id: str) -> bool:
        """Elimina un rol"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        cursor.execute('DELETE FROM roles WHERE id = ?', (role_id,))
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
        return cursor.rowcount > 0
    
    def reorder_roles(self, server_id: str, role_positions: Dict[str, int]):
        """Reordena los roles por posición"""
        cursor = self.conn.cursor() # pyright: ignore[reportOptionalMemberAccess]
        for role_id, position in role_positions.items():
            cursor.execute('''
                UPDATE roles SET position = ? WHERE id = ? AND server_id = ?
            ''', (position, role_id, server_id))
        self.conn.commit() # pyright: ignore[reportOptionalMemberAccess]
