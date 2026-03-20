"""
Inicializador del paquete repositories
"""
from typing import Dict, Any
from src.repositories.base import Repository, CRUDRepository
from src.repositories.user_repository import UserRepository
from src.repositories.server_repository import ServerRepository
from src.repositories.channel_repository import ChannelRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.server_member_repository import ServerMemberRepository
from src.repositories.invite_repository import InviteRepository
from src.repositories.file_transfer_repository import FileTransferRepository


class RepositoryFactory:
    """Factory para crear y gestionar repositorios"""
    
    _repositories: Dict[str, Any] = {}
    _db_path: str = "data/chat.db"
    
    def __init__(self, db_path: str = "data/chat.db"):
        self._db_path = db_path
        self._initialize_repositories()
    
    def _initialize_repositories(self):
        """Inicializa todos los repositorios"""
        self._repositories = {
            'users': UserRepository(self._db_path),
            'servers': ServerRepository(self._db_path),
            'channels': ChannelRepository(self._db_path),
            'messages': MessageRepository(self._db_path),
            'roles': RoleRepository(self._db_path),
            'server_members': ServerMemberRepository(self._db_path),
            'invites': InviteRepository(self._db_path),
            'file_transfers': FileTransferRepository(self._db_path)
        }
        
        # Inicializar todas las tablas
        for repo in self._repositories.values():
            repo.initialize()
    
    def get_repository(self, name: str) -> Any:
        """Obtiene un repositorio por nombre"""
        return self._repositories.get(name)
    
    def close_all(self):
        """Cierra todas las conexiones de repositorios"""
        for repo in self._repositories.values():
            repo.close()
    
    def initialize_database(self):
        """Inicializa la base de datos completa"""
        self._initialize_repositories()


__all__ = [
    'Repository',
    'CRUDRepository',
    'UserRepository',
    'ServerRepository',
    'ChannelRepository',
    'MessageRepository',
    'RoleRepository',
    'ServerMemberRepository',
    'InviteRepository',
    'FileTransferRepository',
    'RepositoryFactory'
]
