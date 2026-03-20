"""
Ventana de login/registro
"""
import customtkinter as ctk
from typing import Callable, Optional
from models.user import UserCreate


class LoginWindow(ctk.CTkToplevel):
    """Ventana de login y registro"""
    
    def __init__(self, master, on_login_success: Callable, on_register_click: Callable):
        super().__init__(master)
        
        self.title("Chat App - Login")
        self.geometry("400x500")
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
        
        # Botón login
        self.login_button = ctk.CTkButton(
            form_frame,
            text="Iniciar Sesión",
            height=40,
            command=self._on_login,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.login_button.grid(row=2, column=0, pady=(0, 15), sticky="ew")
        
        # Separador
        separator = ctk.CTkLabel(
            form_frame,
            text="─" * 30,
            text_color="gray60"
        )
        separator.grid(row=3, column=0, pady=10)
        
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
        register_button.grid(row=4, column=0, pady=(0, 20), sticky="ew")
        
        # Label error
        self.error_label = ctk.CTkLabel(
            form_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(size=12)
        )
        self.error_label.grid(row=5, column=0, pady=(10, 0))
        
        # Bind Enter
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self._on_login())
        
        # Focus en username
        self.username_entry.focus()
    
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
        
        if not username or not password:
            self.error_label.configure(text="Completa todos los campos")
            return
        
        self.on_login_success(username, password)
    
    def show_error(self, message: str):
        """Muestra un mensaje de error"""
        self.error_label.configure(text=message)
    
    def clear_fields(self):
        """Limpia los campos"""
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")
