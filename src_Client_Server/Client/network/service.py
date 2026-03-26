"""
Servicio de red para comunicación cliente-servidor (solo cliente)
"""
import socket
import threading
import json
import time
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import queue

from src_Client_Server.Client.utils.config_manager import ConfigManager
from src_Client_Server.Client.utils.logger import setup_logger
logger = setup_logger(__name__)

@dataclass
class NetworkMessage:
    """Mensaje de red estandarizado"""
    type: str
    data: Dict[str, Any]
    sender_id: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_json(self) -> str:
        """Convierte el mensaje a JSON"""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NetworkMessage':
        """Crea un mensaje desde JSON"""
        data = json.loads(json_str)
        return cls(**data)


class NetworkService(ABC):
    """Clase base para servicios de red"""
    
    @abstractmethod
    def start(self):
        """Inicia el servicio de red"""
        pass
    
    @abstractmethod
    def stop(self):
        """Detiene el servicio de red"""
        pass
    
    @abstractmethod
    def send(self, target_id: str, message: NetworkMessage) -> bool:
        """Envía un mensaje a un destino"""
        pass
    
    @abstractmethod
    def broadcast(self, message: NetworkMessage, exclude: Optional[List[str]] = None):
        """Envía un mensaje a todos los conectados"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica si está conectado"""
        pass
    
    @abstractmethod
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback para un tipo de evento"""
        pass


class TCPClient(NetworkService):
    """Cliente TCP para conectarse a un servidor"""
    
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.message_queue = queue.Queue()
        self.callbacks: Dict[str, List[Callable]] = {}
        self.receiver_thread: Optional[threading.Thread] = None
        self.server_address: Optional[tuple] = None
        self.server_host, self.server_port = ConfigManager.get_server_config()
    
    def connect(self, server_host: str, server_port: int = 5555) -> bool:
        """Se conecta a un servidor"""
        logger.info("Inicializando TCPClient")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((server_host, server_port))
            self.connected = True
            self.running = True
            self.server_address = (server_host, server_port)
            logger.info(f"Connected to server at {server_host}:{server_port}")
            self.receiver_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receiver_thread.start()
            
            return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
            logger.info(f"Error connecting to server: {e}")
            return False
    
    def disconnect(self):
        """Se desconecta del servidor"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def _receive_messages(self):
        """Recibe mensajes del servidor"""
        while self.running and self.socket:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                message = NetworkMessage.from_json(data.decode())
                self.message_queue.put(message)
                
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break
        
        self.connected = False
        self._notify_callbacks('disconnected', {})
    
    def send(self, message: NetworkMessage) -> bool:
        """Envía un mensaje al servidor"""
        if not self.connected or not self.socket:
            return False
        try:
            self.socket.send(message.to_json().encode())
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            return False
    
    def broadcast(self, message: NetworkMessage, exclude: Optional[List[str]] = None):
        """No implementado en cliente (solo envía al servidor)"""
        self.send(message)
    
    def is_connected(self) -> bool:
        """Verifica si está conectado"""
        return self.connected
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def start_processing(self):
        """Inicia el procesamiento de mensajes en el hilo actual"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=0.1)
                self._notify_callbacks('message', {'message': message})
            except queue.Empty:
                continue
    
    def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notifica a los callbacks"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in callback: {e}")

    def start(self):
        """Inicia el cliente (no hace nada ya que la conexión se establece con connect)"""
        pass

    def stop(self):
        """Detiene el cliente desconectándolo del servidor"""
        self.disconnect()

