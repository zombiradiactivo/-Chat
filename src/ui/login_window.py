"""
Ventana de login/registro
"""
import customtkinter as ctk
from typing import Callable, Optional
from models.user import UserCreate
from utils.config_manager import ConfigManager


class LoginWindow(ctk.CTkToplevel):
    """Ventana de login y registro"""
    
    def __init__(self, master, on_login_success: Callable, on_register_click: Callable):
        super().__init__(master)
        
        self.title("Chat App - Login")
        self.geometry("450x650")
        self.resizable(False, False)
        
        self.on_login_success = on_login_success
        self.on_register_click = on_register_click
        
        # Centrar ventana
        self.center_window()
        
        # Configurar grid
        self.grid_columnconfigure(0, weight=1)
        
        # Logo/título
        title = ctk.CTkLabel(
            self,
            text="💬 Chat App",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.grid(row=0, column=0, pady=(40, 20), padx=20)
        
        subtitle = ctk.CTkLabel(
            self,
            text="Inicia sesión para continuar",
            font=ctk.CTkFont(size=14),
            text_color="gray60"
        )
        subtitle.grid(row=1, column=0, pady=(0, 30))
        
        # Formulario
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.grid(row=2, column=0, padx=40, sticky="ew")
        form_frame.grid_columnconfigure(0, weight=1)
        
        # Username/Email
        self.username_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Usuario o Email",
            height=40
        )
        self.username_entry.grid(row=0, column=0, pady=(0, 15), sticky="ew")
        
        # Password
        self.password_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Contraseña",
            show="•",
            height=40
        )
        self.password_entry.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        
        # Separador - Configuración del servidor
        server_label = ctk.CTkLabel(
            form_frame,
            text="Configuración del Servidor",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray70"
        )
        server_label.grid(row=2, column=0, pady=(15, 10), sticky="w")
        
        # Host del servidor
        self.host_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Host (ej: 127.0.0.1)",
            height=35
        )
        self.host_entry.grid(row=3, column=0, pady=(0, 10), sticky="ew")
        
        # Puerto del servidor
        self.port_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Puerto (ej: 5555)",
            height=35
        )
        self.port_entry.grid(row=4, column=0, pady=(0, 15), sticky="ew")
        
        # Checkbox recordar usuario
        self.remember_var = ctk.BooleanVar(value=False)
        remember_check = ctk.CTkCheckBox(
            form_frame,
            text="Recordar usuario",
            variable=self.remember_var
        )
        remember_check.grid(row=5, column=0, pady=(0, 20), sticky="w")
        
        # Botón login
        self.login_button = ctk.CTkButton(
            form_frame,
            text="Iniciar Sesión",
            height=40,
            command=self._on_login,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.login_button.grid(row=6, column=0, pady=(0, 15), sticky="ew")
        
        # Separador
        separator = ctk.CTkLabel(
            form_frame,
            text="─" * 30,
            text_color="gray60"
        )
        separator.grid(row=7, column=0, pady=10)
        
        # Botón registro
        register_button = ctk.CTkButton(
            form_frame,
            text="Crear Cuenta",
            height=40,
            fg_color="transparent",
            border_width=2,
            command=self.on_register_click,
            font=ctk.CTkFont(size=14)
        )
        register_button.grid(row=8, column=0, pady=(0, 20), sticky="ew")
        
        # Label error
        self.error_label = ctk.CTkLabel(
            form_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(size=12)
        )
        self.error_label.grid(row=9, column=0, pady=(10, 0))
        
        # Cargar configuración guardada
        self._load_saved_config()
        
        # Bind Enter
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self._on_login())
        
        # Focus en username
        self.username_entry.focus()
    
    def _load_saved_config(self):
        """Carga la configuración guardada"""
        config = ConfigManager.load_config()
        
        # Cargar servidor
        server_config = config.get('server', {})
        self.host_entry.insert(0, server_config.get('host', '127.0.0.1'))
        self.port_entry.insert(0, str(server_config.get('port', 5555)))
        
        # Cargar usuario recordado
        ui_config = config.get('ui', {})
        if ui_config.get('remember_username'):
            self.remember_var.set(True)
            last_username = ui_config.get('last_username')
            if last_username:
                self.username_entry.insert(0, last_username)
    
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _on_login(self):
        """Maneja el evento de login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        
        # Validaciones
        if not username or not password:
            self.error_label.configure(text="Completa usuario y contraseña")
            return
        
        if not host:
            self.error_label.configure(text="Configura el host del servidor")
            return
        
        if not port_str:
            self.error_label.configure(text="Configura el puerto del servidor")
            return
        
        # Validar puerto
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                self.error_label.configure(text="Puerto debe estar entre 1 y 65535")
                return
        except ValueError:
            self.error_label.configure(text="Puerto debe ser un número")
            return
        
        # Guardar configuración
        remember = self.remember_var.get()
        ConfigManager.set_server_config(host, port)
        ConfigManager.set_last_username(username, remember)
        
        # Llamar callback de login
        self.on_login_success(username, password)
    
    def show_error(self, message: str):
        """Muestra un mensaje de error"""
        self.error_label.configure(text=message)
    
    def clear_fields(self):
        """Limpia los campos"""
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")
