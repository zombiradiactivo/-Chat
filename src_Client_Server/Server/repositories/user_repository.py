"""
Repositorio de usuarios
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from hashlib import sha256

from src_Client_Server.Server.repositories.base import CRUDRepository
from src_Client_Server.Server.models.user import User, UserCreate, UserUpdate


class UserRepository(CRUDRepository):
    """Repositorio para manejar usuarios en SQLite"""
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Inicializa la base de datos y crea las tablas"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                discriminator TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                profile_picture TEXT,
                banner TEXT,
                description TEXT,
                status TEXT DEFAULT 'offline',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_seen TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
    
    def _hash_password(self, password: str) -> str:
        """Hashea una contraseña"""
        return sha256(password.encode()).hexdigest()
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convierte una fila de la BD a un objeto User"""
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            discriminator=row['discriminator'],
            profile_picture=row['profile_picture'],
            banner=row['banner'],
            description=row['description'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now(),
            is_active=bool(row['is_active']),
            last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None
        )
    
    def create(self, data: Dict[str, Any]) -> str:
        """Crea un nuevo usuario"""
        user_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor() # type: ignore
        cursor.execute('''
            INSERT INTO users (
                id, username, email, discriminator, password_hash,
                profile_picture, banner, description, status,
                created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data['username'],
            data['email'],
            data.get('discriminator', '0000'),
            self._hash_password(data['password']),
            data.get('profile_picture'),
            data.get('banner'),
            data.get('description'),
            data.get('status', 'offline'),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            1
        ))
        self.conn.commit()# type: ignore
        return user_id
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Obtiene un usuario por ID"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por nombre de usuario"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None
    
    def get_all(self) -> List[User]:
        """Obtiene todos los usuarios"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT * FROM users WHERE is_active = 1')
        rows = cursor.fetchall()
        return [self._row_to_user(row) for row in rows]
    
    def update(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un usuario"""
        if 'password' in data:
            data['password_hash'] = self._hash_password(data.pop('password'))
        
        fields = []
        values = []
        for key, value in data.items():
            if key not in ['id', 'created_at']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(datetime.now().isoformat())  # updated_at
        values.append(user_id)
        
        cursor = self.conn.cursor()# type: ignore
        cursor.execute(f'''
            UPDATE users SET {', '.join(fields)}, updated_at = ?
            WHERE id = ?
        ''', values)
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def delete(self, user_id: str) -> bool:
        """Elimina un usuario (soft delete)"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        self.conn.commit()# type: ignore
        return cursor.rowcount > 0
    
    def verify_password(self, user_id: str, password: str) -> bool:
        """Verifica la contraseña de un usuario"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        return self._hash_password(password) == row['password_hash']
    
    def update_last_seen(self, user_id: str):
        """Actualiza el último visto del usuario"""
        cursor = self.conn.cursor()# type: ignore
        cursor.execute('''
            UPDATE users SET last_seen = ? WHERE id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()# type: ignore
