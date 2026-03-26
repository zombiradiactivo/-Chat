"""
Servicio de invitaciones
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid

from repositories import RepositoryFactory
from models.invite import Invite, InviteCreate
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InviteService:
    """Servicio para gestionar invitaciones"""
    
    def __init__(self, repo_factory: Optional[RepositoryFactory] = None):
        self.repo_factory = repo_factory or RepositoryFactory()
        self.invites_repo = self.repo_factory.get_repository('invites')
        self.servers_repo = self.repo_factory.get_repository('servers')
    
    def create_invite(
        self,
        server_id: str,
        creator_id: str,
        max_uses: Optional[int] = None,
        expires_in_hours: Optional[int] = None,
        is_temporary: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Invite]]:
        """Crea una nueva invitación"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return False, "Servidor no encontrado", None
            
            # Generar código único
            code = self._generate_unique_code()
            
            invite_data = {
                'server_id': server_id,
                'creator_id': creator_id,
                'code': code,
                'max_uses': max_uses,
                'expires_in': expires_in_hours,
                'is_temporary': is_temporary
            }
            
            invite_id = self.invites_repo.create(invite_data)
            invite = self.invites_repo.get_by_id(invite_id)
            
            logger.info(f"Invitación creada: {code} para servidor {server.name}")
            return True, None, invite
            
        except Exception as e:
            logger.error(f"Error creando invitación: {e}")
            return False, "Error interno del servidor", None
    
    def accept_invite(self, user_id: str, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Acepta una invitación y une al usuario al servidor"""
        try:
            invite = self.invites_repo.get_by_code(code)
            if not invite:
                return False, "Invitación no encontrada", None
            
            # Verificar validez
            if not invite.is_valid():
                return False, "Esta invitación ya no es válida", None
            
            server = self.servers_repo.get_by_id(invite.server_id)
            if not server:
                return False, "Servidor no encontrado", None
            
            # Verificar si ya es miembro
            from repositories import RepositoryFactory
            members_repo = RepositoryFactory().get_repository('server_members')
            if members_repo.is_member(user_id, invite.server_id):
                return False, "Ya eres miembro de este servidor", None
            
            # Verificar límite de miembros
            if server.member_count >= server.max_members:
                return False, "El servidor está lleno", None
            
            # Unir al usuario
            members_repo.create({
                'user_id': user_id,
                'server_id': invite.server_id
            })
            
            # Incrementar contador
            self.servers_repo.increment_member_count(invite.server_id)
            
            # Incrementar usos
            self.invites_repo.increment_uses(invite.id)
            
            logger.info(f"Invitación aceptada: {code} por usuario {user_id}")
            return True, None, server.to_dict()
            
        except Exception as e:
            logger.error(f"Error aceptando invitación: {e}")
            return False, "Error interno del servidor", None
    
    def revoke_invite(self, invite_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """Revoca una invitación"""
        try:
            invite = self.invites_repo.get_by_id(invite_id)
            if not invite:
                return False, "Invitación no encontrada"
            
            # Solo el creador o dueño del servidor pueden revocar
            server = self.servers_repo.get_by_id(invite.server_id)
            if invite.creator_id != user_id and server.owner_id != user_id:
                return False, "No tienes permiso para revocar esta invitación"
            
            success = self.invites_repo.delete(invite_id)
            if success:
                logger.info(f"Invitación revocada: {invite.code}")
                return True, None
            
            return False, "Error al revocar invitación"
            
        except Exception as e:
            logger.error(f"Error revocando invitación: {e}")
            return False, "Error interno del servidor"
    
    def get_server_invites(self, server_id: str, user_id: str) -> List[Invite]:
        """Obtiene todas las invitaciones de un servidor"""
        try:
            server = self.servers_repo.get_by_id(server_id)
            if not server:
                return []
            
            # Solo dueño o con permiso pueden ver todas
            if server.owner_id != user_id:
                # Verificar permiso
                members_repo = RepositoryFactory().get_repository('server_members')
                member = members_repo.get_by_id(user_id, server_id)
                if not member:
                    return []
                # Verificar permiso MANAGE_SERVER
                # (implementar)
            
            return self.invites_repo.get_by_server(server_id)
        except Exception as e:
            logger.error(f"Error obteniendo invitaciones: {e}")
            return []
    
    def _generate_unique_code(self, length: int = 8) -> str:
        """Genera un código de invitación único"""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            existing = self.invites_repo.get_by_code(code)
            if not existing:
                return code
