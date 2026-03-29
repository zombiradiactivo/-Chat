"""
Servicio de permisos
"""
from typing import List, Set, Optional
from ..repositories import RepositoryFactory
from ..models.enums import Permission
from ..models.role import Role
from ..models.server_member import ServerMember
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class PermissionService:
    """Servicio para gestionar permisos"""
    
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def has_permission(
        self,
        user_id: str,
        server_id: str,
        permission: Permission,
        channel_id: Optional[str] = None
    ) -> bool:
        """Verifica si un usuario tiene un permiso específico"""
        try:
            members_repo = self.repo_factory.get_repository('server_members')
            roles_repo = self.repo_factory.get_repository('roles')
            
            # Obtener miembro
            member = members_repo.get_by_id(user_id, server_id)
            if not member:
                return False
            
            # Obtener todos los roles del servidor
            all_roles = roles_repo.get_by_server(server_id)
            
            # Verificar permisos en todos los roles del usuario
            for role_id in member.role_ids:
                for role in all_roles:
                    if role.id == role_id:
                        if role.has_permission(permission):
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando permiso: {e}")
            return False
    
    def get_user_permissions(self, user_id: str, server_id: str) -> Set[Permission]:
        """Obtiene todos los permisos de un usuario en un servidor"""
        try:
            members_repo = self.repo_factory.get_repository('server_members')
            roles_repo = self.repo_factory.get_repository('roles')
            
            member = members_repo.get_by_id(user_id, server_id)
            if not member:
                return set()
            
            all_roles = roles_repo.get_by_server(server_id)
            permissions = set()
            
            for role_id in member.role_ids:
                for role in all_roles:
                    if role.id == role_id:
                        for perm_str in role.permissions:
                            try:
                                permissions.add(Permission(perm_str))
                            except ValueError:
                                continue
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error obteniendo permisos: {e}")
            return set()
    
    def get_highest_role_position(self, user_id: str, server_id: str) -> int:
        """Obtiene la posición más alta de los roles del usuario"""
        try:
            members_repo = self.repo_factory.get_repository('server_members')
            roles_repo = self.repo_factory.get_repository('roles')
            
            member = members_repo.get_by_id(user_id, server_id)
            if not member:
                return -1
            
            roles = roles_repo.get_by_server(server_id)
            max_position = -1
            
            for role_id in member.role_ids:
                for role in roles:
                    if role.id == role_id and role.position > max_position:
                        max_position = role.position
            
            return max_position
            
        except Exception as e:
            logger.error(f"Error obteniendo posición de rol: {e}")
            return -1
    
    def can_manage_role(self, user_id: str, server_id: str, target_role_id: str) -> bool:
        """Verifica si un usuario puede gestionar un rol específico"""
        try:
            members_repo = self.repo_factory.get_repository('server_members')
            roles_repo = self.repo_factory.get_repository('roles')
            
            member = members_repo.get_by_id(user_id, server_id)
            if not member:
                return False
            
            target_role = roles_repo.get_by_id(target_role_id)
            if not target_role:
                return False
            
            # No se puede modificar el rol @everyone
            if target_role.is_default:
                return False
            
            # Dueño del servidor siempre puede
            server = self.repo_factory.get_repository('servers').get_by_id(server_id)
            if server.owner_id == user_id:
                return True
            
            # Verificar si tiene permiso MANAGE_ROLES
            if self.has_permission(user_id, server_id, Permission.MANAGE_ROLES):
                # Verificar jerarquía: el rol del usuario debe ser superior al rol objetivo
                user_position = self.get_highest_role_position(user_id, server_id)
                if user_position > target_role.position:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando gestión de rol: {e}")
            return False
    
    def can_manage_channel(self, user_id: str, channel_id: str) -> bool:
        """Verifica si un usuario puede gestionar un canal"""
        try:
            channels_repo = self.repo_factory.get_repository('channels')
            channel = channels_repo.get_by_id(channel_id)
            if not channel:
                return False
            
            return self.has_permission(user_id, channel.server_id, Permission.MANAGE_CHANNELS)
            
        except Exception as e:
            logger.error(f"Error verificando gestión de canal: {e}")
            return False
    
    def can_send_message(self, user_id: str, channel_id: str) -> bool:
        """Verifica si un usuario puede enviar mensajes a un canal"""
        try:
            channels_repo = self.repo_factory.get_repository('channels')
            channel = channels_repo.get_by_id(channel_id)
            if not channel:
                return False
            
            # Verificar permiso base
            if not self.has_permission(user_id, channel.server_id, Permission.SEND_MESSAGES):
                return False
            
            # Verificar si el canal es privado y el usuario tiene acceso
            if channel.is_private:
                members_repo = self.repo_factory.get_repository('server_members')
                member = members_repo.get_by_id(user_id, channel.server_id)
                if not member:
                    return False
                
                # Verificar roles permitidos
                if channel.allowed_roles:
                    has_access = any(role_id in member.role_ids for role_id in channel.allowed_roles)
                    if not has_access:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando permiso de envío: {e}")
            return False
