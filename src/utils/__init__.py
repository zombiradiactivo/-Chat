"""
Inicializador del paquete utils
"""
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import uuid
import os
import json
import hashlib
import mimetypes
import re

from .encryption import EncryptionService, AESEncryption
from .validation import validate_email, validate_username, validate_password, validate_server_name, validate_channel_name, validate_hex_color
from .logger import setup_logger, get_log_file_path
from .config_manager import ConfigManager

__all__ = [
    'EncryptionService',
    'AESEncryption',
    'validate_email',
    'validate_username',
    'validate_password',
    'validate_server_name',
    'validate_channel_name',
    'validate_hex_color',
    'setup_logger',
    'get_log_file_path',
    'ConfigManager'
]


def generate_id() -> str:
    """Genera un ID único"""
    return str(uuid.uuid4())


def generate_invite_code(length: int = 8) -> str:
    """Genera un código de invitación aleatorio"""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def ensure_directory(path: str) -> Path:
    """Asegura que un directorio existe"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_app_data_dir() -> Path:
    """Obtiene el directorio de datos de la aplicación"""
    home = Path.home()
    app_dir = home / ".discord_clone"
    return ensure_directory(str(app_dir))


def get_uploads_dir() -> Path:
    """Obtiene el directorio de uploads"""
    uploads = get_app_data_dir() / "uploads"
    return ensure_directory(str(uploads))


def get_avatars_dir() -> Path:
    """Obtiene el directorio de avatares"""
    avatars = get_app_data_dir() / "avatars"
    return ensure_directory(str(avatars))


def get_banners_dir() -> Path:
    """Obtiene el directorio de banners"""
    banners = get_app_data_dir() / "banners"
    return ensure_directory(str(banners))


def save_json(data: Any, filepath: str):
    """Guarda datos en formato JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def load_json(filepath: str, default: Any = None) -> Any:
    """Carga datos desde un archivo JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def compute_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Calcula el hash SHA-256 de un archivo"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def format_file_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_timestamp(dt: datetime, relative: bool = False) -> str:
    """Formatea una fecha/hora"""
    if relative:
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"hace {diff.days} día{'s' if diff.days > 1 else ''}"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"hace {hours} hora{'s' if hours > 1 else ''}"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
        else:
            return "ahora"
    else:
        return dt.strftime("%d/%m/%Y %H:%M")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Trunca un texto a una longitud máxima"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """Sanitiza un nombre de archivo"""
    import re
    # Eliminar caracteres peligrosos
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Eliminar espacios al inicio/final
    filename = filename.strip()
    # Limitar longitud
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename


def is_valid_image(filename: str) -> bool:
    """Verifica si un archivo es una imagen válida"""
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    ext = os.path.splitext(filename)[1].lower()
    return ext in valid_extensions


def is_valid_video(filename: str) -> bool:
    """Verifica si un archivo es un video válido"""
    valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    ext = os.path.splitext(filename)[1].lower()
    return ext in valid_extensions


def is_valid_audio(filename: str) -> bool:
    """Verifica si un archivo es un audio válido"""
    valid_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}
    ext = os.path.splitext(filename)[1].lower()
    return ext in valid_extensions


def get_mime_type(filename: str) -> str:
    """Obtiene el MIME type de un archivo"""
    import mimetypes
    mime, _ = mimetypes.guess_type(filename)
    return mime or 'application/octet-stream'


def deep_update(base_dict: Dict, update_dict: Dict) -> Dict:
    """Actualiza un diccionario de forma recursiva"""
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            base_dict[key] = deep_update(base_dict[key], value)
        else:
            base_dict[key] = value
    return base_dict
