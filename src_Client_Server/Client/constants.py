"""
Constantes de la aplicación
"""
from enum import Enum


class AppState(Enum):
    """Estados de la aplicación"""
    LOGIN = "login"
    REGISTER = "register"
    MAIN = "main"


class MessageType(Enum):
    """Tipos de mensaje para el sistema de red"""
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SYSTEM = "system"
    VIDEO_FRAME = "video_frame"
    FILE_CHUNK = "file_chunk"
    FILE_COMPLETE = "file_complete"


class NetworkEvent(Enum):
    """Eventos de red"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MESSAGE_RECEIVED = "message"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"


# Colores de la aplicación (tema Discord-like)
COLORS = {
    'primary': '#7289DA',
    'secondary': '#99AAB5',
    'success': '#43B581',
    'warning': '#FAA61A',
    'danger': '#F04747',
    'background': '#36393F',
    'sidebar': '#202225',
    'channel': '#2F3136',
    'chat': '#36393F',
    'text': '#DCDDDE',
    'text_muted': '#72767D',
    'border': '#202225'
}

# Límites
LIMITS = {
    'username_min': 2,
    'username_max': 32,
    'password_min': 8,
    'server_name_max': 100,
    'channel_name_max': 100,
    'message_max_length': 2000,
    'max_servers_per_user': 100,
    'max_channels_per_server': 250,
    'max_roles_per_server': 250
}
