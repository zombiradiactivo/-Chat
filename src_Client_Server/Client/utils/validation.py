"""
Utilidades de validación
"""
import re
from typing import Tuple, Optional


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Valida un email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Email inválido"
    return True, None


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """Valida un nombre de usuario"""
    if len(username) < 2 or len(username) > 32:
        return False, "El nombre de usuario debe tener entre 2 y 32 caracteres"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos"
    
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """Valida una contraseña"""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    # Opcional: verificar complejidad
    # if not re.search(r'[A-Z]', password):
    #     return False, "La contraseña debe contener al menos una mayúscula"
    # if not re.search(r'[a-z]', password):
    #     return False, "La contraseña debe contener al menos una minúscula"
    # if not re.search(r'[0-9]', password):
    #     return False, "La contraseña debe contener al menos un número"
    
    return True, None


def validate_server_name(name: str) -> Tuple[bool, Optional[str]]:
    """Valida el nombre de un servidor"""
    if len(name) < 1 or len(name) > 100:
        return False, "El nombre debe tener entre 1 y 100 caracteres"
    return True, None


def validate_channel_name(name: str) -> Tuple[bool, Optional[str]]:
    """Valida el nombre de un canal"""
    if len(name) < 1 or len(name) > 100:
        return False, "El nombre debe tener entre 1 y 100 caracteres"
    
    if not all(c.isalnum() or c in '- _' for c in name):
        return False, "El nombre solo puede contener letras, números, guiones y espacios"
    
    return True, None


def validate_hex_color(color: str) -> Tuple[bool, Optional[str]]:
    """Valida un color hexadecimal"""
    pattern = r'^#[0-9A-Fa-f]{6}$'
    if not re.match(pattern, color):
        return False, "El color debe ser un hexadecimal válido (ej: #FF5733)"
    return True, None
