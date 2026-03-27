"""
Ventana principal de la aplicación
"""
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
from PIL import Image, ImageTk
import threading
import time

from src_Client_Server.Client.models.user import User, UserStatus
from src_Client_Server.Client.models.server import Server
from src_Client_Server.Client.models.channel import Channel, ChannelType
from src_Client_Server.Client.models.message import Message
from src_Client_Server.Client.models import enums
from src_Client_Server.Client.ui.components import AvatarLabel, ChannelButton, ServerButton, MessageBubble, UserListItem, ScrollableFrame
from src_Client_Server.Client.ui.login_window import ConfigManager, LoginWindow
from src_Client_Server.Client.ui.register_window import RegisterWindow
from src_Client_Server.Client.ui.create_server_modal import CreateServerModal
from src_Client_Server.Client.ui.create_channel_modal import CreateChannelModal
from src_Client_Server.Client.ui.server_settings_modal import ServerSettingsModal
from src_Client_Server.Client.ui.manage_roles_modal import ManageRolesModal
from src_Client_Server.Client.utils.logger import setup_logger
from src_Client_Server.Client.network.service import TCPClient, NetworkMessage

logger = setup_logger(__name__)


class MainWindow(ctk.CTk):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana
        self.title("Chat App - Discord Clone")
        self.geometry("1200x700")
        self.minsize(900, 500)
        
        # Servicios de red del cliente (para comunicarse con el servidor)
        self.network_service = TCPClient()
        self.network_service.register_callback('message', self._on_message_received)
        self.is_connected = False
        self.current_user_data = None  # Datos del usuario obtenidos del servidor
        
        # Response handling
        self.response_event = threading.Event()
        self.response_data = None

        # Ip Port predeterminados
        self.host = "127.0.0.1"
        self.port = 5555

        # Estado
        self.current_user: Optional[User] = None
        self.current_server: Optional[Server] = None
        self.current_channel: Optional[Channel] = None
        self.servers: list = []
        self.channels: list = []
        self.messages: list = []
        
        # Configurar apariencia
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Construir UI
        self._build_ui()
        
        # Mostrar login
        self._show_login()
    
    def _build_ui(self):
        """Construye la interfaz de usuario"""
        # Configurar grid principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Panel de servidores (izquierda)
        self.server_panel = ctk.CTkFrame(self, width=72, corner_radius=0)
        self.server_panel.grid(row=0, column=0, sticky="nsw")
        self.server_panel.grid_propagate(False)
        
        self.server_buttons_frame = ScrollableFrame(
            self.server_panel,
            width=60,
            height=self.winfo_height()
        )
        self.server_buttons_frame.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        
        # Botón para añadir servidor
        self.add_server_btn = ctk.CTkButton(
            self.server_buttons_frame,
            text="+",
            width=32,
            height=32,
            corner_radius=8,
            command=self._on_add_server,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            font=ctk.CTkFont(size=20)
        )
        self.add_server_btn.pack(pady=(0, 10))
        
        # Separador
        separator = ctk.CTkFrame(self, width=2, fg_color=("gray70", "gray30"))
        separator.grid(row=0, column=1, sticky="ns")
        
        # Panel de canales
        self.channel_panel = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.channel_panel.grid(row=0, column=2, sticky="nsw")
        self.channel_panel.grid_columnconfigure(0, weight=1)
        self.channel_panel.grid_rowconfigure(1, weight=1)
        
        # Header del servidor
        self.server_header = ctk.CTkFrame(self.channel_panel, height=60, fg_color=("gray85", "gray20"))
        self.server_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.server_header.grid_propagate(False)
        self.server_header.grid_columnconfigure(1, weight=1)  # Columna del título se expande
        
        # Botón de configuración (inicialmente oculto)
        self.settings_btn = ctk.CTkButton(
            self.server_header,
            text="⚙️",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray75", "gray35"),
            command=self._on_server_settings,
            state="disabled"
        )
        self.settings_btn.grid(row=0, column=0, padx=(10, 5), pady=15)
        
        # Título del servidor
        self.server_title = ctk.CTkLabel(
            self.server_header,
            text="Selecciona un servidor",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.server_title.grid(row=0, column=1, padx=5, pady=15, sticky="w")
        
        # Botón de gestión de roles (inicialmente oculto)
        self.roles_btn = ctk.CTkButton(
            self.server_header,
            text="👥",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray75", "gray35"),
            command=self._on_manage_roles,
            state="disabled"
        )
        self.roles_btn.grid(row=0, column=2, padx=(5, 10), pady=15)
        
        # Lista de canales
        self.channels_frame = ScrollableFrame(self.channel_panel)
        self.channels_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Botón para crear canal
        self.add_channel_btn = ctk.CTkButton(
            self.channels_frame,
            text="+ Crear Canal",
            height=30,
            fg_color="transparent",
            border_width=1,
            command=self._on_create_channel,
            state="disabled"
        )
        self.add_channel_btn.pack(pady=(10, 0), fill="x")
        
        # Separador
        separator2 = ctk.CTkFrame(self, width=2, fg_color=("gray70", "gray30"))
        separator2.grid(row=0, column=3, sticky="ns")
        
        # Panel de chat
        self.chat_panel = ctk.CTkFrame(self, corner_radius=0)
        self.chat_panel.grid(row=0, column=4, sticky="nsew")
        self.chat_panel.grid_columnconfigure(0, weight=1)
        self.chat_panel.grid_rowconfigure(1, weight=1)
        
        # Header del canal
        self.channel_header = ctk.CTkFrame(self.chat_panel, height=60, fg_color=("gray85", "gray20"))
        self.channel_header.grid(row=0, column=0, sticky="ew")
        
        self.channel_title = ctk.CTkLabel(
            self.channel_header,
            text="Selecciona un canal",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.channel_title.pack(side="left", padx=20, pady=15)
        
        # Mensajes
        self.messages_frame = ScrollableFrame(self.chat_panel)
        self.messages_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Input de mensaje
        self.message_input_frame = ctk.CTkFrame(self.chat_panel, fg_color=("gray90", "gray15"))
        self.message_input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.message_input_frame.grid_columnconfigure(0, weight=1)
        
        self.message_entry = ctk.CTkEntry(
            self.message_input_frame,
            placeholder_text="Escribe un mensaje...",
            height=40
        )
        self.message_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")
        self.message_entry.bind("<Return>", lambda e: self._send_message())
        
        self.send_button = ctk.CTkButton(
            self.message_input_frame,
            text="Enviar",
            width=80,
            height=40,
            command=self._send_message
        )
        self.send_button.grid(row=0, column=1, padx=(0, 10), pady=10)
        
        # Separador
        separator3 = ctk.CTkFrame(self, width=2, fg_color=("gray70", "gray30"))
        separator3.grid(row=0, column=5, sticky="ns")
        
        # Panel de miembros
        self.members_panel = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.members_panel.grid(row=0, column=6, sticky="nse")
        self.members_panel.grid_columnconfigure(0, weight=1)
        
        members_title = ctk.CTkLabel(
            self.members_panel,
            text="Miembros",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        members_title.grid(row=0, column=0, pady=15, padx=15, sticky="w")
        
        self.members_frame = ScrollableFrame(self.members_panel)
        self.members_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Configurar pesos
        self.grid_columnconfigure(4, weight=1)
    
    def _show_login(self):
        """Muestra la ventana de login"""
        self.login_window = LoginWindow(
            self,
            on_login_success=self._handle_login,
            on_register_click=self._show_register
        )
        self.login_window.grab_set()
    
    def _show_register(self):
        """Muestra la ventana de registro"""
        self.login_window.withdraw()
        self.register_window = RegisterWindow(
            self,
            on_register_success=self._handle_register,
            on_back=self._back_to_login
        )
        self.register_window.grab_set()
    
    def _back_to_login(self):
        """Vuelve al login"""
        self.register_window.destroy()
        self.login_window.deiconify()
        self.login_window.grab_set()
    
    def _on_message_received(self, data):
        """Maneja los mensajes recibidos del servidor"""
        message = data.get('message')
        if not message:
            return
        # Procesar respuestas específicas
        if message.type in ["login_response", "register_response", 
                            "get_user_servers_response", "get_server_channels_response", 
                            "update_server_response", "create_channel_response", 
                            "delete_channel_response", "get_roles_response",
                            "create_role_response", "update_role_response",
                            "delete_role_response", "reorder_roles_response",
                            "check_permission_response" ]:
            self.response_data = message.data
            self.response_event.set()
    
    def _handle_login(self, username: str, password: str):
        """Maneja el login"""
        # Conectar al servidor si no está conectado
        if not self.is_connected:
            server_host, server_port = ConfigManager.get_server_config()
            logger.info(f"Conectando a {server_host}:{server_port}")
            if not self.network_service.connect(server_host, server_port):
                self.login_window.show_error("No se pudo conectar al servidor")
                return
            self.is_connected = True
            # Iniciar procesamiento de mensajes en segundo plano
            threading.Thread(target=self.network_service.start_processing, daemon=True).start()
            time.sleep(0.5)  # Pequeña pausa para conectarse
        
        # Enviar mensaje de login al servidor
        login_message = NetworkMessage(
            type="login",
            data={"email": username, "password": password},
            sender_id="client"
        )
        
        print(f"[CLIENT] Enviando login: email={username}, password={'*' * len(password)}")
        
        if not self.network_service.send(login_message):
            self.login_window.show_error("Error enviando solicitud de login")
            return
        
        # Esperar respuesta del servidor
        if not self.response_event.wait(timeout=5.0):
            self.login_window.show_error("Timeout esperando respuesta del servidor")
            return
        
        print(f"[CLIENT] Respuesta recibida: {self.response_data}")
        
        if not self.response_data or not self.response_data.get("success"):
            error = self.response_data.get("error", "Error desconocido") if self.response_data else "Error desconocido"
            self.login_window.show_error(f"Error de login: {error}")
            self.response_event.clear()
            return
        
        # Obtener usuario del servidor
        user_data = self.response_data.get("user")
        if not user_data:
            self.login_window.show_error("Usuario no encontrado")
            self.response_event.clear()
            return
        
        print(f"[CLIENT] Usuario autenticado: {user_data}")
        
        # Crear objeto User con los datos del servidor
        self.current_user = User(**user_data)
        self.response_event.clear()
        
        self.login_window.destroy()
        self._load_user_servers()
        self._show_main_interface()
    
    def _handle_register(self, username: str, email: str, password: str):
        """Maneja el registro"""
        # Conectar al servidor si no está conectado
        if not self.is_connected:
            server_host, server_port = ConfigManager.get_server_config()
            if not self.network_service.connect(server_host, server_port):
                self.register_window.show_error("No se pudo conectar al servidor")
                return
            self.is_connected = True
            # Iniciar procesamiento de mensajes en segundo plano
            threading.Thread(target=self.network_service.start_processing, daemon=True).start()
            time.sleep(0.5)
        
        # Enviar mensaje de registro al servidor
        register_message = NetworkMessage(
            type="register",
            data={"username": username, "email": email, "password": password},
            sender_id="client"
        )
        
        print(f"[CLIENT] Enviando resgistro: username={username}, email={email}  ,password={'*' * len(password)}")

        if not self.network_service.send(register_message):
            self.register_window.show_error("Error enviando solicitud de registro")
            return
        
        # Esperar respuesta
        if not self.response_event.wait(timeout=5.0):
            self.register_window.show_error("Timeout esperando respuesta")
            return
        
        print(f"[CLIENT] Respuesta recibida: {self.response_data}")

        if not self.response_data or not self.response_data.get("success"):
            error = self.response_data.get("error", "Error desconocido") if self.response_data else "Error"
            self.register_window.show_error(f"Error de registro: {error}")
            self.response_event.clear()
            return
        


        self.register_window.show_success("Cuenta creada exitosamente!")
        self.response_event.clear()
        self.register_window.after(1500, self._back_to_login)
    
    def _load_user_servers(self):
        """Carga los servidores del usuario"""
        if not self.current_user:
            return
        
        # Solicitar servidores al servidor
        get_servers_message = NetworkMessage(
            type="get_user_servers",
            data={"user_id": self.current_user.id},
            sender_id=self.current_user.id
        )
        
        if not self.network_service.send(get_servers_message):
            logger.error("Error al solicitar servidores del usuario")
            logger.info(get_servers_message)
            return
        
        # Esperar respuesta
        if not self.response_event.wait(timeout=5.0):
            logger.error("Timeout esperando servidores")
            return
        
        print(f"[CLIENT] Respuesta recibida: {self.response_data}")

        if not self.response_data or not self.response_data.get("success"):
            logger.error("Error obteniendo servidores")
            return
        
        servers_data = self.response_data.get("servers", [])
        self.servers = servers_data
        logger.info(f"CHANNELS DATA : {self.servers}")
        self.response_event.clear()
        self._update_server_list()
    
    def _update_server_list(self):
        """Actualiza la lista de servidores en la sidebar"""
        # Limpiar botones existentes
        for widget in self.server_buttons_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget != self.add_server_btn:
                widget.destroy()
        
        # Crear botones
        for server in self.servers:
            btn = ServerButton(
                self.server_buttons_frame,
                server_name=server['name'],
                server_id=server['id'],
                command=lambda s=server: self._select_server(s)
            )
            btn.pack(pady=5, fill="x")
    
    def _select_server(self, server: Dict[str, Any]):
        """Selecciona un servidor"""
        self.current_server = Server(**server)
        self._load_server_channels()
        self._update_server_header()
        self._load_server_members()
    
    def _update_server_header(self):
        """Actualiza el header del servidor"""
        if self.current_server:
            logger.info(self.current_server , self.current_user.id)
            self.server_title.configure(text=self.current_server.name)
            self.add_channel_btn.configure(state="normal")
            
            #logger.info("Permisos verificados mediante comunicación con el servidor")

            # Verificar permisos para botones (simplificado para cliente)
            can_manage_server = self.current_server.owner_id == self.current_user.id if self.current_user else False
            can_manage_roles = can_manage_server  # Simplificado: solo el dueño puede gestionar roles
            
            # Dueño siempre puede gestionar roles
            if can_manage_server:
                can_manage_roles = True
            
            self.settings_btn.configure(state="normal" if can_manage_server else "disabled")
            self.roles_btn.configure(state="normal" if can_manage_roles else "disabled")
        else:
            self.server_title.configure(text="Selecciona un servidor")
            self.add_channel_btn.configure(state="disabled")
            self.settings_btn.configure(state="disabled")
            self.roles_btn.configure(state="disabled")
    
    def _load_server_channels(self):
        """Carga los canales del servidor actual"""
        if not self.current_server:
            return
        
        # Solicitar canales al servidor
        get_channels_message = NetworkMessage(
            type="get_server_channels",
            data={"server_id": self.current_server.id},
            sender_id=self.current_user.id if self.current_user else "unknown"
        )
        
        if not self.network_service.send(get_channels_message):
            logger.error("Error enviando solicitud de canales")
            logger.info(get_channels_message)
            return
    
        # Esperar respuesta
        if not self.response_event.wait(timeout=5.0):
            logger.error("Timeout obteniendo respuesta en _load_server_channels")
            return
        
        print(f"[CLIENT] Respuesta recibida: {self.response_data}")

        if not self.response_data or not self.response_data.get("success"):
            logger.error("Error obteniendo canales")
            self.response_event.clear()
            return
            
        channels_data = self.response_data.get("channels", [])
        self.channels = channels_data
        logger.info(f"CHANNELS DATA : {self.channels}")
        self.response_event.clear()
        self._update_channel_list()


    def _update_channel_list(self):
        """Actualiza la lista de canales"""
        # Limpiar canales (excepto el botón + Crear Canal)
        for widget in self.channels_frame.winfo_children():
            if widget != self.add_channel_btn:
                widget.destroy()
        
        # Crear botones por tipo, comparando valores en lugar del enum directamente
        text_channels = [c for c in self.channels if c['type'] == 'text']
        voice_channels = [c for c in self.channels if c['type'] == 'voice']
        logger.info(f"Cargando canales: {len(text_channels)} de texto, {len(voice_channels)} de voz")

        for c in self.channels:
            type_str = c.type.value if hasattr(c['type'], 'value') else c['type']
            print(f"Canal: {c['name']} (ID: {c['id']}, Tipo: {c['type']}, Valor: {type_str})")
        
        if self.channels:
            ctk.CTkLabel(self.channels_frame, text="CANALES DE TEXTO", 
                        font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(10, 5), anchor="w", padx=5)
            
            for channel in text_channels:
                btn = ChannelButton(
                    self.channels_frame,
                    channel_name=channel['name'],
                    channel_id=channel['id'],
                    channel_type=channel['type'],
                    command=lambda c=channel: self._select_channel(c)
                )
                btn.pack(pady=2, fill="x", padx=3)
        
        if voice_channels:
            ctk.CTkLabel(self.channels_frame, text="CANALES DE VOZ", 
                        font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(15, 5), anchor="w", padx=5)
            for channel in voice_channels:
                btn = ChannelButton(
                    self.channels_frame,
                    channel_name=channel['name'],
                    channel_id=channel['id'],
                    channel_type=channel['type'],
                    command=lambda c=channel: self._select_channel(c)
                )
                btn.pack(pady=2, fill="x", padx=3)
    
    def _select_channel(self, channel: Dict[str, Any]):
        """Selecciona un canal"""
        self.current_channel = Channel(**channel)
        logger.info(self.current_channel)
        # self.channel_title.configure(**Channel)
        self._load_channel_messages()
    
    def _load_channel_messages(self):
        """Carga los mensajes del canal actual"""
        if not self.current_channel:
            return
        
        # Limpiar mensajes
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        
        # Cargar mensajes
        # Solicitar mensajes al servidor
        get_messages_message = NetworkMessage(
            type="get_channel_messages",
            data={"channel_id": self.current_channel.id},
            sender_id=self.current_user.id if self.current_user else "unknown"
        )
        
        if not self.network_service.send(get_messages_message):
            logger.error("Error enviando solicitud de canales")
            logger.info(get_messages_message)
            return
        
        # Esperar respuesta
        if not self.response_event.wait(timeout=5.0):
            logger.error("Timeout obteniendo respuesta en _load_channel_messages")
            return
        
        print(f"[CLIENT] Respuesta recibida: {self.response_data}")

        if not self.response_data or not self.response_data.get("success"):
            logger.error("Error obteniendo canales")
            self.response_event.clear()
            return


        message_data = self.response_data.get("channels", [])
        self.messages = message_data
        logger.info(f"CHANNELS MESSAGE DATA : {self.messages}")
        self.response_event.clear()
        self._display_messages()
    









    def _display_messages(self):
        """Muestra los mensajes en el chat"""
        for message in self.messages:
            # Obtener autor (simplificado)
            author_name = f"Usuario {message.author_id[:8]}"
            
            bubble = MessageBubble(
                self.messages_frame,
                author=author_name,
                content=message.content,
                timestamp=message.created_at.strftime("%H:%M"),
                is_own=(message.author_id == self.current_user.id if self.current_user else False)
            )
            bubble.pack(fill="x", pady=5, padx=10)
        
        # Scroll al final
        self.messages_frame._parent_canvas.yview_moveto(1.0)
    
    def _send_message(self):
        """Envía un mensaje"""
        if not self.current_channel or not self.current_user:
            return
        
        content = self.message_entry.get().strip()
        if not content:
            return
        
        # Enviar mensaje al servidor
        send_message_message = NetworkMessage(
            type="send_message",
            data={
                "content": content,
                "channel_id": self.current_channel.id,
                "author_id": self.current_user.id
            },
            sender_id=self.current_user.id
        )
        
        if self.network_service.send(send_message_message):
            self.message_entry.delete(0, "end")
            # En una implementación real, esperaríamos la confirmación del servidor
            # Por ahora, recargamos inmediatamente
            self._load_channel_messages()
        else:
            print(f"Error enviando mensaje al servidor")
    
    def _load_server_members(self):
        """Carga los miembros del servidor actual"""
        if not self.current_server:
            return
        
        # Solicitar miembros al servidor
        get_members_message = NetworkMessage(
            type="get_server_members",
            data={"server_id": self.current_server.id},
            sender_id=self.current_user.id if self.current_user else "unknown"
        )
        
        if self.network_service.send(get_members_message):
            # En una implementación real, esperaríamos la respuesta de forma asíncrona
            # Por ahora, simulamos con datos vacíos y limpiamos la lista
            for widget in self.members_frame.winfo_children():
                widget.destroy()
            logger.info(f"Solicitud de miembros enviada para servidor {self.current_server.name}")
        else:
            logger.error("Error enviando solicitud de miembros")
    
    def _on_add_server(self):
        """Muestra modal para crear servidor"""
        if not self.current_user:
            return
        
        modal = CreateServerModal(
            self,
            on_create=self._on_create_server
        )
    
    def _on_create_server(self, **kwargs):
        """Crea un nuevo servidor"""
        if not self.current_user:
            return
        
        # Enviar solicitud de creación de servidor al servidor
        create_server_message = NetworkMessage(
            type="create_server",
            data={
                "owner_id": self.current_user.id,
                **kwargs
            },
            sender_id=self.current_user.id
        )
        
        if self.network_service.send(create_server_message):
            # En una implementación real, esperaríamos la respuesta de forma asíncrona
            # Por ahora, recargamos la lista de servidores
            self._load_user_servers()
        else:
            print(f"Error enviando solicitud de creación de servidor")
    
    def _on_create_channel(self):
        """Muestra modal para crear canal"""
        if not self.current_server:
            return
        
        modal = CreateChannelModal(
            self,
            server_id=self.current_server.id,
            on_create=self._on_channel_created
        )
    
    def _on_channel_created(self, **kwargs):
        """Canal creado exitosamente"""
        if not self.current_server:
            return
        if not self.current_user:
            return

        # Extraer server_id de kwargs si existe para evitar duplicado
        kwargs.pop('server_id', None)
        
        # Enviar solicitud de creación de canal al servidor
        create_channel_message = NetworkMessage(
            type="create_channel",
            data={
                "server_id": self.current_server.id,
                "creator_id": self.current_user.id,
                **kwargs
            },
            sender_id=self.current_user.id
        )
        
        if self.network_service.send(create_channel_message):
            # En una implementación real, esperaríamos la respuesta de forma asíncrona
            # Por ahora, recargamos la lista de canales
            self._load_server_channels()
        else:
            print(f"Error enviando solicitud de creación de canal")
    
    def _on_server_settings(self):
        """Abre modal de configuración del servidor"""
        if not self.current_server or not self.current_user:
            return
        
        modal = ServerSettingsModal(
            self,
            server_id=self.current_server.id,
            user_id=self.current_user.id,
            on_save=self._on_server_settings_saved
        )
    
    def _on_server_settings_saved(self, updated_server: Server):
        """Callback cuando se guarda la configuración del servidor"""
        # Actualizar servidor actual
        self.current_server = updated_server
        # Actualizar en la lista de servidores
        for i, s in enumerate(self.servers):
            if s['id'] == updated_server.id:
                self.servers[i] = updated_server.dict()
                break
        # Actualizar header
        self._update_server_header()
    
    def _on_manage_roles(self):
        """Abre modal de gestión de roles"""
        if not self.current_server or not self.current_user:
            return
        
        modal = ManageRolesModal(
            self,
            server_id=self.current_server.id,
            user_id=self.current_user.id,
            on_save=self._on_roles_saved
        )
    
    def _on_roles_saved(self):
        """Callback cuando se guardan los roles"""
        # Recargar canales y miembros por si los roles afectan permisos
        self._load_server_channels()
        self._load_server_members()
    
    def _show_main_interface(self):
        """Muestra la interfaz principal"""
        self.deiconify()
        self._load_user_servers()

    def set_host_ip(self, host, port):
        self.host = host
        self.port = port