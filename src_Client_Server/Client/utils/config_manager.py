"""
Gestor de configuraciones de la aplicación
"""
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

class ConfigManager:
    """Gestor de configuraciones guardadas en JSON"""
    
    CONFIG_DIR = Path(__file__).parent.parent.parent / "Client/data"
    CONFIG_FILE = CONFIG_DIR / "app_config.json"
    
    # Configuración por defecto
    DEFAULT_CONFIG = {
        "server": {
            "host": "127.0.0.1",
            "port": 5555
        },
        "ui": {
            "remember_username": False,
            "last_username": None
        },
        "last_login": None
    }
    
    @classmethod
    def initialize(cls):
        """Inicializa el archivo de configuración si no existe"""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        if not cls.CONFIG_FILE.exists():
            cls.save_config(cls.DEFAULT_CONFIG)
    
    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Carga la configuración desde JSON"""
        cls.initialize()
        
        try:
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            return cls.DEFAULT_CONFIG.copy()
    
    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> bool:
        """Guarda la configuración a JSON"""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            return False
    
    @classmethod
    def get_server_config(cls) -> tuple:
        """Obtiene la configuración del servidor como tupla (host, port)"""
        config = cls.load_config()
        server_config = config.get('server', cls.DEFAULT_CONFIG['server'])
        host = server_config.get('host', '127.0.0.1')
        port = int(server_config.get('port', 5555))
        return host, port
    
    @classmethod
    def set_server_config(cls, host: str, port: int) -> bool:
        """Guarda la configuración del servidor"""
        config = cls.load_config()
        config['server'] = {
            'host': host,
            'port': port
        }
        config['last_login'] = datetime.now().isoformat()
        return cls.save_config(config)
    
    @classmethod
    def get_last_username(cls) -> Optional[str]:
        """Obtiene el último usuario recordado"""
        config = cls.load_config()
        return config.get('ui', {}).get('last_username')
    
    @classmethod
    def set_last_username(cls, username: str, remember: bool = False) -> bool:
        """Guarda el último usuario si está habilitado recordar"""
        config = cls.load_config()
        config['ui']['remember_username'] = remember
        if remember:
            config['ui']['last_username'] = username
        else:
            config['ui']['last_username'] = None
        config['last_login'] = datetime.now().isoformat()
        return cls.save_config(config)
    
    @classmethod
    def get_app_config(cls) -> Dict[str, Any]:
        """Obtiene toda la configuración"""
        return cls.load_config()
    
    @classmethod
    def update_config(cls, key: str, value: Any) -> bool:
        """Actualiza una clave específica"""
        config = cls.load_config()
        config[key] = value
        return cls.save_config(config)
