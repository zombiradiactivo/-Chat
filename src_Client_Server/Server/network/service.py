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
from enum import Enum
from datetime import datetime, date

from src_Client_Server.Server.utils.config_manager import ConfigManager
from src_Client_Server.Server.utils.logger import setup_logger
logger = setup_logger(__name__)

class EnumEncoder(json.JSONEncoder):
    """Encoder para manejar enums, datetime y otros tipos en JSON"""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def _serialize_for_json(obj):
    """Convierte objetos a formato JSON-serializable - recursiva y robusta"""
    if obj is None:
        return None
    elif isinstance(obj, bool):  # Verificar antes de int porque bool es subclass de int
        return obj
    elif isinstance(obj, (int, float, str)):
        return obj
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Es un objeto personalizado, convertir su __dict__
        return _serialize_for_json(obj.__dict__)
    else:
        # Como último recurso, convertir a string
        return str(obj)

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
        msg_dict = asdict(self)
        msg_dict['data'] = _serialize_for_json(msg_dict['data'])
        return json.dumps(msg_dict, cls=EnumEncoder)
    
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
    
    def start(self,host: str = '0.0.0.0', port: int = 5555):
        """Inicia el servidor"""
        logger.info("Inicializando TCPServer")

        if self.running:
            logger.info("TCPServer ya está corriendo")
            return
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(10)
        self.running = True
        
        self.server_thread = threading.Thread(target=self._accept_connections, daemon=True)
        self.server_thread.start()
        
        # Thread para procesar mensajes
        threading.Thread(target=self._process_messages, daemon=True).start()
        threading.Thread(target=self._accept_connections, daemon=True).start()
    
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
        """Procesa mensajes de la cola y los enruta a handlers específicos"""
        while self.running:
            try:
                client_id, message = self.message_queue.get(timeout=0.1)
                # Enrutar mensaje según su tipo
                self._handle_message(client_id, message)
                self._notify_callbacks('message', {
                    'sender_id': client_id,
                    'message': message
                })
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing message: {e}")
    
    def _handle_message(self, client_id: str, message: NetworkMessage):
        """Enruta los mensajes a handlers específicos según el tipo"""
        try:
            # Importar los servicios necesarios aquí para evitar dependencias circulares
            from src_Client_Server.Server.repositories import RepositoryFactory
            from src_Client_Server.Server.services.server_service import ServerService
            from src_Client_Server.Server.services.auth_service import AuthService
            
            repo_factory = RepositoryFactory()
            
            logger.info(f"Mensaje recibido: {message}, de user id {client_id}")

            # Enrutar según tipo de mensaje
            if message.type == "get_server":
                self._handle_get_server(client_id, message, repo_factory)
            elif message.type == "update_server":
                self._handle_update_server(client_id, message, repo_factory)
            elif message.type == "get_user_servers":
                self._handle_get_user_servers(client_id, message, repo_factory)
            elif message.type == "get_server_channels":
                self._handle_get_server_channels(client_id, message, repo_factory)
            elif message.type == "get_channel_messages":
                self._handle_get_channel_messages(client_id, message, repo_factory)
            elif message.type == "create_channel":
                self._handle_create_channel(client_id, message, repo_factory)
            elif message.type == "delete_channel":
                self._handle_delete_channel(client_id, message, repo_factory)
            elif message.type == "create_server":
                self._handle_create_server(client_id, message, repo_factory)
            elif message.type == "login":
                self._handle_login(client_id, message, repo_factory)
            elif message.type == "register":
                self._handle_register(client_id, message, repo_factory)
            elif message.type == "get_server_roles":
                self._handle_get_server_roles(client_id, message, repo_factory)
            elif message.type == "create_role":
                self._handle_create_role(client_id, message, repo_factory)
            elif message.type == "update_role":
                self._handle_update_role(client_id, message, repo_factory)
            elif message.type == "delete_role":
                self._handle_delete_role(client_id, message, repo_factory)
            elif message.type == "reorder_roles":
                self._handle_reorder_roles(client_id, message, repo_factory)
            elif message.type == "check_permission":
                self._handle_check_permission(client_id, message, repo_factory)
            elif message.type == "send_message":
                self._handle_send_message(client_id, message, repo_factory)
            else:
                print(f"Error handling message type {message.type}")

        except Exception as e:
            print(f"Error handling message type {message.type}: {e}")
    
    def _handle_get_server(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de obtener servidor"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            server_id = message.data.get("server_id")
            server = server_service.get_server(server_id)
            
            if server:
                server_data = _serialize_for_json(server.dict())
                response = NetworkMessage(
                    type="get_server_response",
                    data={"success": True, "server": server_data},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="get_server_response",
                    data={"success": False, "error": "Servidor no encontrado"},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="get_server_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_update_server(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de actualizar servidor"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            
            # Extraer el resto de los datos
            update_data = {k: v for k, v in message.data.items() if k not in ["server_id", "user_id"]}
            
            success, error, updated_server = server_service.update_server(
                server_id, user_id, **update_data
            )
            
            if success:
                server_data = _serialize_for_json(updated_server.dict())
                response = NetworkMessage(
                    type="update_server_response",
                    data={"success": True, "server": server_data},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="update_server_response",
                    data={"success": False, "error": error},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="update_server_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_get_user_servers(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de obtener servidores del usuario"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            user_id = message.data.get("user_id")
            servers = server_service.get_user_servers(user_id)
            
            # Serializar servers correctamente
            servers_data = [_serialize_for_json(s.dict()) if hasattr(s, 'dict') else _serialize_for_json(s) for s in servers]
            
            response = NetworkMessage(
                type="get_user_servers_response",
                data={"success": True, "servers": servers_data},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            print(f"[GET_USER_SERVERS ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            response = NetworkMessage(
                type="get_user_servers_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_get_server_channels(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de obtener canales del servidor"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            server_id = message.data.get("server_id")
            channels = server_service.get_server_channels(server_id)
            

            if channels:
                channels_data = [_serialize_for_json(c.dict()) if hasattr(c, 'dict') else _serialize_for_json(c) for c in channels]
                response = NetworkMessage(
                    type="get_server_channels_response",
                    data={"success": True, "channels": channels_data},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="get_server_channels_response",
                    data={"success": False, "error": "Canal no encontrado"},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="get_server_channels_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    

    def _handle_get_channel_messages(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de obtener mensajes de un canal"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            from src_Client_Server.Server.services.message_service import MessageService
            server_service = ServerService(repo_factory)
            message_service = MessageService(repo_factory)

            channel_id = message.data.get("channel_id")

            logger.info(f"Solicitando mensajes para el canal: {channel_id}")

            messages = message_service.get_channel_messages(channel_id)
            # Cambiamos la validación: 
            # Si 'messages' es None, podrías considerar que el canal no existe.
            # Si 'messages' es una lista (aunque sea []), es un éxito.
            if messages is not None:
                channels_messages_data = [
                    _serialize_for_json(m.dict()) if hasattr(m, 'dict') else _serialize_for_json(m) 
                    for m in messages
                ]
                
                response = NetworkMessage(
                    type="get_channel_messages_response",
                    data={"success": True, "messages": channels_messages_data},
                    sender_id="server"
                )
            else:
                # Esto solo ocurre si el servicio indica que el canal NO existe
                response = NetworkMessage(
                    type="get_channel_messages_response",
                    data={"success": False, "error": "El canal especificado no existe"},
                    sender_id="server"
                )

            self.send(client_id, response)
            logger.info(f"Respuesta enviada a {client_id}: {response} (Mensajes: {len(channels_messages_data) if messages else 0})")

        except Exception as e:
            logger.error(f"Error en _handle_get_channel_messages: {str(e)}")
            response = NetworkMessage(
                type="get_channel_messages_response", # Corregido el tipo (tenías get_server_channels_response)
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)


    def _handle_create_channel(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de crear canal"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            server_id = message.data.get("server_id")
            channel_name = message.data.get("channel_name")
            user_id = message.data.get("user_id")
            
            success, error, channel = server_service.create_channel(
                server_id, channel_name, user_id
            )
            
            if success:
                channel_data = _serialize_for_json(channel.dict())
                response = NetworkMessage(
                    type="create_channel_response",
                    data={"success": True, "channel": channel_data},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="create_channel_response",
                    data={"success": False, "error": error},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="create_channel_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_delete_channel(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de eliminar canal"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            
            success, error = server_service.delete_channel(channel_id, user_id)
            
            response = NetworkMessage(
                type="delete_channel_response",
                data={"success": success, "error": error or ""},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="delete_channel_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    

    def _handle_create_server(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de crear canal"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            from ..models.enums import ConnectionType, SecurityLevel
            server_service = ServerService(repo_factory)
            
            user_id = message.data.get("user_id")
            
            # Extraer y convertir datos del servidor
            server_data = {}
            for key, value in message.data.items():
                if key == "connection_type" and isinstance(value, str):
                    server_data[key] = ConnectionType(value)
                elif key == "security_level" and isinstance(value, str):
                    server_data[key] = SecurityLevel(value)
                elif key not in ["user_id"]:
                    server_data[key] = value

            logger.info(f"Creando servidor de : {user_id}")

            success, error, server = server_service.create_server(user_id, **server_data)
            
            if success:
                server_data = _serialize_for_json(server.dict())
                response = NetworkMessage(
                    type="create_server_response",
                    data={"success": True, "server": server_data},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="create_server_response",
                    data={"success": False, "error": error},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="create_server_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")


    def _handle_send_message(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja enviar mensajes a un canal"""
        try:
            from src_Client_Server.Server.services.message_service import MessageService
            from src_Client_Server.Server.repositories import RepositoryFactory
            message_service = MessageService(repo_factory)

            logger.info(f"Creando mensaje de : {client_id}")

            # ERROR CORREGIDO: Usamos message.data que es el diccionario
            success, error, created_message = message_service.send_message(**message.data)
            
            if success:
                # Serializamos el objeto mensaje si es necesario
                message_dict = _serialize_for_json(created_message.dict()) if hasattr(created_message, 'dict') else _serialize_for_json(created_message)
                
                response = NetworkMessage(
                    type="send_message_response",
                    data={"success": True, "message": message_dict},
                    sender_id="server"
                )
                self.send(client_id, response)
                logger.info(f"Respuesta enviada a {client_id}")
                
                # BROADCAST: Enviar el mensaje a todos los clientes conectados al mismo servidor (excluyendo al autor)
                # Obtener el canal del mensaje
                channel = message_service.channels_repo.get_by_id(message.data.get('channel_id'))
                if channel:
                    server = repo_factory.get_repository('servers').get_by_id(channel.server_id)
                    if server:
                        # Crear mensaje de broadcast con el canal y servidor
                        broadcast_msg_dict = {
                            "type": "message_broadcast",
                            "data": {
                                "message": message_dict,
                                "channel_id": channel.id,
                                "server_id": server.id
                            },
                            "sender_id": "server"
                        }
                        
                        # Enviar a todos los clientes conectados al mismo servidor (excluyendo al autor)
                        with self.lock:
                            for connected_client_id in list(self.clients.keys()):
                                if connected_client_id != client_id:  # Excluir al autor
                                    try:
                                        broadcast_msg_json = json.dumps(broadcast_msg_dict)
                                        self.clients[connected_client_id].send(broadcast_msg_json.encode())
                                        logger.info(f"Broadcast de mensaje a {connected_client_id} para canal {channel.id}")
                                    except Exception as e:
                                        logger.error(f"Error enviando broadcast a {connected_client_id}: {e}")
            else:
                response = NetworkMessage(
                    type="send_message_response",
                    data={"success": False, "error": error},
                    sender_id="server"
                )
                self.send(client_id, response)

        except Exception as e:
            logger.error(f"Error en _handle_send_message: {e}")
            response = NetworkMessage(
                type="send_message_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_login(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de login"""
        try:
            from src_Client_Server.Server.services.auth_service import AuthService
            auth_service = AuthService(repo_factory)
            
            email = message.data.get("email")
            password = message.data.get("password")
            
            print(f"[LOGIN] Attempting login with email: {email}")
            
            # El orden de retorno es (success, error, user)
            success, error, user = auth_service.login(email, password)
            
            print(f"[LOGIN] Result - Success: {success}, Error: {error}, User type: {type(user)}")
            
            if success and user:
                try:
                    user_dict = user.dict() if hasattr(user, 'dict') else user.__dict__
                    # Convertir enums a valores
                    if 'status' in user_dict:
                        user_dict['status'] = user_dict['status'].value if hasattr(user_dict['status'], 'value') else user_dict['status']
                    print(f"[LOGIN] User converted to dict successfully")
                except Exception as e:
                    print(f"[LOGIN] Error converting user to dict: {e}")
                    import traceback
                    traceback.print_exc()
                    user_dict = None
            else:
                user_dict = None
            
            if success and user_dict:
                response = NetworkMessage(
                    type="login_response",
                    data={"success": True, "user": user_dict},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="login_response",
                    data={"success": False, "error": error or "Usuario no encontrado"},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            print(f"[LOGIN ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            response = NetworkMessage(
                type="login_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_register(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de registro"""
        try:
            from src_Client_Server.Server.services.auth_service import AuthService
            auth_service = AuthService(repo_factory)
            
            email = message.data.get("email")
            password = message.data.get("password")
            username = message.data.get("username")
            
            print(f"[REGISTER] Attempting registration with username: {username}, email: {email}")
            
            # El orden de retorno es (success, error, user)
            success, error, user = auth_service.register(username, email, password)
            
            print(f"[REGISTER] Result - Success: {success}, Error: {error}, User type: {type(user)}")
            
            if success and user:
                try:
                    user_dict = user.dict() if hasattr(user, 'dict') else user.__dict__
                    # Convertir enums a valores
                    if 'status' in user_dict:
                        user_dict['status'] = user_dict['status'].value if hasattr(user_dict['status'], 'value') else user_dict['status']
                    print(f"[REGISTER] User converted to dict successfully")
                except Exception as e:
                    print(f"[REGISTER] Error converting user to dict: {e}")
                    user_dict = None
            else:
                user_dict = None
            
            if success and user_dict:
                response = NetworkMessage(
                    type="register_response",
                    data={"success": True, "user": user_dict},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="register_response",
                    data={"success": False, "error": error or "Error en registro"},
                    sender_id="server"
                )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            print(f"[REGISTER ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            response = NetworkMessage(
                type="register_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_get_server_roles(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de obtener roles del servidor"""
        try:
            server_id = message.data.get("server_id")
            roles_repo = repo_factory.get_repository('roles')
            roles = roles_repo.get_by_server(server_id)
            roles.sort(key=lambda r: r.position)
            
            roles_data = [_serialize_for_json(r.dict()) if hasattr(r, 'dict') else _serialize_for_json(r) for r in roles]
            response = NetworkMessage(
                type="get_roles_response",
                data={"success": True, "roles": roles_data},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="get_roles_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_create_role(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de crear rol"""
        try:
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            
            # Verificar permisos
            server_service = __import__('src_Client_Server.Server.services.server_service', fromlist=['ServerService']).ServerService(repo_factory)
            server = server_service.get_server(server_id)
            if not server or server.owner_id != user_id:
                response = NetworkMessage(
                    type="create_role_response",
                    data={"success": False, "error": "Sin permisos"},
                    sender_id="server"
                )
                self.send(client_id, response)
                logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
                return
            
            # Crear rol
            roles_repo = repo_factory.get_repository('roles')
            role_data = {
                "server_id": server_id,
                "name": message.data.get("name"),
                "color": message.data.get("color", "#99AAB5"),
                "permissions": message.data.get("permissions", []),
                "mentionable": message.data.get("mentionable", False),
                "hoisted": message.data.get("hoisted", False),
                "position": len(roles_repo.get_by_server(server_id))
            }
            created_role = roles_repo.create(role_data)
            
            response = NetworkMessage(
                type="create_role_response",
                data={"success": True, "role": _serialize_for_json(created_role.dict()) if hasattr(created_role, 'dict') else _serialize_for_json(created_role)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="create_role_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_update_role(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de actualizar rol"""
        try:
            role_id = message.data.get("id")
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            
            # Verificar permisos
            server_service = __import__('src_Client_Server.Server.services.server_service', fromlist=['ServerService']).ServerService(repo_factory)
            server = server_service.get_server(server_id)
            if not server or server.owner_id != user_id:
                response = NetworkMessage(
                    type="update_role_response",
                    data={"success": False, "error": "Sin permisos"},
                    sender_id="server"
                )
                self.send(client_id, response)
                logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
                return
            
            # Actualizar rol
            roles_repo = repo_factory.get_repository('roles')
            update_data = {k: v for k, v in message.data.items() 
                          if k not in ["id", "server_id", "user_id"]}
            updated_role = roles_repo.update(role_id, update_data)
            
            response = NetworkMessage(
                type="update_role_response",
                data={"success": True, "role": _serialize_for_json(updated_role.dict()) if hasattr(updated_role, 'dict') else _serialize_for_json(updated_role)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="update_role_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_delete_role(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja solicitud de eliminar rol"""
        try:
            role_id = message.data.get("role_id")
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            
            # Verificar permisos
            server_service = __import__('src_Client_Server.Server.services.server_service', fromlist=['ServerService']).ServerService(repo_factory)
            server = server_service.get_server(server_id)
            if not server or server.owner_id != user_id:
                response = NetworkMessage(
                    type="delete_role_response",
                    data={"success": False, "error": "Sin permisos"},
                    sender_id="server"
                )
                self.send(client_id, response)
                logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
                return
            
            # Eliminar rol
            roles_repo = repo_factory.get_repository('roles')
            success = roles_repo.delete(role_id)
            
            response = NetworkMessage(
                type="delete_role_response",
                data={"success": success, "error": "" if success else "Error al eliminar"},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="delete_role_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_reorder_roles(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja reordenación de roles"""
        try:
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            positions = message.data.get("positions", {})
            
            # Verificar permisos
            server_service = __import__('src_Client_Server.Server.services.server_service', fromlist=['ServerService']).ServerService(repo_factory)
            server = server_service.get_server(server_id)
            if not server or server.owner_id != user_id:
                response = NetworkMessage(
                    type="reorder_roles_response",
                    data={"success": False, "error": "Sin permisos"},
                    sender_id="server"
                )
                self.send(client_id, response)
                logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
                return
            
            # Reordenar roles
            roles_repo = repo_factory.get_repository('roles')
            for role_id, position in positions.items():
                roles_repo.update(role_id, {"position": position})
            
            response = NetworkMessage(
                type="reorder_roles_response",
                data={"success": True},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="reorder_roles_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
    def _handle_check_permission(self, client_id: str, message: NetworkMessage, repo_factory):
        """Verifica si el usuario tiene un permiso específico"""
        try:
            user_id = message.data.get("user_id")
            server_id = message.data.get("server_id")
            permission = message.data.get("permission")
            
            # Verificar permisos
            permission_service = __import__('src_Client_Server.Server.services.permission_service', fromlist=['PermissionService']).PermissionService(repo_factory)
            server_service = __import__('src_Client_Server.Server.services.server_service', fromlist=['ServerService']).ServerService(repo_factory)
            
            # Dueño siempre tiene permisos
            server = server_service.get_server(server_id)
            is_owner = server and server.owner_id == user_id
            
            # Verificar permiso
            has_perm = is_owner or permission_service.has_permission(user_id, server_id, permission)
            
            response = NetworkMessage(
                type="check_permission_response",
                data={"success": has_perm},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
        except Exception as e:
            response = NetworkMessage(
                type="check_permission_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Mensaje de respuesta a {client_id} , response: {response}")
    
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
                    logger.info(f"Logger de eventos: Tipo: {event_type} , Datos: {data}")
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
        raise NotImplementedError
    
    def stop(self):
        raise NotImplementedError
    