"""
Configuración de la aplicación
"""
import os
from pathlib import Path

# Directorio base
BASE_DIR = Path(__file__).parent

# Directorios
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
UPLOADS_DIR = DATA_DIR / "uploads"
AVATARS_DIR = DATA_DIR / "avatars"
BANNERS_DIR = DATA_DIR / "banners"

# Crear directorios si no existen
for directory in [DATA_DIR, LOGS_DIR, UPLOADS_DIR, AVATARS_DIR, BANNERS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Base de datos
DATABASE_PATH = DATA_DIR / "chat.db"

# Configuración de red
NETWORK = {
    'default_host': '127.0.0.1',
    'default_port': 5555,
    'buffer_size': 4096,
    'max_connections': 100
}

# Configuración de archivos
FILES = {
    'max_file_size': 100 * 1024 * 1024,  # 100 MB
    'allowed_extensions': {
        'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
        'videos': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
        'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
        'documents': ['.pdf', '.txt', '.doc', '.docx']
    },
    'chunk_size': 8192
}

# Configuración de UI
UI = {
    'theme': 'dark',
    'color_theme': 'blue',
    'window_size': (1200, 700),
    'min_window_size': (900, 500),
    'sidebar_width': 72,
    'channel_panel_width': 240,
    'members_panel_width': 240
}

# Configuración de video/audio
STREAMING = {
    'video_fps': 15,
    'video_quality': 70,
    'audio_sample_rate': 44100,
    'audio_channels': 2,
    'max_broadcasters_per_channel': 10
}

# Configuración de logging
LOGGING = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'log_to_file': True,
    'log_to_console': True
}
