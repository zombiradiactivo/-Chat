"""
Ventana de registro
"""
import customtkinter as ctk
from typing import Callable
from models.user import UserCreate
from utils.validation import validate_username, validate_email, validate_password


class RegisterWindow(ctk.CTkToplevel):
    """Ventana de registro"""
    
    def __init__(self, master, on_register_success: Callable, on_back: Callable):
        super().__init__(master)
        
        self.title("Chat App - Registro")
        self.geometry("450x600")
        self.resizable(False, False)
        
        self.on_register_success = on_register_success
        self.on_back = on_back
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        
        # Título
        title = ctk.CTkLabel(
            self,
            text="📝 Crear Cuenta",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, pady=(30, 20), padx=30)
        
        # Formulario
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.grid(row=1, column=0, padx=30, sticky="ew")
        form_frame.grid_columnconfigure(0, weight=1)
        
        # Username
        ctk.CTkLabel(form_frame, text="Usuario", anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.username_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Ej: Juan123",
            height=35
        )
        self.username_entry.grid(row=1, column=0, pady=(0, 15), sticky="ew")
        
        # Email
        ctk.CTkLabel(form_frame, text="Email", anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.email_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="tu@email.com",
            height=35
        )
        self.email_entry.grid(row=3, column=0, pady=(0, 15), sticky="ew")
        
        # Password
        ctk.CTkLabel(form_frame, text="Contraseña", anchor="w").grid(row=4, column=0, sticky="w", pady=(0, 5))
        self.password_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Mínimo 8 caracteres",
            show="•",
            height=35
        )
        self.password_entry.grid(row=5, column=0, pady=(0, 15), sticky="ew")
        
        # Confirm Password
        ctk.CTkLabel(form_frame, text="Confirmar Contraseña", anchor="w").grid(row=6, column=0, sticky="w", pady=(0, 5))
        self.confirm_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Repite tu contraseña",
            show="•",
            height=35
        )
        self.confirm_entry.grid(row=7, column=0, pady=(0, 20), sticky="ew")
        
        # Botón registro
        self.register_button = ctk.CTkButton(
            form_frame,
            text="Crear Cuenta",
            height=40,
            command=self._on_register,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.register_button.grid(row=8, column=0, pady=(0, 15), sticky="ew")
        
        # Botón volver
        back_button = ctk.CTkButton(
            form_frame,
            text="← Volver",
            height=35,
            fg_color="transparent",
            border_width=1,
            command=self.on_back,
            font=ctk.CTkFont(size=12)
        )
        back_button.grid(row=9, column=0, pady=(0, 20), sticky="ew")
        
        # Error label
        self.error_label = ctk.CTkLabel(
            form_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(size=12),
            wraplength=350
        )
        self.error_label.grid(row=10, column=0, pady=(10, 0))
        
        # Bind Enter
        self.username_entry.bind("<Return>", lambda e: self.email_entry.focus())
        self.email_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.confirm_entry.focus())
        self.confirm_entry.bind("<Return>", lambda e: self._on_register())
        
        self.username_entry.focus()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _on_register(self):
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        
        # Validaciones
        is_valid, error = validate_username(username)
        if not is_valid:
            self.show_error(f"Nombre de usuario inválido: {error}")
            return
        
        is_valid, error = validate_email(email)
        if not is_valid:
            self.show_error(f"Email inválido: {error}")
            return
        
        is_valid, error = validate_password(password)
        if not is_valid:
            self.show_error(f"Contraseña inválida: {error}")
            return
        
        if password != confirm:
            self.show_error("Las contraseñas no coinciden")
            return
        
        self.on_register_success(username, email, password)
    
    def show_error(self, message: str):
        self.error_label.configure(text=message)
    
    def show_success(self, message: str):
        self.error_label.configure(text=message, text_color="green")
    
    def clear_fields(self):
        self.username_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.confirm_entry.delete(0, "end")
        self.error_label.configure(text="")
