"""
Modal para configurar servidor
"""
import customtkinter as ctk
from typing import Callable, Optional
from src_Client_Server.Client.models.server import Server, ServerUpdate
from src_Client_Server.Client.models.enums import ConnectionType, SecurityLevel
from src_Client_Server.Client.network.service import TCPClient, NetworkMessage
from src_Client_Server.Client.utils.config_manager import ConfigManager
from src_Client_Server.Client.utils.logger import setup_logger
import threading

logger = setup_logger(__name__)


class ServerSettingsModal(ctk.CTkToplevel):
    """Ventana modal para configurar servidor"""
    
    def __init__(self, master, server_id: str, user_id: str, on_save: Callable):
        super().__init__(master)
        
        self.server_id = server_id
        self.user_id = user_id
        self.on_save = on_save
        
        # Cliente de red para comunicarse con el servidor
        self.network_service = TCPClient()
        self.server: Optional[Server] = None
        self.response_received = False
        self.response_data = None
        self.response_event = threading.Event()
        
        # Registrar callback para respuestas
        self.network_service.register_callback('message', self._on_message_received)
        
        # Conectar al servidor
        self._connect_to_server()
        
        # Cargar datos del servidor
        self._load_server()
        
        # Si no se pudo cargar o no tiene permisos, cerrar
        if not self.server:
            self.after(100, self.destroy)
            return
        
        self.title("Configuración del Servidor")
        self.geometry("500x700")
        self.resizable(False, False)
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        
        self._build_ui()
    
    def _connect_to_server(self):
        """Conecta al servidor"""
        server_host, server_port = ConfigManager.get_server_config()
        if not self.network_service.connect(server_host, server_port):
            self._show_error("No se pudo conectar al servidor")
            return False
        # Iniciar procesamiento de mensajes en segundo plano
        threading.Thread(target=self.network_service.start_processing, daemon=True).start()
        return True
    
    def _on_message_received(self, data):
        """Maneja los mensajes recibidos del servidor"""
        message = data.get('message')
        if not message:
            return
        # Procesar respuestas específicas
        if message.type == "get_server_response":
            self.response_data = message.data
            self.response_received = True
            self.response_event.set()
        elif message.type == "update_server_response":
            self.response_data = message.data
            self.response_received = True
            self.response_event.set()
    
    def _load_server(self):
        """Carga los datos del servidor"""
        # Enviar solicitud al servidor
        get_server_message = NetworkMessage(
            type="get_server",
            data={"server_id": self.server_id, "user_id": self.user_id},
            sender_id=self.user_id
        )
        
        if not self.network_service.send(get_server_message):
            self._show_error("Error enviando solicitud al servidor")
            return False
        
        # Esperar respuesta
        if not self.response_event.wait(timeout=5.0):
            self._show_error("Timeout esperando respuesta del servidor")
            return False
        
        if not self.response_received or not self.response_data:
            self._show_error("No se recibió respuesta del servidor")
            return False
        
        if not self.response_data.get("success"):
            error_msg = self.response_data.get("error", "Error desconocido")
            self._show_error(f"Error del servidor: {error_msg}")
            return False
        
        server_dict = self.response_data.get("server")
        if not server_dict:
            self._show_error("Servidor no encontrado")
            return False
        
        self.server = Server(**server_dict)
        if self.server.owner_id != self.user_id:
            self._show_error("No tienes permiso para modificar este servidor")
            self.server = None
            return False
        
        self.response_received = False
        self.response_data = None
        self.response_event.clear()
        return True
    
    def _build_ui(self):
        """Construye la interfaz"""
        # Título
        title = ctk.CTkLabel(
            self,
            text="⚙️ Configuración del Servidor",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 30), padx=30, sticky="w")
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(self, height=500)
        form_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        form_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Nombre del servidor
        ctk.CTkLabel(form_frame, text="Nombre del servidor *", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.name_entry = ctk.CTkEntry(form_frame, height=35)
        self.name_entry.insert(0, self.server.name)
        self.name_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # if self.server is None:
        #     return

        # Descripción
        ctk.CTkLabel(form_frame, text="Descripción", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.description_entry = ctk.CTkEntry(form_frame, height=35)
        if self.server.description:
            self.description_entry.insert(0, self.server.description)
        self.description_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Icono (URL)
        ctk.CTkLabel(form_frame, text="Icono (URL de imagen)", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.icon_entry = ctk.CTkEntry(form_frame, height=35)
        if self.server.icon:
            self.icon_entry.insert(0, self.server.icon)
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
        self.connection_type.set(self.server.connection_type.value)
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
        self.security_level.set(self.server.security_level.value)
        self.security_level.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Máximo de miembros
        ctk.CTkLabel(form_frame, text="Máximo de miembros", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.max_members = ctk.CTkEntry(form_frame, height=35)
        self.max_members.insert(0, str(self.server.max_members))
        self.max_members.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Separador
        ctk.CTkLabel(form_frame, text="Características", 
                    font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, columnspan=2, pady=(20, 10), sticky="w")
        row += 1
        
        # Transferencia de archivos
        self.file_transfer_var = ctk.BooleanVar(value=self.server.allow_file_transfer)
        file_transfer_check = ctk.CTkCheckBox(
            form_frame,
            text="Permitir transferencia de archivos",
            variable=self.file_transfer_var
        )
        file_transfer_check.grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky="w")
        row += 1
        
        # Video streaming
        self.video_streaming_var = ctk.BooleanVar(value=self.server.allow_video_streaming)
        video_check = ctk.CTkCheckBox(
            form_frame,
            text="Permitir video/audio streaming",
            variable=self.video_streaming_var
        )
        video_check.grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky="w")
        row += 1
        
        # Verificación requerida
        self.verification_var = ctk.BooleanVar(value=self.server.require_verification)
        verification_check = ctk.CTkCheckBox(
            form_frame,
            text="Requerir verificación para unirse",
            variable=self.verification_var
        )
        verification_check.grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky="w")
        row += 1
        
        # Separador informativo
        info_label = ctk.CTkLabel(
            form_frame,
            text="Nota: Algunos cambios pueden afectar a todos los miembros del servidor.",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
            wraplength=400
        )
        info_label.grid(row=row, column=0, columnspan=2, pady=20, sticky="w")
        
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
        
        save_btn = ctk.CTkButton(
            button_frame,
            text="Guardar Cambios",
            height=40,
            command=self._on_save,
            font=ctk.CTkFont(weight="bold")
        )
        save_btn.grid(row=0, column=1, sticky="ew")
    
    def _on_save(self):
        """Guarda los cambios del servidor"""
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("El nombre del servidor es obligatorio")
            return
        
        try:
            max_members = int(self.max_members.get() or 100)
            if max_members < 1 or max_members > 10000:
                raise ValueError()
        except ValueError:
            self._show_error("Máximo de miembros debe ser un número entre 1 y 10000")
            return
        
        # Preparar datos de actualización
        update_data = {
            'name': name,
            'description': self.description_entry.get().strip() or None,
            'icon': self.icon_entry.get().strip() or None,
            'connection_type': ConnectionType(self.connection_type.get()).value,
            'security_level': SecurityLevel(self.security_level.get()).value,
            'max_members': max_members,
            'allow_file_transfer': self.file_transfer_var.get(),
            'allow_video_streaming': self.video_streaming_var.get(),
            'require_verification': self.verification_var.get()
        }
        
        # Enviar solicitud al servidor
        update_server_message = NetworkMessage(
            type="update_server",
            data={'server_id': self.server_id, 'user_id': self.user_id, **update_data},
            sender_id=self.user_id
        )
        
        if not self.network_service.send(update_server_message):
            self._show_error("Error enviando solicitud al servidor")
            return
        
        if not self.response_event.wait(timeout=5.0):
            self._show_error("Timeout esperando respuesta del servidor")
            return
        
        if not self.response_received or not self.response_data:
            self._show_error("No se recibió respuesta del servidor")
            return
        
        if not self.response_data.get("success"):
            error_msg = self.response_data.get("error", "Error desconocido")
            self._show_error(f"Error del servidor: {error_msg}")
            return
        
        updated_server_dict = self.response_data.get("server")
        if not updated_server_dict:
            self._show_error("Servidor no actualizado")
            return
        
        updated_server = Server(**updated_server_dict)
        if self.on_save:
            self.on_save(updated_server)
        self.destroy()
    
    def _show_error(self, message: str):
        """Muestra mensaje de error"""
        error_win = ctk.CTkToplevel(self)
        error_win.title("Error")
        error_win.geometry("300x100")
        error_win.resizable(False, False)
        error_win.transient(self)
        error_win.grab_set()
        
        label = ctk.CTkLabel(error_win, text=message, wraplength=250)
        label.pack(expand=True, padx=20, pady=20)
        
        btn = ctk.CTkButton(error_win, text="OK", command=error_win.destroy)
        btn.pack(pady=(0, 10))
        
        # Centrar
        error_win.update_idletasks()
        w = error_win.winfo_width()
        h = error_win.winfo_height()
        x = (error_win.winfo_screenwidth() // 2) - (w // 2)
        y = (error_win.winfo_screenheight() // 2) - (h // 2)
        error_win.geometry(f'{w}x{h}+{x}+{y}')
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
