"""
Servicio de gestión de servidores
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid
import json

from repositories import RepositoryFactory
from models.server import Server, ServerCreate, ServerUpdate
from models.channel import Channel, ChannelCreate
from models.role import Role, RoleCreate
from models.server_member import ServerMember
from models.enums import ConnectionType, SecurityLevel, Permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ServerService:
    """Servicio para gestionar servidores"""
    
    def __init__(self, repo_factory: Optional[RepositoryFactory] = None):
        self.repo_factory = repo_factory or RepositoryFactory()
        self.servers_repo = self.repo_factory.get_repository('servers')
        self.channels_repo = self.repo_factory.get_repository('channels')
        self.roles_repo = self.repo_factory.get_repository('roles')
        self.members_repo = self.repo_factory.get_repository('server_members')
    
    def create_server(self, owner_id: str, **kwargs) -> Tuple[bool, Optional[str], Optional[Server]]:
        """Crea un nuevo servidor"""
        try:
            # Validar nombre
            from utils.validation import validate_server_name
            is_valid, error = validate_server_name(kwargs.get('name', ''))
            if not is_valid:
                return False, error, None

            # Crear servidor
            server_data = {
                'name': kwargs['name'],
                'owner_id': owner_id,
                'icon': kwargs.get('icon'),
                'description': kwargs.get('description'),
                'connection_type': kwargs.get('connection_type', ConnectionType.CLIENT_SERVER),
                'security_level': kwargs.get('security_level', SecurityLevel.BASIC),
                'max_members': kwargs.get('max_members', 100),
                'allow_file_transfer': kwargs.get('allow_file_transfer', True),
                'allow_video_streaming': kwargs.get('allow_video_streaming', True),
                'require_verification': kwargs.get('require_verification', False)
            }

            server_id = self.servers_repo.create(server_data)
            server = self.servers_repo.get_by_id(server_id)

            # 1. Crear rol @everyone
            everyone_role_id = self._create_everyone_role(server_id)

            # 2. Añadir dueño como miembro con rol @everyone
            self._add_member(owner_id, server_id, [everyone_role_id])

            # 3. Crear rol Admin y asignarlo al dueño
            admin_role_id = self._create_admin_role(server_id)
            self._add_role_to_member(owner_id, server_id, admin_role_id)

            # 4. Crear canales por defecto
            self._create_default_channels(server_id)

            logger.info(f"Servidor creado: {server.name} ({server_id})")
            return True, None, server

        except Exception as e:
            logger.error(f"Error creando servidor: {e}")
            return False, "Error interno del servidor", None
    
    def update_server(self, server_id: str, user_id: str, **kwargs) -> Tuple[bool, Optional[str], Optional[Server]]:
        """Actualiza un servidor (solo dueño o con permiso)"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado", None
            
            # Verificar que el usuario es el dueño
            if server.owner_id != user_id:
                return False, "No tienes permiso para modificar este servidor", None
            
            success = self.servers_repo.update(server_id, kwargs)
            if success:
                server = self.servers_repo.get_by_id(server_id)
                logger.info(f"Servidor actualizado: {server.name}")
                return True, None, server
            
            return False, "Error al actualizar", None
            
        except Exception as e:
            logger.error(f"Error actualizando servidor: {e}")
            return False, "Error interno del servidor", None
    
    def delete_server(self, server_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """Elimina un servidor (solo dueño)"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado"
            
            if server.owner_id != user_id:
                return False, "No tienes permiso para eliminar este servidor"
            
            # Eliminar canales, roles y miembros asociados
            self._delete_server_data(server_id)
            
            success = self.servers_repo.delete(server_id)
            if success:
                logger.info(f"Servidor eliminado: {server.name}")
                return True, None
            
            return False, "Error al eliminar servidor"
            
        except Exception as e:
            logger.error(f"Error eliminando servidor: {e}")
            return False, "Error interno del servidor"
    
    def get_server(self, server_id: str) -> Optional[Server]:
        """Obtiene un servidor por ID"""
        return self.servers_repo.get_by_id(server_id)
    
    def get_user_servers(self, user_id: str) -> List[Server]:
        """Obtiene todos los servidores de un usuario"""
        return self.servers_repo.get_member_servers(user_id)
    
    def get_server_channels(self, server_id: str) -> List[Channel]:
        """Obtiene todos los canales de un servidor"""
        return self.channels_repo.get_by_server(server_id)
    
    def create_channel(self, server_id: str, creator_id: str, **kwargs) -> Tuple[bool, Optional[str], Optional[Channel]]:
        """Crea un canal en un servidor"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado", None
            
            # Verificar permiso (dueño o manage_channels)
            if not self._has_permission(creator_id, server_id, Permission.MANAGE_CHANNELS):
                return False, "No tienes permiso para crear canales", None
            
            from utils.validation import validate_channel_name
            is_valid, error = validate_channel_name(kwargs.get('name', ''))
            if not is_valid:
                return False, error, None
            
            channel_data = {
                'name': kwargs['name'],
                'type': kwargs['type'],
                'server_id': server_id,
                'topic': kwargs.get('topic'),
                'position': kwargs.get('position', 0),
                'is_private': kwargs.get('is_private', False),
                'allowed_roles': kwargs.get('allowed_roles', []),
                'parent_id': kwargs.get('parent_id')
            }
            
            channel_id = self.channels_repo.create(channel_data)
            channel = self.channels_repo.get_by_id(channel_id)
            
            # Actualizar lista de canales del servidor
            server.channels.append(channel_id)
            self.servers_repo.update(server_id, {'channels': server.channels})
            
            logger.info(f"Canal creado: {channel.name} en servidor {server.name}")
            return True, None, channel
            
        except Exception as e:
            logger.error(f"Error creando canal: {e}")
            return False, "Error interno del servidor", None
    
    def delete_channel(self, channel_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """Elimina un canal"""
        try:
            channel = self.channels_repo.get_by_id(channel_id)
            if not channel:
                return False, "Canal no encontrado"
            
            server = self.servers_repo.get_by_id(channel.server_id)
            if not server:
                return False, "Servidor no encontrado"
            
            if server.owner_id != user_id and not self._has_permission(user_id, channel.server_id, Permission.MANAGE_CHANNELS):
                return False, "No tienes permiso para eliminar este canal"
            
            # Eliminar de la lista de canales del servidor
            if channel_id in server.channels:
                server.channels.remove(channel_id)
                self.servers_repo.update(server.id, {'channels': server.channels})
            
            success = self.channels_repo.delete(channel_id)
            if success:
                logger.info(f"Canal eliminado: {channel.name}")
                return True, None
            
            return False, "Error al eliminar canal"
            
        except Exception as e:
            logger.error(f"Error eliminando canal: {e}")
            return False, "Error interno del servidor"
    
    def create_role(self, server_id: str, creator_id: str, **kwargs) -> Tuple[bool, Optional[str], Optional[Role]]:
        """Crea un rol en un servidor"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado", None
            
            # Verificar permiso
            if not self._has_permission(creator_id, server_id, Permission.MANAGE_ROLES):
                return False, "No tienes permiso para crear roles", None
            
            role_data = {
                'server_id': server_id,
                'name': kwargs['name'],
                'color': kwargs.get('color', '#99AAB5'),
                'permissions': kwargs.get('permissions', []),
                'mentionable': kwargs.get('mentionable', False),
                'hoisted': kwargs.get('hoisted', False),
                'position': kwargs.get('position', 0)
            }
            
            role_id = self.roles_repo.create(role_data)
            role = self.roles_repo.get_by_id(role_id)
            
            # Actualizar lista de roles del servidor
            server.roles.append(role_id)
            self.servers_repo.update(server_id, {'roles': server.roles})
            
            logger.info(f"Rol creado: {role.name} en servidor {server.name}")
            return True, None, role
            
        except Exception as e:
            logger.error(f"Error creando rol: {e}")
            return False, "Error interno del servidor", None
    
    def update_role(self, role_id: str, user_id: str, **kwargs) -> Tuple[bool, Optional[str], Optional[Role]]:
        """Actualiza un rol"""
        try:
            role = self.roles_repo.get_by_id(role_id)
            if not role:
                return False, "Rol no encontrado", None
            
            # Verificar permiso
            if not self._has_permission(user_id, role.server_id, Permission.MANAGE_ROLES):
                return False, "No tienes permiso para modificar roles", None
            
            # No permitir modificar el rol @everyone
            if role.is_default:
                return False, "No puedes modificar el rol @everyone"
            
            success = self.roles_repo.update(role_id, kwargs)
            if success:
                role = self.roles_repo.get_by_id(role_id)
                logger.info(f"Rol actualizado: {role.name}")
                return True, None, role
            
            return False, "Error al actualizar rol", None
            
        except Exception as e:
            logger.error(f"Error actualizando rol: {e}")
            return False, "Error interno del servidor", None
    
    def delete_role(self, role_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """Elimina un rol"""
        try:
            role = self.roles_repo.get_by_id(role_id)
            if not role:
                return False, "Rol no encontrado"
            
            if role.is_default:
                return False, "No puedes eliminar el rol @everyone"
            
            if not self._has_permission(user_id, role.server_id, Permission.MANAGE_ROLES):
                return False, "No tienes permiso para eliminar roles"
            
            # Eliminar de la lista de roles del servidor
            server = self.servers_repo.get_by_id(role.server_id)
            if role_id in server.roles:
                server.roles.remove(role_id)
                self.servers_repo.update(server.id, {'roles': server.roles})
            
            # Eliminar rol de todos los miembros
            members = self.members_repo.get_by_server(role.server_id)
            for member in members:
                if role_id in member.role_ids:
                    member.role_ids.remove(role_id)
                    self.members_repo.update(member.user_id, role.server_id, {'role_ids': member.role_ids})
            
            success = self.roles_repo.delete(role_id)
            if success:
                logger.info(f"Rol eliminado: {role.name}")
                return True, None
            
            return False, "Error al eliminar rol"
            
        except Exception as e:
            logger.error(f"Error eliminando rol: {e}")
            return False, "Error interno del servidor"
    
    def join_server(self, user_id: str, server_id: str) -> Tuple[bool, Optional[str]]:
        """Unirse a un servidor"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado"
            
            # Verificar si ya es miembro
            if self.members_repo.is_member(user_id, server_id):
                return False, "Ya eres miembro de este servidor"
            
            # Verificar límite de miembros
            if server.member_count >= server.max_members:
                return False, "El servidor está lleno"
            
            # Verificar si está baneado
            if self.members_repo.is_baned(user_id, server_id):
                return False, "Estás baneado de este servidor"
            
            # Obtener rol por defecto
            default_role = self.roles_repo.get_default_role(server_id)
            role_ids = [default_role.id] if default_role else []
            
            # Añadir miembro
            member_data = {
                'user_id': user_id,
                'server_id': server_id,
                'role_ids': role_ids
            }
            
            self.members_repo.create(member_data)
            self.servers_repo.increment_member_count(server_id)
            
            logger.info(f"Usuario {user_id} se unió a servidor {server.name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error uniéndose a servidor: {e}")
            return False, "Error interno del servidor"
    
    def leave_server(self, user_id: str, server_id: str) -> Tuple[bool, Optional[str]]:
        """Abandonar un servidor"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado"
            
            if server.owner_id == user_id:
                return False, "El dueño no puede abandonar el servidor (debe transferirlo o eliminarlo)"
            
            success = self.members_repo.delete(user_id, server_id)
            if success:
                self.servers_repo.decrement_member_count(server_id)
                logger.info(f"Usuario {user_id} abandonó servidor {server.name}")
                return True, None
            
            return False, "No eres miembro de este servidor"
            
        except Exception as e:
            logger.error(f"Error abandonando servidor: {e}")
            return False, "Error interno del servidor"
    
    def get_server_members(self, server_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los miembros de un servidor"""
        try:
            members = self.members_repo.get_by_server(server_id)
            users_repo = self.repo_factory.get_repository('users')
            
            result = []
            for member in members:
                user = users_repo.get_by_id(member.user_id)
                if user:
                    roles = []
                    for role_id in member.role_ids:
                        role = self.roles_repo.get_by_id(role_id)
                        if role:
                            roles.append(role.to_dict())
                    
                    result.append({
                        'user': user.to_dict(),
                        'member': member.to_dict(),
                        'roles': roles
                    })
            
            return result
        except Exception as e:
            logger.error(f"Error obteniendo miembros: {e}")
            return []
    
    def _create_everyone_role(self, server_id: str) -> str:
        """Crea el rol @everyone y devuelve su ID"""
        everyone_role = RoleCreate(
            server_id=server_id,
            name="@everyone",
            is_default=True,
            permissions=[
                Permission.SEND_MESSAGES.value,
                Permission.READ_MESSAGE_HISTORY.value,
                Permission.CONNECT.value,
                Permission.SEND_FILES.value,
                Permission.RECEIVE_FILES.value
            ]
        )
        return self.roles_repo.create(everyone_role.dict())

    def _create_admin_role(self, server_id: str) -> str:
        """Crea el rol Admin y devuelve su ID"""
        admin_role = RoleCreate(
            server_id=server_id,
            name="Admin",
            color="#FF5555",
            permissions=[p.value for p in Permission],
            hoisted=True
        )
        return self.roles_repo.create(admin_role.dict())

    def _add_role_to_member(self, user_id: str, server_id: str, role_id: str) -> bool:
        """Añade un rol a un miembro"""
        member = self.members_repo.get_by_id(user_id, server_id)
        if member and role_id not in member.role_ids:
            member.role_ids.append(role_id)
            return self.members_repo.update(user_id, server_id, {'role_ids': member.role_ids})
        return False
    
    def _create_default_channels(self, server_id: str):
        """Crea canales por defecto"""
        # Canal de texto general
        text_channel = ChannelCreate(
            server_id=server_id,
            name="general",
            type="text",
            topic="Canal general de conversación"
        )
        self.channels_repo.create(text_channel.dict())
        
        # Canal de voz general
        voice_channel = ChannelCreate(
            server_id=server_id,
            name="Voz General",
            type="voice"
        )
        self.channels_repo.create(voice_channel.dict())
    
    def _add_member(self, user_id: str, server_id: str, role_ids: List[str]):
        """Añade un miembro al servidor"""
        member_data = {
            'user_id': user_id,
            'server_id': server_id,
            'role_ids': role_ids
        }
        self.members_repo.create(member_data)
    
    def _get_everyone_role_id(self, server_id: str) -> str:
        """Obtiene el ID del rol @everyone"""
        role = self.roles_repo.get_default_role(server_id)
        return role.id if role else ""
    
    def _has_permission(self, user_id: str, server_id: str, permission: Permission) -> bool:
        """Verifica si un usuario tiene un permiso en un servidor"""
        member = self.members_repo.get_by_id(user_id, server_id)
        if not member:
            return False
        
        roles = self.roles_repo.get_by_server(server_id)
        for role_id in member.role_ids:
            for role in roles:
                if role.id == role_id and role.has_permission(permission):
                    return True
        
        return False
    
    def _delete_server_data(self, server_id: str):
        """Elimina todos los datos asociados a un servidor"""
        # Eliminar canales
        channels = self.channels_repo.get_by_server(server_id)
        for channel in channels:
            self.channels_repo.delete(channel.id)
        
        # Eliminar roles
        roles = self.roles_repo.get_by_server(server_id)
        for role in roles:
            self.roles_repo.delete(role.id)
        
        # Eliminar miembros
        members = self.members_repo.get_by_server(server_id, include_banned=True)
        for member in members:
            self.members_repo.delete(member.user_id, server_id)
