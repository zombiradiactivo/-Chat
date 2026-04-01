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
        """Maneja un cliente con protocolo de longitud prefijada"""
        try:
            while self.running:
                try:
                    # Leer primero los 4 bytes de longitud
                    header = self._recv_exact(client_socket, 4)
                    if not header:
                        break
                    
                    msg_length = int.from_bytes(header, 'big')
                    
                    # Limitar tamaño máximo de mensaje (10MB)
                    if msg_length > 10 * 1024 * 1024:
                        print(f"Mensaje demasiado grande de {client_id}: {msg_length} bytes")
                        break
                    
                    # Leer el mensaje completo
                    data = self._recv_exact(client_socket, msg_length)
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
    
    def _recv_exact(self, sock: socket.socket, num_bytes: int) -> bytes:
        """Lee exactamente num_bytes del socket"""
        data = b''
        while len(data) < num_bytes:
            chunk = sock.recv(num_bytes - len(data))
            if not chunk:
                return b''
            data += chunk
        return data
    
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
            elif message.type == "get_server_members":
                self._handle_get_server_members(client_id, message, repo_factory)
            elif message.type == "create_invite":
                self._handle_create_invite(client_id, message, repo_factory)
            elif message.type == "accept_invite":
                self._handle_accept_invite(client_id, message, repo_factory)
            elif message.type == "get_server_invites":
                self._handle_get_server_invites(client_id, message, repo_factory)
            elif message.type == "revoke_invite":
                self._handle_revoke_invite(client_id, message, repo_factory)
            elif message.type == "upload_file":
                self._handle_upload_file(client_id, message, repo_factory)
            elif message.type == "download_file":
                self._handle_download_file(client_id, message, repo_factory)
            elif message.type == "assign_role":
                self._handle_assign_role(client_id, message, repo_factory)
            elif message.type == "remove_role":
                self._handle_remove_role(client_id, message, repo_factory)
            elif message.type == "video_frame":
                self._handle_video_frame(client_id, message, repo_factory)
            elif message.type == "start_call":
                self._handle_start_call(client_id, message, repo_factory)
            elif message.type == "join_call":
                self._handle_join_call(client_id, message, repo_factory)
            elif message.type == "leave_call":
                self._handle_leave_call(client_id, message, repo_factory)
            elif message.type == "screen_share_start":
                self._handle_screen_share_start(client_id, message, repo_factory)
            elif message.type == "screen_share_stop":
                self._handle_screen_share_stop(client_id, message, repo_factory)
            elif message.type == "screen_frame":
                self._handle_screen_frame(client_id, message, repo_factory)
            elif message.type == "audio_frame":
                self._handle_audio_frame(client_id, message, repo_factory)
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
            limit = message.data.get("limit", 10)
            before = message.data.get("before")
            
            # Limitar a máximo 30 mensajes por petición
            limit = min(limit, 30)

            logger.info(f"Solicitando mensajes para el canal: {channel_id}, limit: {limit}, before: {before}")

            messages = message_service.get_channel_messages(channel_id, limit=limit, before=before)
            if messages is not None:
                channels_messages_data = [
                    _serialize_for_json(m.dict()) if hasattr(m, 'dict') else _serialize_for_json(m) 
                    for m in messages
                ]
                
                response = NetworkMessage(
                    type="get_channel_messages_response",
                    data={
                        "success": True,
                        "messages": channels_messages_data,
                        "has_more": len(channels_messages_data) >= limit
                    },
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
            from src_Client_Server.Server.models.enums import ChannelType
            server_service = ServerService(repo_factory)
            
            server_id = message.data.get("server_id")
            # Soportar ambos nombres de campo (channel_name o name)
            channel_name = message.data.get("channel_name") or message.data.get("name")
            user_id = message.data.get("user_id") or message.data.get("creator_id")
            channel_type = message.data.get("type", "text")
            
            # Convertir tipo de canal a enum si es string
            if isinstance(channel_type, str):
                channel_type = ChannelType(channel_type)
            
            success, error, channel = server_service.create_channel(
                server_id, user_id,
                name=channel_name,
                type=channel_type,
                topic=message.data.get("topic"),
                is_private=message.data.get("is_private", False)
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
            from src_Client_Server.Server.services.permission_service import PermissionService
            from src_Client_Server.Server.repositories import RepositoryFactory
            message_service = MessageService(repo_factory)
            permission_service = PermissionService()

            logger.info(f"Creando mensaje de : {client_id}")

            # Verificar permisos de envío
            channel_id = message.data.get('channel_id')
            author_id = message.data.get('author_id')
            
            if not permission_service.can_send_message(author_id, channel_id):
                response = NetworkMessage(
                    type="send_message_response",
                    data={"success": False, "error": "No tienes permisos para enviar mensajes en este canal"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return

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
                        broadcast_msg = NetworkMessage(
                            type= "message_broadcast",
                            data= {
                                "message": message_dict,
                                "channel_id": channel.id,
                                "server_id": server.id
                            },
                            sender_id= "server"
                        )
                        
                        # Enviar a todos los clientes conectados al mismo servidor (excluyendo al autor)
                        with self.lock:
                            for connected_client_id in list(self.clients.keys()):
                                if connected_client_id != client_id:  # Excluir al autor
                                    try:
                                        # broadcast_msg_json = json.dumps(broadcast_msg)
                                        self.send(connected_client_id, broadcast_msg)
                                        logger.info(f"Broadcast de mensaje a {connected_client_id} para canal {channel.id}")
                                    except Exception as e:
                                        logger.error(f"Error enviando broadcast a {client_id}: {e}")
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
    
    def _handle_get_server_members(self, client_id: str, message: NetworkMessage, repo_factory):
        """Obtiene los miembros de un servidor con su información de usuario y roles"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            server_service = ServerService(repo_factory)
            
            server_id = message.data.get("server_id")
            members_data = server_service.get_server_members(server_id)
            
            serialized_members = []
            for m in members_data:
                serialized_members.append(_serialize_for_json(m))
            
            response = NetworkMessage(
                type="get_server_members_response",
                data={"success": True, "members": serialized_members},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Miembros enviados a {client_id}: {len(serialized_members)} miembros")
        except Exception as e:
            response = NetworkMessage(
                type="get_server_members_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.error(f"Error en _handle_get_server_members: {e}")

    def _handle_create_invite(self, client_id: str, message: NetworkMessage, repo_factory):
        """Crea un codigo de invitacion para un servidor"""
        try:
            from src_Client_Server.Server.services.invite_service import InviteService
            from src_Client_Server.Server.services.server_service import ServerService
            
            server_service = ServerService(repo_factory)
            invite_service = InviteService(repo_factory)
            
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            max_uses = message.data.get("max_uses")
            expires_in_hours = message.data.get("expires_in_hours")
            
            server = server_service.get_server(server_id)
            if not server:
                response = NetworkMessage(
                    type="create_invite_response",
                    data={"success": False, "error": "Servidor no encontrado"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            success, error, invite = invite_service.create_invite(
                server_id, user_id, max_uses, expires_in_hours
            )
            
            if success:
                invite_data = _serialize_for_json(invite.to_dict() if hasattr(invite, 'to_dict') else invite.dict())
                response = NetworkMessage(
                    type="create_invite_response",
                    data={"success": True, "invite": invite_data},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="create_invite_response",
                    data={"success": False, "error": error},
                    sender_id="server"
                )
            self.send(client_id, response)
        except Exception as e:
            response = NetworkMessage(
                type="create_invite_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_accept_invite(self, client_id: str, message: NetworkMessage, repo_factory):
        """Acepta un codigo de invitacion y une al usuario al servidor"""
        try:
            from src_Client_Server.Server.services.invite_service import InviteService
            invite_service = InviteService(repo_factory)
            
            user_id = message.data.get("user_id")
            code = message.data.get("code")
            
            success, error, server_data = invite_service.accept_invite(user_id, code)
            
            if success:
                serialized_server = _serialize_for_json(server_data)
                response = NetworkMessage(
                    type="accept_invite_response",
                    data={"success": True, "server": serialized_server},
                    sender_id="server"
                )
            else:
                response = NetworkMessage(
                    type="accept_invite_response",
                    data={"success": False, "error": error},
                    sender_id="server"
                )
            self.send(client_id, response)
        except Exception as e:
            response = NetworkMessage(
                type="accept_invite_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_get_server_invites(self, client_id: str, message: NetworkMessage, repo_factory):
        """Obtiene las invitaciones de un servidor"""
        try:
            from src_Client_Server.Server.services.invite_service import InviteService
            invite_service = InviteService(repo_factory)
            
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            
            invites = invite_service.get_server_invites(server_id, user_id)
            invites_data = [_serialize_for_json(i.to_dict() if hasattr(i, 'to_dict') else i.dict()) for i in invites]
            
            response = NetworkMessage(
                type="get_server_invites_response",
                data={"success": True, "invites": invites_data},
                sender_id="server"
            )
            self.send(client_id, response)
        except Exception as e:
            response = NetworkMessage(
                type="get_server_invites_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_revoke_invite(self, client_id: str, message: NetworkMessage, repo_factory):
        """Revoca una invitacion"""
        try:
            from src_Client_Server.Server.services.invite_service import InviteService
            invite_service = InviteService(repo_factory)
            
            invite_id = message.data.get("invite_id")
            user_id = message.data.get("user_id")
            
            success, error = invite_service.revoke_invite(invite_id, user_id)
            
            response = NetworkMessage(
                type="revoke_invite_response",
                data={"success": success, "error": error or ""},
                sender_id="server"
            )
            self.send(client_id, response)
        except Exception as e:
            response = NetworkMessage(
                type="revoke_invite_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_upload_file(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja la subida de un archivo"""
        try:
            import os
            import base64
            import hashlib
            import uuid
            import mimetypes
            
            file_data_b64 = message.data.get("file_data")
            filename = message.data.get("filename")
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            
            if not file_data_b64 or not filename:
                response = NetworkMessage(
                    type="upload_file_response",
                    data={"success": False, "error": "Datos de archivo incompletos"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            file_bytes = base64.b64decode(file_data_b64)
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            file_size = len(file_bytes)
            mime_type, _ = mimetypes.guess_type(filename)
            file_type = mime_type or 'application/octet-stream'
            
            upload_dir = os.path.join("data", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            
            file_id = str(uuid.uuid4())
            ext = os.path.splitext(filename)[1]
            safe_filename = f"{file_id}{ext}"
            filepath = os.path.join(upload_dir, safe_filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_bytes)
            
            file_transfer_repo = repo_factory.get_repository('file_transfers')
            total_chunks = 1
            transfer_data = {
                'channel_id': channel_id,
                'sender_id': user_id,
                'filename': filename,
                'file_size': file_size,
                'file_type': file_type,
                'file_hash': file_hash,
                'encrypted': False,
                'chunk_size': file_size,
                'total_chunks': total_chunks,
                'uploaded_chunks': total_chunks,
                'download_url': safe_filename
            }
            transfer_id = file_transfer_repo.create(transfer_data)
            
            from src_Client_Server.Server.services.message_service import MessageService
            from src_Client_Server.Server.models.enums import MessageType
            message_service = MessageService(repo_factory)
            
            attachment_data = {
                'transfer_id': transfer_id,
                'filename': filename,
                'file_size': file_size,
                'file_type': file_type,
                'file_hash': file_hash,
                'download_url': safe_filename
            }
            
            success, error, msg = message_service.send_message(
                content=f"[Archivo] {filename}",
                channel_id=channel_id,
                author_id=user_id,
                message_type=MessageType.FILE,
                attachments=[attachment_data]
            )
            
            response = NetworkMessage(
                type="upload_file_response",
                data={
                    "success": True,
                    "transfer_id": transfer_id,
                    "filename": filename,
                    "file_hash": file_hash,
                    "download_url": safe_filename
                },
                sender_id="server"
            )
            self.send(client_id, response)
            
            if success and msg:
                msg_dict = _serialize_for_json(msg.dict())
                channel = message_service.channels_repo.get_by_id(channel_id)
                if channel:
                    broadcast_msg = NetworkMessage(
                        type="message_broadcast",
                        data={
                            "message": msg_dict,
                            "channel_id": channel_id,
                            "server_id": channel.server_id
                        },
                        sender_id="server"
                    )
                    with self.lock:
                        for connected_client_id in list(self.clients.keys()):
                            if connected_client_id != client_id:
                                try:
                                    self.send(connected_client_id, broadcast_msg)
                                except Exception:
                                    pass
            
            logger.info(f"Archivo subido: {filename} ({file_size} bytes) por {user_id}")
        except Exception as e:
            response = NetworkMessage(
                type="upload_file_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.error(f"Error en _handle_upload_file: {e}")

    def _handle_download_file(self, client_id: str, message: NetworkMessage, repo_factory):
        """Maneja la descarga de un archivo"""
        try:
            import os
            import base64
            
            download_url = message.data.get("download_url")
            
            if not download_url:
                response = NetworkMessage(
                    type="download_file_response",
                    data={"success": False, "error": "URL de descarga no especificada"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            filepath = os.path.join("data", "uploads", download_url)
            
            if not os.path.exists(filepath):
                response = NetworkMessage(
                    type="download_file_response",
                    data={"success": False, "error": "Archivo no encontrado en el servidor"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            with open(filepath, 'rb') as f:
                file_bytes = f.read()
            
            file_data_b64 = base64.b64encode(file_bytes).decode()
            
            response = NetworkMessage(
                type="download_file_response",
                data={
                    "success": True,
                    "file_data": file_data_b64,
                    "filename": message.data.get("filename", download_url)
                },
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Archivo descargado: {download_url} por {client_id}")
        except Exception as e:
            response = NetworkMessage(
                type="download_file_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_assign_role(self, client_id: str, message: NetworkMessage, repo_factory):
        """Asigna un rol a un miembro del servidor"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            from src_Client_Server.Server.services.permission_service import PermissionService
            from src_Client_Server.Server.models.enums import Permission
            
            server_service = ServerService(repo_factory)
            permission_service = PermissionService()
            
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            target_user_id = message.data.get("target_user_id")
            role_id = message.data.get("role_id")
            
            server = server_service.get_server(server_id)
            if not server:
                response = NetworkMessage(
                    type="assign_role_response",
                    data={"success": False, "error": "Servidor no encontrado"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            is_owner = server.owner_id == user_id
            has_perm = is_owner or permission_service.has_permission(user_id, server_id, Permission.MANAGE_ROLES)
            
            if not has_perm:
                response = NetworkMessage(
                    type="assign_role_response",
                    data={"success": False, "error": "Sin permisos para gestionar roles"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            members_repo = repo_factory.get_repository('server_members')
            member = members_repo.get_by_id(target_user_id, server_id)
            if not member:
                response = NetworkMessage(
                    type="assign_role_response",
                    data={"success": False, "error": "El usuario no es miembro del servidor"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            if role_id not in member.role_ids:
                member.role_ids.append(role_id)
                members_repo.update(target_user_id, server_id, {'role_ids': member.role_ids})
            
            response = NetworkMessage(
                type="assign_role_response",
                data={"success": True},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Rol {role_id} asignado a usuario {target_user_id} en servidor {server_id}")
        except Exception as e:
            response = NetworkMessage(
                type="assign_role_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_remove_role(self, client_id: str, message: NetworkMessage, repo_factory):
        """Remueve un rol de un miembro del servidor"""
        try:
            from src_Client_Server.Server.services.server_service import ServerService
            from src_Client_Server.Server.services.permission_service import PermissionService
            from src_Client_Server.Server.models.enums import Permission
            
            server_service = ServerService(repo_factory)
            permission_service = PermissionService()
            
            server_id = message.data.get("server_id")
            user_id = message.data.get("user_id")
            target_user_id = message.data.get("target_user_id")
            role_id = message.data.get("role_id")
            
            server = server_service.get_server(server_id)
            if not server:
                response = NetworkMessage(
                    type="remove_role_response",
                    data={"success": False, "error": "Servidor no encontrado"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            is_owner = server.owner_id == user_id
            has_perm = is_owner or permission_service.has_permission(user_id, server_id, Permission.MANAGE_ROLES)
            
            if not has_perm:
                response = NetworkMessage(
                    type="remove_role_response",
                    data={"success": False, "error": "Sin permisos para gestionar roles"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            members_repo = repo_factory.get_repository('server_members')
            member = members_repo.get_by_id(target_user_id, server_id)
            if not member:
                response = NetworkMessage(
                    type="remove_role_response",
                    data={"success": False, "error": "El usuario no es miembro del servidor"},
                    sender_id="server"
                )
                self.send(client_id, response)
                return
            
            if role_id in member.role_ids:
                member.role_ids.remove(role_id)
                members_repo.update(target_user_id, server_id, {'role_ids': member.role_ids})
            
            response = NetworkMessage(
                type="remove_role_response",
                data={"success": True},
                sender_id="server"
            )
            self.send(client_id, response)
            logger.info(f"Rol {role_id} removido de usuario {target_user_id} en servidor {server_id}")
        except Exception as e:
            response = NetworkMessage(
                type="remove_role_response",
                data={"success": False, "error": str(e)},
                sender_id="server"
            )
            self.send(client_id, response)

    def _handle_video_frame(self, client_id: str, message: NetworkMessage, repo_factory):
        """Reenvia frames de video a los clientes en el canal"""
        try:
            broadcast_msg = NetworkMessage(
                type="video_frame_broadcast",
                data=message.data,
                sender_id=client_id
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_video_frame: {e}")

    def _handle_audio_frame(self, client_id: str, message: NetworkMessage, repo_factory):
        """Reenvia frames de audio a los clientes en el canal"""
        try:
            broadcast_msg = NetworkMessage(
                type="audio_frame_broadcast",
                data=message.data,
                sender_id=client_id
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_audio_frame: {e}")

    def _handle_start_call(self, client_id: str, message: NetworkMessage, repo_factory):
        """Inicia una llamada de voz/video en un canal"""
        try:
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            call_type = message.data.get("call_type", "voice")
            
            broadcast_msg = NetworkMessage(
                type="call_started",
                data={
                    "channel_id": channel_id,
                    "initiator_id": user_id,
                    "call_type": call_type
                },
                sender_id="server"
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    try:
                        self.send(connected_client_id, broadcast_msg)
                    except Exception:
                        pass
            
            logger.info(f"Llamada {call_type} iniciada en canal {channel_id} por {user_id}")
        except Exception as e:
            logger.error(f"Error en _handle_start_call: {e}")

    def _handle_join_call(self, client_id: str, message: NetworkMessage, repo_factory):
        """Un usuario se une a una llamada"""
        try:
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            
            broadcast_msg = NetworkMessage(
                type="call_user_joined",
                data={"channel_id": channel_id, "user_id": user_id},
                sender_id="server"
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_join_call: {e}")

    def _handle_leave_call(self, client_id: str, message: NetworkMessage, repo_factory):
        """Un usuario abandona una llamada"""
        try:
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            
            broadcast_msg = NetworkMessage(
                type="call_user_left",
                data={"channel_id": channel_id, "user_id": user_id},
                sender_id="server"
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_leave_call: {e}")

    def _handle_screen_share_start(self, client_id: str, message: NetworkMessage, repo_factory):
        """Inicia compartir pantalla"""
        try:
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            
            broadcast_msg = NetworkMessage(
                type="screen_share_started",
                data={"channel_id": channel_id, "user_id": user_id},
                sender_id="server"
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_screen_share_start: {e}")

    def _handle_screen_share_stop(self, client_id: str, message: NetworkMessage, repo_factory):
        """Detiene compartir pantalla"""
        try:
            channel_id = message.data.get("channel_id")
            user_id = message.data.get("user_id")
            
            broadcast_msg = NetworkMessage(
                type="screen_share_stopped",
                data={"channel_id": channel_id, "user_id": user_id},
                sender_id="server"
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_screen_share_stop: {e}")

    def _handle_screen_frame(self, client_id: str, message: NetworkMessage, repo_factory):
        """Reenvia frames de pantalla compartida"""
        try:
            broadcast_msg = NetworkMessage(
                type="screen_frame_broadcast",
                data=message.data,
                sender_id=client_id
            )
            with self.lock:
                for connected_client_id in list(self.clients.keys()):
                    if connected_client_id != client_id:
                        try:
                            self.send(connected_client_id, broadcast_msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error en _handle_screen_frame: {e}")

    def send(self, target_id: str, message: NetworkMessage) -> bool:
        """Envia un mensaje a un cliente especifico con longitud prefijada"""
        with self.lock:
            if target_id in self.clients:
                try:
                    msg_bytes = message.to_json().encode()
                    # Prefijar con 4 bytes de longitud (big-endian)
                    length_header = len(msg_bytes).to_bytes(4, 'big')
                    self.clients[target_id].sendall(length_header + msg_bytes)
                    return True
                except Exception as e:
                    print(f"Error sending to {target_id}: {e}")
                    return False
        return False
    
    def broadcast(self, message: NetworkMessage, exclude: Optional[List[str]] = None):
        """Envia un mensaje a todos los clientes con longitud prefijada"""
        exclude = exclude or []
        msg_bytes = message.to_json().encode()
        length_header = len(msg_bytes).to_bytes(4, 'big')
        with self.lock:
            for client_id, client_socket in self.clients.items():
                if client_id not in exclude:
                    try:
                        client_socket.sendall(length_header + msg_bytes)
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
    