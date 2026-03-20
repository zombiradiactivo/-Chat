"""
Repositorio base abstracto
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from datetime import datetime


class Repository(ABC):
    """Clase base para todos los repositorios"""
    
    @abstractmethod
    def initialize(self):
        """Inicializa la base de datos/tablas"""
        pass
    
    @abstractmethod
    def close(self):
        """Cierra la conexión a la base de datos"""
        pass


class CRUDRepository(Repository):
    """Repositorio con operaciones CRUD básicas"""
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> str:
        """Crea un nuevo registro y devuelve su ID"""
        pass
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un registro por su ID"""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """Obtiene todos los registros"""
        pass
    
    @abstractmethod
    def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Actualiza un registro"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Elimina un registro"""
        pass
