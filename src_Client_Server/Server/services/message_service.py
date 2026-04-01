"""
Servicio de mensajería
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid

from ..repositories import RepositoryFactory
from ..models.message import Message, MessageCreate, MessageUpdate
from ..models.enums import MessageType
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class MessageService:
    """Servicio para gestionar mensajes"""
    
    def __init__(self, repo_factory: Optional[RepositoryFactory] = None):
        self.repo_factory = repo_factory or RepositoryFactory()
        self.messages_repo = self.repo_factory.get_repository('messages')
        self.channels_repo = self.repo_factory.get_repository('channels')
        self.file_transfer_service = None  # Se inyectará si es necesario
    
    def send_message(self, **kwargs) -> Tuple[bool, Optional[str], Optional[Message]]:
        """Envía un mensaje a un canal"""
        try:
            # Validar contenido
            content = kwargs.get('content', '').strip()
            if not content:
                return False, "El mensaje no puede estar vacío", None
            
            # Verificar que el canal existe
            channel = self.channels_repo.get_by_id(kwargs['channel_id'])
            if not channel:
                return False, "Canal no encontrado", None
            
            # Verificar que el usuario puede enviar mensajes
            # (se implementaría con permisos)
            
            message_data = {
                'content': content,
                'message_type': kwargs.get('message_type', MessageType.TEXT),
                'channel_id': kwargs['channel_id'],
                'author_id': kwargs['author_id'],
                'reply_to': kwargs.get('reply_to'),
                'mentions': kwargs.get('mentions', []),
                'attachments': kwargs.get('attachments', [])
            }
            
            message_id = self.messages_repo.create(message_data)
            message = self.messages_repo.get_by_id(message_id)
            
            # Actualizar estadísticas del canal
            self.channels_repo.update_message_count(channel.id, 1)
            self.channels_repo.update_last_message(channel.id)
            
            logger.info(f"Mensaje enviado en canal {channel.name}: {content[:50]}...")
            return True, None, message
            
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return False, "Error interno del servidor", None
    
    def edit_message(self, message_id: str, user_id: str, content: str) -> Tuple[bool, Optional[str], Optional[Message]]:
        """Edita un mensaje"""
        try:
            message = self.messages_repo.get_by_id(message_id)
            if not message:
                return False, "Mensaje no encontrado", None
            
            # Verificar que el usuario es el autor
            if message.author_id != user_id:
                return False, "No puedes editar este mensaje", None
            
            success = self.messages_repo.update(message_id, {'content': content})
            if success:
                message = self.messages_repo.get_by_id(message_id)
                logger.info(f"Mensaje editado: {message_id}")
                return True, None, message
            
            return False, "Error al editar mensaje", None
            
        except Exception as e:
            logger.error(f"Error editando mensaje: {e}")
            return False, "Error interno del servidor", None
    
    def delete_message(self, message_id: str, user_id: str, is_admin: bool = False) -> Tuple[bool, Optional[str]]:
        """Elimina un mensaje"""
        try:
            message = self.messages_repo.get_by_id(message_id)
            if not message:
                return False, "Mensaje no encontrado"
            
            # Solo autor o admin puede eliminar
            if message.author_id != user_id and not is_admin:
                return False, "No puedes eliminar este mensaje"
            
            success = self.messages_repo.delete(message_id)
            if success:
                logger.info(f"Mensaje eliminado: {message_id}")
                return True, None
            
            return False, "Error al eliminar mensaje"
            
        except Exception as e:
            logger.error(f"Error eliminando mensaje: {e}")
            return False, "Error interno del servidor"
    
    def get_channel_messages(self, channel_id: str, limit: int = 10, before: Optional[str] = None) -> List[Message]:
        """Obtiene mensajes de un canal"""
        try:
            messages = self.messages_repo.get_by_channel(channel_id, limit, before)
            return messages
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return []
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Obtiene un mensaje por ID"""
        return self.messages_repo.get_by_id(message_id)
    
    def add_reaction(self, message_id: str, user_id: str, emoji: str) -> Tuple[bool, Optional[str]]:
        """Añade una reacción a un mensaje"""
        try:
            message = self.messages_repo.get_by_id(message_id)
            if not message:
                return False, "Mensaje no encontrado"
            
            self.messages_repo.add_reaction(message_id, emoji, user_id)
            logger.info(f"Reacción añadida: {emoji} a mensaje {message_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error añadiendo reacción: {e}")
            return False, "Error interno del servidor"
    
    def remove_reaction(self, message_id: str, user_id: str, emoji: str) -> Tuple[bool, Optional[str]]:
        """Elimina una reacción de un mensaje"""
        try:
            message = self.messages_repo.get_by_id(message_id)
            if not message:
                return False, "Mensaje no encontrado"
            
            self.messages_repo.remove_reaction(message_id, emoji, user_id)
            logger.info(f"Reacción eliminada: {emoji} de mensaje {message_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error eliminando reacción: {e}")
            return False, "Error interno del servidor"
    
    def pin_message(self, message_id: str, user_id: str, server_id: str, has_permission: bool) -> Tuple[bool, Optional[str]]:
        """Fija un mensaje"""
        try:
            message = self.messages_repo.get_by_id(message_id)
            if not message:
                return False, "Mensaje no encontrado"
            
            if not has_permission:
                return False, "No tienes permiso para fijar mensajes"
            
            self.messages_repo.pin_message(message_id, True)
            logger.info(f"Mensaje fijado: {message_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error fijando mensaje: {e}")
            return False, "Error interno del servidor"
    
    def unpin_message(self, message_id: str, user_id: str, server_id: str, has_permission: bool) -> Tuple[bool, Optional[str]]:
        """Desfija un mensaje"""
        try:
            message = self.messages_repo.get_by_id(message_id)
            if not message:
                return False, "Mensaje no encontrado"
            
            if not has_permission:
                return False, "No tienes permiso para desfijar mensajes"
            
            self.messages_repo.pin_message(message_id, False)
            logger.info(f"Mensaje desfijado: {message_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error desfijando mensaje: {e}")
            return False, "Error interno del servidor"
    
    def get_pinned_messages(self, channel_id: str) -> List[Message]:
        """Obtiene mensajes fijados de un canal"""
        try:
            messages = self.messages_repo.get_by_channel(channel_id, limit=100)
            return [m for m in messages if m.pinned]
        except Exception as e:
            logger.error(f"Error obteniendo mensajes fijados: {e}")
            return []
