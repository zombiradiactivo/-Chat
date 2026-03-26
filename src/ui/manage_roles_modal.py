"""
Modal para gestionar roles de un servidor
"""
import customtkinter as ctk
from typing import Callable, List, Dict, Any, Optional
from models.role import Role, RoleCreate, RoleUpdate
from models.enums import Permission
from services import ServerService, PermissionService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ManageRolesModal(ctk.CTkToplevel):
    """Ventana modal para gestionar roles de un servidor"""
    
    def __init__(self, master, server_id: str, user_id: str, on_save: Callable):
        super().__init__(master)
        
        self.server_id = server_id
        self.user_id = user_id
        self.on_save = on_save
        
        self.server_service = ServerService()
        self.permission_service = PermissionService()
        
        # Obtener roles del servidor
        self.roles: List[Role] = []
        self._load_roles()
        
        self.title("Gestionar Roles")
        self.geometry("700x600")
        self.resizable(False, False)
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._build_ui()
    
    def _load_roles(self):
        """Carga los roles del servidor"""
        from repositories import RepositoryFactory
        roles_repo = RepositoryFactory().get_repository('roles')
        self.roles = roles_repo.get_by_server(self.server_id)
        # Ordenar por posición
        self.roles.sort(key=lambda r: r.position)
    
    def _build_ui(self):
        """Construye la interfaz"""
        # Título
        title = ctk.CTkLabel(
            self,
            text="👥 Gestionar Roles",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 15), padx=30, sticky="w")
        
        # Panel principal con scroll
        main_frame = ctk.CTkScrollableFrame(self, height=450)
        main_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Sección de roles
        row = 0
        
        roles_label = ctk.CTkLabel(
            main_frame,
            text="Roles del servidor",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        roles_label.grid(row=row, column=0, pady=(0, 10), sticky="w")
        row += 1
        
        # Frame para la lista de roles
        self.roles_list_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.roles_list_frame.grid(row=row, column=0, pady=(0, 20), sticky="ew")
        self.roles_list_frame.grid_columnconfigure(1, weight=1)
        row += 1
        
        self._render_roles_list()
        
        # Separador
        separator = ctk.CTkFrame(main_frame, height=2, fg_color=("gray70", "gray30"))
        separator.grid(row=row, column=0, pady=10, sticky="ew")
        row += 1
        
        # Botón para crear nuevo rol
        self.create_role_btn = ctk.CTkButton(
            main_frame,
            text="＋ Crear Nuevo Rol",
            height=40,
            command=self._on_create_role,
            fg_color=("#7289DA", "#7289DA"),
            hover_color=("#5B7EBD", "#5B7EBD")
        )
        self.create_role_btn.grid(row=row, column=0, pady=10, sticky="w")
        
        # Botones inferiores
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
            command=self._on_save_changes,
            font=ctk.CTkFont(weight="bold")
        )
        save_btn.grid(row=0, column=1, sticky="ew")
    
    def _render_roles_list(self):
        """Renderiza la lista de roles"""
        # Limpiar frame
        for widget in self.roles_list_frame.winfo_children():
            widget.destroy()
        
        # Verificar permisos
        can_manage = self.permission_service.has_permission(
            self.user_id, self.server_id, Permission.MANAGE_ROLES
        )
        
        # Dueño siempre puede
        server = self.server_service.get_server(self.server_id)
        if server and server.owner_id == self.user_id:
            can_manage = True
        
        for idx, role in enumerate(self.roles):
            self._create_role_row(self.roles_list_frame, role, idx, can_manage)
    
    def _create_role_row(self, parent: ctk.CTkFrame, role: Role, index: int, can_manage: bool):
        """Crea una fila para un rol"""
        row_frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray15"))
        row_frame.grid(row=index, column=0, columnspan=3, pady=5, sticky="ew")
        row_frame.grid_columnconfigure(2, weight=1)
        
        # Botones de reordenar
        if can_manage and not role.is_default:
            up_btn = ctk.CTkButton(
                row_frame,
                text="↑",
                width=30,
                height=30,
                command=lambda r=role: self._move_role_up(r),
                fg_color="transparent",
                border_width=1
            )
            up_btn.grid(row=0, column=0, padx=5, pady=5)
            
            down_btn = ctk.CTkButton(
                row_frame,
                text="↓",
                width=30,
                height=30,
                command=lambda r=role: self._move_role_down(r),
                fg_color="transparent",
                border_width=1
            )
            down_btn.grid(row=0, column=1, padx=(0, 5), pady=5)
        else:
            # Espacio para alinear
            spacer = ctk.CTkLabel(row_frame, text="", width=70)
            spacer.grid(row=0, column=0, columnspan=2, padx=5)
        
        # Nombre del rol
        name_label = ctk.CTkLabel(
            row_frame,
            text=f"{role.name}",
            font=ctk.CTkFont(weight="bold"),
            anchor="w"
        )
        name_label.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
        # Color del rol
        color_label = ctk.CTkLabel(
            row_frame,
            text="   ",
            fg_color=role.color,
            corner_radius=4,
            width=20
        )
        color_label.grid(row=0, column=3, padx=5, pady=10)
        
        # Info de permisos
        perms_text = f"{len(role.permissions)} permiso(s)"
        perms_label = ctk.CTkLabel(
            row_frame,
            text=perms_text,
            text_color="gray60",
            anchor="w"
        )
        perms_label.grid(row=0, column=4, padx=10, pady=10, sticky="w")
        
        # Botones de acción
        if can_manage and not role.is_default:
            edit_btn = ctk.CTkButton(
                row_frame,
                text="✏️",
                width=40,
                height=30,
                command=lambda r=role: self._on_edit_role(r),
                fg_color="transparent",
                border_width=1
            )
            edit_btn.grid(row=0, column=5, padx=5, pady=5)
            
            delete_btn = ctk.CTkButton(
                row_frame,
                text="🗑️",
                width=40,
                height=30,
                command=lambda r=role: self._on_delete_role(r),
                fg_color="transparent",
                border_width=1,
                hover_color=("#FF6B6B", "#C44D4D")
            )
            delete_btn.grid(row=0, column=6, padx=(0, 5), pady=5)
        else:
            # Espacio para alinear
            spacer2 = ctk.CTkLabel(row_frame, text="", width=100)
            spacer2.grid(row=0, column=5, columnspan=2, padx=5)
    
    def _move_role_up(self, role: Role):
        """Mueve el rol hacia arriba en la jerarquía"""
        if role.position <= 0:
            return
        
        # Encontrar el rol con posición anterior
        target_role = None
        for r in self.roles:
            if r.position == role.position - 1:
                target_role = r
                break
        
        if not target_role:
            return
        
        # Intercambiar posiciones
        old_pos = role.position
        role.position = target_role.position
        target_role.position = old_pos
        
        self._render_roles_list()
    
    def _move_role_down(self, role: Role):
        """Mueve el rol hacia abajo en la jerarquía"""
        if role.position >= len(self.roles) - 1:
            return
        
        # Encontrar el rol con posición siguiente
        target_role = None
        for r in self.roles:
            if r.position == role.position + 1:
                target_role = r
                break
        
        if not target_role:
            return
        
        # Intercambiar posiciones
        old_pos = role.position
        role.position = target_role.position
        target_role.position = old_pos
        
        self._render_roles_list()
    
    def _on_create_role(self):
        """Abre modal para crear nuevo rol"""
        EditRoleModal(self, self.server_id, None, self._on_role_saved)
    
    def _on_edit_role(self, role: Role):
        """Abre modal para editar rol"""
        EditRoleModal(self, self.server_id, role, self._on_role_saved)
    
    def _on_delete_role(self, role: Role):
        """Elimina un rol"""
        # Verificar que no sea el último rol no-default (mínimo debe quedar @everyone)
        non_default_roles = [r for r in self.roles if not r.is_default]
        if len(non_default_roles) <= 1 and not role.is_default:
            self._show_error("No se puede eliminar el último rol personalizado")
            return
        
        # Confirmar
        confirm = ctk.CTkInputDialog(
            title="Confirmar",
            text=f"¿Eliminar el rol '{role.name}'?"
        )
        result = confirm.get_input()
        if result != "ok":
            return
        
        # Eliminar
        from repositories import RepositoryFactory
        roles_repo = RepositoryFactory().get_repository('roles')
        success = roles_repo.delete(role.id)
        
        if success:
            self._load_roles()
            self._render_roles_list()
        else:
            self._show_error("Error al eliminar el rol")
    
    def _on_role_saved(self, role_data: Dict[str, Any], is_new: bool):
        """Callback cuando se guarda un rol (desde EditRoleModal)"""
        from repositories import RepositoryFactory
        roles_repo = RepositoryFactory().get_repository('roles')
        
        if is_new:
            # Crear nuevo rol
            role_create = RoleCreate(
                server_id=self.server_id,
                name=role_data['name'],
                color=role_data.get('color', '#99AAB5'),
                permissions=role_data.get('permissions', []),
                mentionable=role_data.get('mentionable', False),
                hoisted=role_data.get('hoisted', False)
            )
            roles_repo.create(role_create.dict())
        else:
            # Actualizar rol existente
            role_update = RoleUpdate(
                name=role_data.get('name'),
                color=role_data.get('color'),
                permissions=role_data.get('permissions'),
                mentionable=role_data.get('mentionable'),
                hoisted=role_data.get('hoisted')
            )
            roles_repo.update(role_data['id'], role_update.dict(exclude_none=True))
        
        self._load_roles()
        self._render_roles_list()
    
    def _on_save_changes(self):
        """Guarda los cambios de reordenación"""
        # Recolectar posiciones actuales
        positions = {}
        for role in self.roles:
            positions[role.id] = role.position
        
        # Guardar reordenación
        from repositories import RepositoryFactory
        roles_repo = RepositoryFactory().get_repository('roles')
        roles_repo.reorder_roles(self.server_id, positions)
        
        if self.on_save:
            self.on_save()
        
        self.destroy()
    
    def _show_error(self, message: str):
        """Muestra un mensaje de error"""
        error_window = ctk.CTkToplevel(self)
        error_window.title("Error")
        error_window.geometry("300x100")
        error_window.resizable(False, False)
        error_window.transient(self)
        error_window.grab_set()
        
        label = ctk.CTkLabel(error_window, text=message, wraplength=250)
        label.pack(expand=True, padx=20, pady=20)
        
        btn = ctk.CTkButton(error_window, text="OK", command=error_window.destroy)
        btn.pack(pady=(0, 10))
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


class EditRoleModal(ctk.CTkToplevel):
    """Modal para crear/editar un rol"""
    
    def __init__(self, master, server_id: str, role: Optional[Role], on_save: Callable):
        super().__init__(master)
        
        self.server_id = server_id
        self.role = role
        self.on_save = on_save
        self.is_new = role is None
        
        self.title("Crear Rol" if self.is_new else "Editar Rol")
        self.geometry("500x700")
        self.resizable(False, False)
        
        self.center_window()
        self.grid_columnconfigure(0, weight=1)
        
        # Cargar permisos disponibles
        self.all_permissions = list(Permission)
        self.selected_permissions: List[str] = []
        if role:
            self.selected_permissions = role.permissions.copy()
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del formulario"""
        # Título
        title_text = "➕ Crear Rol" if self.is_new else "✏️ Editar Rol"
        title = ctk.CTkLabel(
            self,
            text=title_text,
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 30), padx=30, sticky="w")
        
        # Formulario en scrollable frame
        form_frame = ctk.CTkScrollableFrame(self, height=500)
        form_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        form_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Nombre
        ctk.CTkLabel(form_frame, text="Nombre del rol *", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.name_entry = ctk.CTkEntry(form_frame, height=35)
        if self.role:
            self.name_entry.insert(0, self.role.name)
        self.name_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Color
        ctk.CTkLabel(form_frame, text="Color (hex)", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.color_entry = ctk.CTkEntry(form_frame, height=35)
        if self.role:
            self.color_entry.insert(0, self.role.color)
        else:
            self.color_entry.insert(0, "#99AAB5")
        self.color_entry.grid(row=row, column=1, pady=(0, 15), sticky="ew")
        row += 1
        
        # Mentionable
        self.mentionable_var = ctk.BooleanVar(value=self.role.mentionable if self.role else False)
        mentionable_check = ctk.CTkCheckBox(
            form_frame,
            text="Mentionable (todos pueden @mencionar este rol)",
            variable=self.mentionable_var
        )
        mentionable_check.grid(row=row, column=0, columnspan=2, pady=(0, 15), sticky="w")
        row += 1
        
        # Hoisted
        self.hoisted_var = ctk.BooleanVar(value=self.role.hoisted if self.role else False)
        hoisted_check = ctk.CTkCheckBox(
            form_frame,
            text="Hoisted (mostrar separado en la lista de miembros)",
            variable=self.hoisted_var
        )
        hoisted_check.grid(row=row, column=0, columnspan=2, pady=(0, 15), sticky="w")
        row += 1
        
        # Separador
        ctk.CTkLabel(form_frame, text="Permisos", 
                    font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, columnspan=2, pady=(20, 10), sticky="w")
        row += 1
        
        # Permisos agrupados por categoría
        self.permission_vars: Dict[Permission, ctk.BooleanVar] = {}
        
        categories = {
            "Servidor": [
                Permission.MANAGE_SERVER,
                Permission.MANAGE_ROLES,
                Permission.MANAGE_CHANNELS,
                Permission.KICK_MEMBERS,
                Permission.BAN_MEMBERS,
                Permission.MANAGE_MESSAGES,
                Permission.CREATE_INSTANT_INVITE
            ],
            "Canal": [
                Permission.SEND_MESSAGES,
                Permission.SEND_TTS_MESSAGES,
                Permission.EMBED_LINKS,
                Permission.ATTACH_FILES,
                Permission.READ_MESSAGE_HISTORY,
                Permission.MENTION_EVERYONE,
                Permission.USE_EXTERNAL_EMOJIS
            ],
            "Voz/Video": [
                Permission.CONNECT,
                Permission.SPEAK,
                Permission.MUTE_MEMBERS,
                Permission.DEAFEN_MEMBERS,
                Permission.MOVE_MEMBERS,
                Permission.USE_VAD,
                Permission.STREAM
            ],
            "Archivos": [
                Permission.SEND_FILES,
                Permission.RECEIVE_FILES
            ]
        }
        
        for category, perms in categories.items():
            # Label de categoría
            ctk.CTkLabel(form_frame, text=category, 
                        font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=row, column=0, columnspan=2, pady=(10, 5), sticky="w")
            row += 1
            
            # Checkboxes de permisos
            for perm in perms:
                var = ctk.BooleanVar(value=perm.value in self.selected_permissions)
                self.permission_vars[perm] = var
                
                cb = ctk.CTkCheckBox(
                    form_frame,
                    text=perm.value.replace('_', ' ').title(),
                    variable=var
                )
                cb.grid(row=row, column=0, columnspan=2, pady=2, sticky="w", padx=10)
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
        
        save_text = "Crear Rol" if self.is_new else "Guardar Cambios"
        save_btn = ctk.CTkButton(
            button_frame,
            text=save_text,
            height=40,
            command=self._on_save,
            font=ctk.CTkFont(weight="bold")
        )
        save_btn.grid(row=0, column=1, sticky="ew")
    
    def _on_save(self):
        """Guarda el rol"""
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("El nombre es obligatorio")
            return
        
        # Validar color hex
        color = self.color_entry.get().strip()
        if not color.startswith('#') or len(color) != 7:
            self._show_error("Color inválido. Usa formato #RRGGBB")
            return
        
        # Recolectar permisos seleccionados
        permissions = []
        for perm, var in self.permission_vars.items():
            if var.get():
                permissions.append(perm.value)
        
        role_data = {
            'id': self.role.id if self.role else None,
            'name': name,
            'color': color,
            'mentionable': self.mentionable_var.get(),
            'hoisted': self.hoisted_var.get(),
            'permissions': permissions
        }
        
        self.on_save(role_data, self.is_new)
        self.destroy()
    
    def _show_error(self, message: str):
        """Muestra mensaje de error"""
        # Crear ventana de error simple
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
