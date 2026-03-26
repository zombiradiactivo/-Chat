"""
Enumeraciones del sistema
"""
from enum import Enum

class ConnectionType(Enum):
    """Tipo de conexión del servidor"""
    P2P = "p2p"
    CLIENT_SERVER = "client_server"

class SecurityLevel(Enum):
    """Nivel de seguridad del servidor"""
    NONE = "none"
    BASIC = "basic"
    ENCRYPTED = "encrypted"
    END_TO_END = "e2e"

class ChannelType(Enum):
    """Tipo de canal"""
    TEXT = "text"
    VOICE = "voice"
    VIDEO = "video"

class MessageType(Enum):
    """Tipo de mensaje"""
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SYSTEM = "system"

class UserStatus(Enum):
    """Estado del usuario"""
    ONLINE = "online"
    OFFLINE = "offline"
    IDLE = "idle"
    DO_NOT_DISTURB = "dnd"
    INVISIBLE = "invisible"

class Permission(Enum):
    """Permisos disponibles en el sistema"""
    # Permisos de servidor
    MANAGE_SERVER = "manage_server"
    MANAGE_ROLES = "manage_roles"
    MANAGE_CHANNELS = "manage_channels"
    KICK_MEMBERS = "kick_members"
    BAN_MEMBERS = "ban_members"
    MANAGE_MESSAGES = "manage_messages"
    CREATE_INSTANT_INVITE = "create_invite"
    
    # Permisos de canal
    SEND_MESSAGES = "send_messages"
    SEND_TTS_MESSAGES = "send_tts_messages"
    EMBED_LINKS = "embed_links"
    ATTACH_FILES = "attach_files"
    READ_MESSAGE_HISTORY = "read_history"
    MENTION_EVERYONE = "mention_everyone"
    USE_EXTERNAL_EMOJIS = "use_external_emojis"
    
    # Permisos de voz/video
    CONNECT = "connect"
    SPEAK = "speak"
    MUTE_MEMBERS = "mute_members"
    DEAFEN_MEMBERS = "deafen_members"
    MOVE_MEMBERS = "move_members"
    USE_VAD = "use_vad"
    STREAM = "stream"
    
    # Permisos de archivos
    SEND_FILES = "send_files"
    RECEIVE_FILES = "receive_files"

__all__ = [
    'ConnectionType',
    'SecurityLevel',
    'ChannelType',
    'MessageType',
    'UserStatus',
    'Permission'
]
