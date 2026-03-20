"""
Ventana principal de la aplicación
"""
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
from PIL import Image, ImageTk
import threading
import time

from models.user import User
from models.server import Server
from models.channel import Channel
from models.message import Message
from services import AuthService, ServerService, MessageService, InviteService, PermissionService
from ui.components import AvatarLabel, ChannelButton, ServerButton, MessageBubble, UserListItem, ScrollableFrame
from ui.login_window import LoginWindow
from ui.register_window import RegisterWindow
from ui.create_server_modal import CreateServerModal
from ui.create_channel_modal import CreateChannelModal
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MainWindow(ctk.CTk):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana
        self.title("Chat App - Discord Clone")
        self.geometry("1200x700")
        self.minsize(900, 500)
        
        # Servicios
        self.auth_service = AuthService()
        self.server_service = ServerService()
        self.message_service = MessageService()
        self.invite_service = InviteService()
        self.permission_service = PermissionService()
        
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
        
        self.server_title = ctk.CTkLabel(
            self.server_header,
            text="Selecciona un servidor",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.server_title.pack(expand=True)
        
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
    
    def _handle_login(self, username: str, password: str):
        """Maneja el login"""
        success, error, user = self.auth_service.login(username, password)
        
        if success:
            self.current_user = user
            self.login_window.destroy()
            self._load_user_servers()
            self._show_main_interface()
        else:
            self.login_window.show_error(f"Login fallido: {error}")
    
    def _handle_register(self, username: str, email: str, password: str):
        """Maneja el registro"""
        success, error, user = self.auth_service.register(username, email, password)
        
        if success:
            self.register_window.show_success("Cuenta creada exitosamente!")
            self.register_window.after(1500, self._back_to_login)
        else:
            self.register_window.show_error(f"Registro fallido: {error}")
    
    def _load_user_servers(self):
        """Carga los servidores del usuario"""
        if not self.current_user:
            return
        self.servers = self.auth_service.get_user_servers(self.current_user.id)
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
            self.server_title.configure(text=self.current_server.name)
            self.add_channel_btn.configure(state="normal")
        else:
            self.server_title.configure(text="Selecciona un servidor")
            self.add_channel_btn.configure(state="disabled")
    
    def _load_server_channels(self):
        """Carga los canales del servidor actual"""
        if not self.current_server:
            return
        
        self.channels = self.server_service.get_server_channels(self.current_server.id)
        self._update_channel_list()
    
    def _update_channel_list(self):
        """Actualiza la lista de canales"""
        # Limpiar canales
        for widget in self.channels_frame.winfo_children():
            if isinstance(widget, ChannelButton):
                widget.destroy()
        
        # Crear botones por tipo
        text_channels = [c for c in self.channels if c.type == "text"]
        voice_channels = [c for c in self.channels if c.type == "voice"]
        
        if text_channels:
            ctk.CTkLabel(self.channels_frame, text="CANALES DE TEXTO", 
                        font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(10, 5), anchor="w")
            for channel in text_channels:
                btn = ChannelButton(
                    self.channels_frame,
                    channel_name=channel.name,
                    channel_id=channel.id,
                    channel_type=channel.type,
                    command=lambda c=channel: self._select_channel(c)
                )
                btn.pack(pady=2, fill="x")
        
        if voice_channels:
            ctk.CTkLabel(self.channels_frame, text="CANALES DE VOZ", 
                        font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(15, 5), anchor="w")
            for channel in voice_channels:
                btn = ChannelButton(
                    self.channels_frame,
                    channel_name=channel.name,
                    channel_id=channel.id,
                    channel_type=channel.type,
                    command=lambda c=channel: self._select_channel(c)
                )
                btn.pack(pady=2, fill="x")
    
    def _select_channel(self, channel: Channel):
        """Selecciona un canal"""
        self.current_channel = channel
        self.channel_title.configure(text=f"# {channel.name}")
        self._load_channel_messages()
    
    def _load_channel_messages(self):
        """Carga los mensajes del canal actual"""
        if not self.current_channel:
            return
        
        # Limpiar mensajes
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        
        # Cargar mensajes
        self.messages = self.message_service.get_channel_messages(self.current_channel.id)
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
        
        success, error, message = self.message_service.send_message(
            content=content,
            channel_id=self.current_channel.id,
            author_id=self.current_user.id
        )
        
        if success:
            self.message_entry.delete(0, "end")
            self._load_channel_messages()
        else:
            print(f"Error enviando mensaje: {error}")
    
    def _load_server_members(self):
        """Carga los miembros del servidor actual"""
        if not self.current_server:
            return
        
        members = self.server_service.get_server_members(self.current_server.id)
        
        # Limpiar lista
        for widget in self.members_frame.winfo_children():
            widget.destroy()
        
        # Mostrar miembros
        for member_data in members:
            user = member_data['user']
            member = member_data['member']
            
            item = UserListItem(
                self.members_frame,
                username=user['username'],
                status='online'  # Se obtendría del servicio de estado
            )
            item.pack(fill="x", pady=2)
    
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
        success, error, server = self.server_service.create_server(
            owner_id=self.current_user.id,
            **kwargs
        )

        if success:
            self._load_user_servers()
        else:
            print(f"Error creando servidor: {error}")
    
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
        self._load_server_channels()
    
    def _show_main_interface(self):
        """Muestra la interfaz principal"""
        self.deiconify()
        self._load_user_servers()
