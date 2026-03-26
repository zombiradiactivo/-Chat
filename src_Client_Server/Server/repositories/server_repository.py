"""
Repositorio de servidores
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import CRUDRepository
from ..models.server import Server, ServerCreate, ServerUpdate
from ..models.enums import ConnectionType, SecurityLevel


class ServerRepository(CRUDRepository):
    """Repositorio para manejar servidores en SQLite"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la tabla de servidores"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT,
                description TEXT,
                owner_id TEXT NOT NULL,
                connection_type TEXT NOT NULL,
                security_level TEXT NOT NULL,
                max_members INTEGER DEFAULT 100,
                allow_file_transfer BOOLEAN DEFAULT 1,
                allow_video_streaming BOOLEAN DEFAULT 1,
                require_verification BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                member_count INTEGER DEFAULT 0,
                channels TEXT DEFAULT '[]',
                roles TEXT DEFAULT '[]',
                invites TEXT DEFAULT '[]',
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
    
    def _row_to_server(self, row: sqlite3.Row) -> Server:
        """Convierte una fila a objeto Server"""
        import json
        return Server(
            id=row['id'],
            name=row['name'],
            icon=row['icon'],
            description=row['description'],
            owner_id=row['owner_id'],
            connection_type=ConnectionType(row['connection_type']),
            security_level=SecurityLevel(row['security_level']),
            max_members=row['max_members'],
            allow_file_transfer=bool(row['allow_file_transfer']),
            allow_video_streaming=bool(row['allow_video_streaming']),
            require_verification=bool(row['require_verification']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now(),
            member_count=row['member_count'],
            channels=json.loads(row['channels']) if row['channels'] else [],
            roles=json.loads(row['roles']) if row['roles'] else [],
            invites=json.loads(row['invites']) if row['invites'] else []
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea un nuevo servidor"""
        server_id = str(uuid.uuid4())
        
        import json
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            INSERT INTO servers (
                id, name, icon, description, owner_id,
                connection_type, security_level, max_members,
                allow_file_transfer, allow_video_streaming, require_verification,
                created_at, updated_at, member_count, channels, roles, invites
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            server_id,
            data['name'],
            data.get('icon'),
            data.get('description'),
            data['owner_id'],
            data['connection_type'].value,
            data['security_level'].value,
            data.get('max_members', 100),
            data.get('allow_file_transfer', True),
            data.get('allow_video_streaming', True),
            data.get('require_verification', False),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            0,
            json.dumps([]),
            json.dumps([]),
            json.dumps([])
        ))
        self.conn.commit() # type: ignore
        return server_id
    
    def get_by_id(self, server_id: str) -> Optional[Server]:
        """Obtiene un servidor por ID"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
        row = cursor.fetchone()
        return self._row_to_server(row) if row else None
    
    def get_by_owner(self, owner_id: str) -> List[Server]:
        """Obtiene todos los servidores de un dueño"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM servers WHERE owner_id = ?', (owner_id,))
        rows = cursor.fetchall()
        return [self._row_to_server(row) for row in rows]
    
    def get_member_servers(self, user_id: str) -> List[Server]:
        """Obtiene todos los servidores donde un usuario es miembro"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            SELECT s.* FROM servers s
            JOIN server_members sm ON s.id = sm.server_id
            WHERE sm.user_id = ? AND sm.is_baned = 0
        ''', (user_id,))
        rows = cursor.fetchall()
        return [self._row_to_server(row) for row in rows]
    
    def get_all(self) -> List[Server]:
        """Obtiene todos los servidores"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('SELECT * FROM servers')
        rows = cursor.fetchall()
        return [self._row_to_server(row) for row in rows]
    
    def update(self, server_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un servidor"""
        import json
        
        fields = []
        values = []
        for key, value in data.items():
            if key not in ['id', 'created_at']:
                if key in ['connection_type', 'security_level']:
                    value = value.value
                elif key in ['channels', 'roles', 'invites']:
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(datetime.now().isoformat())
        values.append(server_id)
        
        cursor = self.conn.cursor() # type: ignore
        cursor.execute(f'''
            UPDATE servers SET {', '.join(fields)}, updated_at = ?
            WHERE id = ?
        ''', values)
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def delete(self, server_id: str) -> bool:
        """Elimina un servidor"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('DELETE FROM servers WHERE id = ?', (server_id,))
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def increment_member_count(self, server_id: str):
        """Incrementa el contador de miembros"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            UPDATE servers SET member_count = member_count + 1 WHERE id = ?
        ''', (server_id,))
        self.conn.commit()# type: ignore
    
    def decrement_member_count(self, server_id: str):
        """Decrementa el contador de miembros"""
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            UPDATE servers SET member_count = member_count - 1 WHERE id = ?
        ''', (server_id,))
        self.conn.commit()# type: ignore
