"""
Modal para crear canal
"""
import customtkinter as ctk
from typing import Callable
from models.enums import ChannelType


class CreateChannelModal(ctk.CTkToplevel):
    """Ventana modal para crear canal"""
    
    def __init__(self, master, server_id: str, on_create: Callable):
        super().__init__(master)
        
        self.title("Crear Canal")
        self.geometry("400x600")
        self.resizable(False, False)
        self.server_id = server_id
        self.on_create = on_create
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        
        # Título
        title = ctk.CTkLabel(
            self,
            text="# Crear Canal",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 30), padx=30, sticky="w")
        
        # Formulario
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="ew")
        form_frame.grid_columnconfigure(0, weight=1)
        
        # Nombre
        ctk.CTkLabel(form_frame, text="Nombre del canal *", anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        self.name_entry = ctk.CTkEntry(form_frame, height=35)
        self.name_entry.grid(row=1, column=0, pady=(0, 15), sticky="ew")
        
        # Tipo
        ctk.CTkLabel(form_frame, text="Tipo de canal", anchor="w").grid(
            row=2, column=0, sticky="w", pady=(0, 5))
        self.type_combo = ctk.CTkComboBox(
            form_frame,
            values=["text", "voice", "video"],
            height=35
        )
        self.type_combo.set("text")
        self.type_combo.grid(row=3, column=0, pady=(0, 15), sticky="ew")
        
        # Tema/Topic
        ctk.CTkLabel(form_frame, text="Tema o descripción", anchor="w").grid(
            row=4, column=0, sticky="w", pady=(0, 5))
        self.topic_entry = ctk.CTkEntry(form_frame, height=35)
        self.topic_entry.grid(row=5, column=0, pady=(0, 15), sticky="ew")
        
        # Canal privado
        self.private_var = ctk.BooleanVar(value=False)
        private_check = ctk.CTkCheckBox(
            form_frame,
            text="Canal privado (solo roles específicos)",
            variable=self.private_var,
            command=self._toggle_roles
        )
        private_check.grid(row=6, column=0, pady=(0, 15), sticky="w")
        
        # Roles permitidos (inicialmente oculto)
        self.roles_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.roles_frame.grid(row=7, column=0, pady=(0, 15), sticky="ew")
        self.roles_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.roles_frame, text="Roles permitidos (separados por comas)", 
                    anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.roles_entry = ctk.CTkEntry(self.roles_frame, height=35, state="disabled")
        self.roles_entry.grid(row=1, column=0, sticky="ew")
        
        # Posición
        ctk.CTkLabel(form_frame, text="Posición", anchor="w").grid(
            row=8, column=0, sticky="w", pady=(0, 5))
        self.position_entry = ctk.CTkEntry(form_frame, height=35)
        self.position_entry.insert(0, "0")
        self.position_entry.grid(row=9, column=0, pady=(0, 20), sticky="ew")
        
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
            text="Crear Canal",
            height=40,
            command=self._on_create,
            font=ctk.CTkFont(weight="bold")
        )
        create_btn.grid(row=0, column=1, sticky="ew")
        
        # Bind Enter
        self.name_entry.bind("<Return>", lambda e: self._on_create())
        self.name_entry.focus()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _toggle_roles(self):
        """Muestra/oculta el campo de roles"""
        if self.private_var.get():
            self.roles_entry.configure(state="normal")
        else:
            self.roles_entry.configure(state="disabled")
    
    def _on_create(self):
        """Crea el canal"""
        name = self.name_entry.get().strip()
        if not name:
            return
        
        allowed_roles = []
        if self.private_var.get():
            roles_text = self.roles_entry.get().strip()
            if roles_text:
                allowed_roles = [r.strip() for r in roles_text.split(',')]
        
        data = {
            'name': name,
            'type': ChannelType(self.type_combo.get()),
            'server_id': self.server_id,
            'topic': self.topic_entry.get().strip() or None,
            'position': int(self.position_entry.get() or 0),
            'is_private': self.private_var.get(),
            'allowed_roles': allowed_roles
        }
        
        self.on_create(**data)
        self.destroy()
