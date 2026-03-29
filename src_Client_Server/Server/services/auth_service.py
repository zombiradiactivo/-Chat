"""
Servicio de autenticación y gestión de usuarios
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

from ..repositories import RepositoryFactory
from ..models.user import User, UserCreate, UserUpdate
from ..models.server_member import ServerMember
from ..models.enums import UserStatus
from ..utils.logger import setup_logger

from ..utils.validation import validate_username, validate_email, validate_password


logger = setup_logger(__name__)


class AuthService:
    """Servicio de autenticación"""
    
    def __init__(self, repo_factory: Optional[RepositoryFactory] = None):
        self.repo_factory = repo_factory or RepositoryFactory()
        self.users_repo = self.repo_factory.get_repository('users')
        self.members_repo = self.repo_factory.get_repository('server_members')
        self.current_user: Optional[User] = None
    
    def register(self, username: str, email: str, password: str) -> Tuple[bool, Optional[str], Optional[User]]:
        """Registra un nuevo usuario"""
        try:
            # Validar datos
            
            is_valid, error = validate_username(username)
            if not is_valid:
                return False, error, None
            
            is_valid, error = validate_email(email)
            if not is_valid:
                return False, error, None
            
            is_valid, error = validate_password(password)
            if not is_valid:
                return False, error, None
            
            # Verificar que el usuario no exista
            if self.users_repo.get_by_username(username):
                return False, "El nombre de usuario ya está en uso", None
            
            if self.users_repo.get_by_email(email):
                return False, "El email ya está registrado", None
            
            # Crear usuario
            user_data = {
                'username': username,
                'email': email,
                'password': password,
                'discriminator': self._generate_discriminator(username)
            }
            
            user_id = self.users_repo.create(user_data)
            user = self.users_repo.get_by_id(user_id)
            
            logger.info(f"Usuario registrado: {username} ({user_id})")
            return True, None, user
            
        except Exception as e:
            logger.error(f"Error en registro: {e}")
            return False, "Error interno del servidor", None
    
    def login(self, identifier: str, password: str) -> Tuple[bool, Optional[str], Optional[User]]:
        """Autentica un usuario"""
        try:
            # Buscar usuario por username o email
            user = self.users_repo.get_by_username(identifier)
            if not user:
                user = self.users_repo.get_by_email(identifier)
            
            if not user:
                return False, "Usuario no encontrado", None
            
            if not user.is_active:
                return False, "La cuenta está desactivada", None
            
            # Verificar contraseña
            if not self.users_repo.verify_password(user.id, password):
                return False, "Contraseña incorrecta", None
            
            # Actualizar último acceso
            self.users_repo.update_last_seen(user.id)
            user.last_seen = datetime.now()
            
            self.current_user = user
            logger.info(f"Usuario logueado: {user.username}")
            return True, None, user
            
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False, "Error interno del servidor", None
    
    def logout(self):
        """Cierra sesión"""
        if self.current_user:
            logger.info(f"Usuario deslogueado: {self.current_user.username}")
            self.current_user = None
    
    def get_current_user(self) -> Optional[User]:
        """Obtiene el usuario actual"""
        return self.current_user
    
    def update_profile(self, user_id: str, **kwargs) -> Tuple[bool, Optional[str], Optional[User]]:
        """Actualiza el perfil de un usuario"""
        try:
            user = self.users_repo.get_by_id(user_id)
            if not user:
                return False, "Usuario no encontrado", None
            
            # Validar username si se cambia
            if 'username' in kwargs and kwargs['username'] != user.username:
                is_valid, error = validate_username(kwargs['username'])
                if not is_valid:
                    return False, error, None
                
                if self.users_repo.get_by_username(kwargs['username']):
                    return False, "El nombre de usuario ya está en uso", None
            
            # Validar email si se cambia
            if 'email' in kwargs and kwargs['email'] != user.email:
                is_valid, error = validate_email(kwargs['email'])
                if not is_valid:
                    return False, error, None
                
                if self.users_repo.get_by_email(kwargs['email']):
                    return False, "El email ya está registrado", None
            
            success = self.users_repo.update(user_id, kwargs)
            if success:
                user = self.users_repo.get_by_id(user_id)
                logger.info(f"Perfil actualizado: {user.username}")
                return True, None, user
            
            return False, "Error al actualizar", None
            
        except Exception as e:
            logger.error(f"Error actualizando perfil: {e}")
            return False, "Error interno del servidor", None
    
    def delete_account(self, user_id: str) -> bool:
        """Elimina la cuenta de un usuario (soft delete)"""
        try:
            success = self.users_repo.delete(user_id)
            if success:
                logger.info(f"Cuenta eliminada: {user_id}")
                if self.current_user and self.current_user.id == user_id:
                    self.current_user = None
            return success
        except Exception as e:
            logger.error(f"Error eliminando cuenta: {e}")
            return False
    
    def _generate_discriminator(self, username: str) -> str:
        """Genera un discriminador único (como Discord)"""
        import random
        # Por simplicidad, generamos 4 dígitos aleatorios
        # En producción, se buscaría uno que no esté en uso
        return f"{random.randint(0, 9999):04d}"
    
    def get_user_servers(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los servidores donde un usuario es miembro"""
        try:
            members = self.members_repo.get_by_user(user_id)
            servers_repo = self.repo_factory.get_repository('servers')
            servers = []
            
            for member in members:
                server = servers_repo.get_by_id(member.server_id)
                if server:
                    servers.append(server.to_dict())
            
            return servers
        except Exception as e:
            logger.error(f"Error obteniendo servidores del usuario: {e}")
            return []
