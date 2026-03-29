"""
Modal para crear servidor
"""
import customtkinter as ctk
from typing import Callable, Dict, Any
from ..models.enums import ConnectionType, SecurityLevel


class CreateServerModal(ctk.CTkToplevel):
    """Ventana modal para crear servidor"""
    
    def __init__(self, master, on_create: Callable):
        super().__init__(master)
        
        self.title("Crear Servidor")
        self.geometry("500x700")
        self.resizable(False, False)
        self.on_create = on_create
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        
        # Título
        title = ctk.CTkLabel(
            self,
            text="🏰 Crear Servidor",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 30), padx=30, sticky="w")
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(self, height=500)
        form_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        form_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Nombre
        ctk.CTkLabel(form_frame, text="Nombre del servidor *", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.name_entry = ctk.CTkEntry(form_frame, height=35)
        self.name_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Descripción
        ctk.CTkLabel(form_frame, text="Descripción", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.description_entry = ctk.CTkEntry(form_frame, height=35)
        self.description_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Icono (placeholder)
        ctk.CTkLabel(form_frame, text="Icono (URL)", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.icon_entry = ctk.CTkEntry(form_frame, height=35)
        self.icon_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Separador
        ctk.CTkLabel(form_frame, text="Configuración de Conexión", 
                    font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, columnspan=2, pady=(20, 10), sticky="w")
        row += 1
        
        # Tipo de conexión
        ctk.CTkLabel(form_frame, text="Tipo de conectividad", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.connection_type = ctk.CTkComboBox(
            form_frame,
            values=["client_server", "p2p", "hybrid"],
            height=35
        )
        self.connection_type.set("client_server")
        self.connection_type.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Nivel de seguridad
        ctk.CTkLabel(form_frame, text="Nivel de seguridad", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.security_level = ctk.CTkComboBox(
            form_frame,
            values=["none", "basic", "encrypted", "e2e"],
            height=35
        )
        self.security_level.set("encrypted")
        self.security_level.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Máximo de miembros
        ctk.CTkLabel(form_frame, text="Máximo de miembros", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.max_members = ctk.CTkEntry(form_frame, height=35)
        self.max_members.insert(0, "100")
        self.max_members.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Separador
        ctk.CTkLabel(form_frame, text="Características", 
                    font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, columnspan=2, pady=(20, 10), sticky="w")
        row += 1
        
        # Transferencia de archivos
        self.file_transfer_var = ctk.BooleanVar(value=True)
        file_transfer_check = ctk.CTkCheckBox(
            form_frame,
            text="Permitir transferencia de archivos",
            variable=self.file_transfer_var
        )
        file_transfer_check.grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky="w")
        row += 1
        
        # Video streaming
        self.video_streaming_var = ctk.BooleanVar(value=True)
        video_check = ctk.CTkCheckBox(
            form_frame,
            text="Permitir video/audio streaming",
            variable=self.video_streaming_var
        )
        video_check.grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky="w")
        row += 1
        
        # Verificación requerida
        self.verification_var = ctk.BooleanVar(value=False)
        verification_check = ctk.CTkCheckBox(
            form_frame,
            text="Requerir verificación para unirse",
            variable=self.verification_var
        )
        verification_check.grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky="w")
        row += 1
        
        # Botones
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=30, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancelar",
            height=40,
            fg_color="transparent",
            border_width=2,
            command=self.destroy
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        create_btn = ctk.CTkButton(
            button_frame,
            text="Crear Servidor",
            height=40,
            command=self._on_create,
            font=ctk.CTkFont(weight="bold")
        )
        create_btn.grid(row=0, column=1, sticky="ew")
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _on_create(self):
        """Crea el servidor"""
        name = self.name_entry.get().strip()
        if not name:
            return
        
        data = {
            'name': name,
            'description': self.description_entry.get().strip() or None,
            'icon': self.icon_entry.get().strip() or None,
            'connection_type': self.connection_type.get(),
            'security_level': self.security_level.get(),
            'max_members': int(self.max_members.get() or 100),
            'allow_file_transfer': self.file_transfer_var.get(),
            'allow_video_streaming': self.video_streaming_var.get(),
            'require_verification': self.verification_var.get()
        }
        
        self.on_create(**data)
        self.destroy()
