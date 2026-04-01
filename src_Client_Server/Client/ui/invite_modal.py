"""
Modal para gestionar invitaciones a un servidor
"""
import customtkinter as ctk
from typing import Optional, List, Dict, Any
from src_Client_Server.Client.network.service import TCPClient, NetworkMessage
from src_Client_Server.Client.utils.config_manager import ConfigManager
from src_Client_Server.Client.utils.logger import setup_logger
import threading

logger = setup_logger(__name__)


class InviteModal(ctk.CTkToplevel):
    """Ventana modal para gestionar invitaciones"""
    
    def __init__(self, master, server_id: str, server_name: str, user_id: str):
        super().__init__(master)
        
        self.server_id = server_id
        self.server_name = server_name
        self.user_id = user_id
        
        # Cliente de red
        self.network_service = TCPClient()
        self.response_event = threading.Event()
        self.response_data = None
        
        self.network_service.register_callback('message', self._on_message_received)
        self._connect_to_server()
        
        self.title(f"Invitaciones - {server_name}")
        self.geometry("500x450")
        self.resizable(False, False)
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.invites: List[Dict] = []
        
        self._build_ui()
        self._load_invites()
    
    def _connect_to_server(self):
        server_host, server_port = ConfigManager.get_server_config()
        if not self.network_service.connect(server_host, server_port):
            return False
        threading.Thread(target=self.network_service.start_processing, daemon=True).start()
        return True
    
    def _on_message_received(self, data):
        message = data.get('message')
        if not message:
            return
        if message.type in ["create_invite_response", "get_server_invites_response",
                           "revoke_invite_response", "accept_invite_response"]:
            self.response_data = message.data
            self.response_event.set()
    
    def _build_ui(self):
        # Título
        title = ctk.CTkLabel(
            self,
            text="🔗 Invitaciones",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 15), padx=30, sticky="w")
        
        # Panel principal
        main_frame = ctk.CTkScrollableFrame(self, height=280)
        main_frame.grid(row=1, column=0, padx=30, pady=(0, 10), sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        self.invites_frame = main_frame
        
        # Sección para crear nueva invitación
        create_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray20"))
        create_frame.grid(row=2, column=0, padx=30, pady=(0, 10), sticky="ew")
        create_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(create_frame, text="Max usos:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.max_uses_entry = ctk.CTkEntry(create_frame, width=60, height=30)
        self.max_uses_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(create_frame, text="Expira (horas):", font=ctk.CTkFont(size=12)).grid(
            row=0, column=2, padx=(10, 5), pady=5, sticky="w")
        self.expires_entry = ctk.CTkEntry(create_frame, width=60, height=30)
        self.expires_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        create_btn = ctk.CTkButton(
            create_frame,
            text="Crear Invitación",
            height=30,
            command=self._create_invite,
            fg_color=("#7289DA", "#7289DA")
        )
        create_btn.grid(row=0, column=4, padx=10, pady=5)
        
        # Botón cerrar
        close_btn = ctk.CTkButton(
            self,
            text="Cerrar",
            height=35,
            command=self.destroy,
            fg_color="transparent",
            border_width=2
        )
        close_btn.grid(row=3, column=0, padx=30, pady=(0, 15), sticky="ew")
    
    def _load_invites(self):
        """Carga las invitaciones del servidor"""
        msg = NetworkMessage(
            type="get_server_invites",
            data={"server_id": self.server_id, "user_id": self.user_id},
            sender_id=self.user_id
        )
        
        if not self.network_service.send(msg):
            return
        
        if not self.response_event.wait(timeout=5.0):
            return
        
        if self.response_data and self.response_data.get("success"):
            self.invites = self.response_data.get("invites", [])
            self.after(0, self._render_invites)
        
        self.response_event.clear()
    
    def _render_invites(self):
        """Renderiza la lista de invitaciones"""
        for widget in self.invites_frame.winfo_children():
            widget.destroy()
        
        if not self.invites:
            ctk.CTkLabel(
                self.invites_frame,
                text="No hay invitaciones activas",
                text_color="gray60"
            ).pack(pady=20)
            return
        
        for invite in self.invites:
            self._create_invite_row(invite)
    
    def _create_invite_row(self, invite: dict):
        """Crea una fila para una invitación"""
        row_frame = ctk.CTkFrame(self.invites_frame, fg_color=("gray90", "gray15"))
        row_frame.pack(pady=3, fill="x")
        row_frame.grid_columnconfigure(1, weight=1)
        
        # Código
        code_label = ctk.CTkLabel(
            row_frame,
            text=invite.get('code', ''),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#7289DA"
        )
        code_label.grid(row=0, column=0, padx=10, pady=8)
        
        # Info
        uses = invite.get('uses', 0)
        max_uses = invite.get('max_uses') or "∞"
        info_text = f"Usos: {uses}/{max_uses}"
        
        expires_at = invite.get('expires_at')
        if expires_at:
            info_text += f" | Expira: {expires_at[:16]}"
        
        info_label = ctk.CTkLabel(
            row_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        info_label.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        # Botón copiar
        copy_btn = ctk.CTkButton(
            row_frame,
            text="📋",
            width=30,
            height=28,
            fg_color="transparent",
            border_width=1,
            command=lambda c=invite.get('code', ''): self._copy_code(c)
        )
        copy_btn.grid(row=0, column=2, padx=2, pady=5)
        
        # Botón revocar
        revoke_btn = ctk.CTkButton(
            row_frame,
            text="🗑️",
            width=30,
            height=28,
            fg_color="transparent",
            border_width=1,
            hover_color=("#FF6B6B", "#C44D4D"),
            command=lambda inv=invite: self._revoke_invite(inv)
        )
        revoke_btn.grid(row=0, column=3, padx=(2, 5), pady=5)
    
    def _create_invite(self):
        """Crea una nueva invitación"""
        max_uses_str = self.max_uses_entry.get().strip()
        expires_str = self.expires_entry.get().strip()
        
        max_uses = int(max_uses_str) if max_uses_str else None
        expires_hours = int(expires_str) if expires_str else None
        
        msg = NetworkMessage(
            type="create_invite",
            data={
                "server_id": self.server_id,
                "user_id": self.user_id,
                "max_uses": max_uses,
                "expires_in_hours": expires_hours
            },
            sender_id=self.user_id
        )
        
        if not self.network_service.send(msg):
            return
        
        if not self.response_event.wait(timeout=5.0):
            return
        
        if self.response_data and self.response_data.get("success"):
            invite = self.response_data.get("invite", {})
            self.invites.append(invite)
            self._render_invites()
            self.max_uses_entry.delete(0, "end")
            self.expires_entry.delete(0, "end")
        
        self.response_event.clear()
    
    def _revoke_invite(self, invite: dict):
        """Revoca una invitación"""
        msg = NetworkMessage(
            type="revoke_invite",
            data={
                "invite_id": invite.get('id'),
                "user_id": self.user_id
            },
            sender_id=self.user_id
        )
        
        if not self.network_service.send(msg):
            return
        
        if not self.response_event.wait(timeout=5.0):
            return
        
        if self.response_data and self.response_data.get("success"):
            self.invites = [i for i in self.invites if i.get('id') != invite.get('id')]
            self._render_invites()
        
        self.response_event.clear()
    
    def _copy_code(self, code: str):
        """Copia el código de invitación al portapapeles"""
        self.clipboard_clear()
        self.clipboard_append(code)
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


class AcceptInviteDialog(ctk.CTkToplevel):
    """Diálogo para unirse a un servidor con código de invitación"""
    
    def __init__(self, master, user_id: str, on_success=None):
        super().__init__(master)
        
        self.user_id = user_id
        self.on_success = on_success
        
        self.network_service = TCPClient()
        self.response_event = threading.Event()
        self.response_data = None
        
        self.network_service.register_callback('message', self._on_message_received)
        self._connect_to_server()
        
        self.title("Unirse a servidor")
        self.geometry("400x200")
        self.resizable(False, False)
        
        self.center_window()
        self._build_ui()
    
    def _connect_to_server(self):
        server_host, server_port = ConfigManager.get_server_config()
        self.network_service.connect(server_host, server_port)
        threading.Thread(target=self.network_service.start_processing, daemon=True).start()
    
    def _on_message_received(self, data):
        message = data.get('message')
        if not message:
            return
        if message.type == "accept_invite_response":
            self.response_data = message.data
            self.response_event.set()
    
    def _build_ui(self):
        title = ctk.CTkLabel(
            self,
            text="Unirse a un servidor",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(20, 10))
        
        ctk.CTkLabel(self, text="Código de invitación:").pack(pady=(10, 5))
        
        self.code_entry = ctk.CTkEntry(self, width=250, height=35, placeholder_text="Ej: ABC12345")
        self.code_entry.pack(pady=5)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15, padx=30, fill="x")
        btn_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkButton(
            btn_frame, text="Cancelar", height=35,
            fg_color="transparent", border_width=2,
            command=self.destroy
        ).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        ctk.CTkButton(
            btn_frame, text="Unirse", height=35,
            command=self._accept_invite,
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=1, sticky="ew")
    
    def _accept_invite(self):
        code = self.code_entry.get().strip().upper()
        if not code:
            return
        
        msg = NetworkMessage(
            type="accept_invite",
            data={"user_id": self.user_id, "code": code},
            sender_id=self.user_id
        )
        
        if not self.network_service.send(msg):
            return
        
        if not self.response_event.wait(timeout=5.0):
            return
        
        if self.response_data and self.response_data.get("success"):
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            error = self.response_data.get("error", "Error desconocido") if self.response_data else "Error"
            self._show_error(error)
        
        self.response_event.clear()
    
    def _show_error(self, message: str):
        error_win = ctk.CTkToplevel(self)
        error_win.title("Error")
        error_win.geometry("300x100")
        error_win.resizable(False, False)
        error_win.transient(self)
        error_win.grab_set()
        
        ctk.CTkLabel(error_win, text=message, wraplength=250).pack(expand=True, padx=20, pady=20)
        ctk.CTkButton(error_win, text="OK", command=error_win.destroy).pack(pady=(0, 10))
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
