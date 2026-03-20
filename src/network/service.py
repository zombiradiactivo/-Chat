"""
Servicio de red para comunicación P2P y cliente-servidor
"""
import socket
import threading
import json
import time
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import queue


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



class TCPServer(NetworkService):
    """Servidor TCP para modo cliente-servidor"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[str, socket.socket] = {}
        self.running = False
        self.message_queue = queue.Queue()
        self.callbacks: Dict[str, List[Callable]] = {}
        self.lock = threading.RLock()
        self.server_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Inicia el servidor"""
        if self.running:
            return
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True
        
        self.server_thread = threading.Thread(target=self._accept_connections, daemon=True)
        self.server_thread.start()
        
        # Thread para procesar mensajes
        threading.Thread(target=self._process_messages, daemon=True).start()
    
    def stop(self):
        """Detiene el servidor"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        with self.lock:
            for client_socket in self.clients.values():
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
    
    def _accept_connections(self):
        """Acepta conexiones entrantes"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_id = f"{addr[0]}:{addr[1]}"
                
                with self.lock:
                    self.clients[client_id] = client_socket
                
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_id),
                    daemon=True
                ).start()
                
                self._notify_callbacks('client_connected', {'client_id': client_id, 'address': addr})
                
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_id: str):
        """Maneja un cliente"""
        try:
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    message = NetworkMessage.from_json(data.decode())
                    self.message_queue.put((client_id, message))
                    
                except Exception as e:
                    print(f"Error receiving from {client_id}: {e}")
                    break
        finally:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
            try:
                client_socket.close()
            except:
                pass
            self._notify_callbacks('client_disconnected', {'client_id': client_id})
    
    def _process_messages(self):
        """Procesa mensajes de la cola"""
        while self.running:
            try:
                client_id, message = self.message_queue.get(timeout=0.1)
                self._notify_callbacks('message', {
                    'sender_id': client_id,
                    'message': message
                })
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing message: {e}")
    
    def send(self, target_id: str, message: NetworkMessage) -> bool:
        """Envía un mensaje a un cliente específico"""
        with self.lock:
            if target_id in self.clients:
                try:
                    self.clients[target_id].send(message.to_json().encode())
                    return True
                except Exception as e:
                    print(f"Error sending to {target_id}: {e}")
                    return False
        return False
    
    def broadcast(self, message: NetworkMessage, exclude: Optional[List[str]] = None):
        """Envía un mensaje a todos los clientes"""
        exclude = exclude or []
        with self.lock:
            for client_id, client_socket in self.clients.items():
                if client_id not in exclude:
                    try:
                        client_socket.send(message.to_json().encode())
                    except Exception as e:
                        print(f"Error broadcasting to {client_id}: {e}")
    
    def is_connected(self) -> bool:
        """Verifica si el servidor está corriendo"""
        return self.running and self.server_socket is not None
    
    def get_connected_clients(self) -> List[str]:
        """Obtiene la lista de clientes conectados"""
        with self.lock:
            return list(self.clients.keys())
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback para un tipo de evento"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notifica a los callbacks registrados"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in callback: {e}")


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
    
    def connect(self, host: str, port: int = 5555) -> bool:
        """Se conecta a un servidor"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.running = True
            self.server_address = (host, port)
            
            self.receiver_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receiver_thread.start()
            
            return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
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
