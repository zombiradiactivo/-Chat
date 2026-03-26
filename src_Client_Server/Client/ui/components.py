"""
Componentes personalizados de UI
"""
import customtkinter as ctk
from typing import Callable, Optional, Any
from PIL import Image, ImageTk
import io
import base64


class AvatarLabel(ctk.CTkLabel):
    """Label con avatar de usuario"""
    
    def __init__(self, master, image_data: Optional[str] = None, size: int = 40, **kwargs):
        self.size = size
        self.image_data = image_data
        
        # Crear imagen por defecto
        default_image = self._create_default_avatar()
        
        super().__init__(
            master,
            image=default_image,
            text="",
            width=size,
            height=size,
            **kwargs
        )
        
        if image_data:
            self.set_image(image_data)
    
    def _create_default_avatar(self) -> ctk.CTkImage:
        """Crea un avatar por defecto"""
        # Crear imagen simple con iniciales
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (self.size, self.size), color='#7289DA')
        draw = ImageDraw.Draw(img)
        
        # Dibujar círculo
        draw.ellipse([2, 2, self.size-2, self.size-2], fill='#7289DA')
        
        return ctk.CTkImage(img, size=(self.size, self.size))
    
    def set_image(self, image_data: str):
        """Establece la imagen desde base64"""
        try:
            if image_data.startswith('http'):
                # URL - se manejaría con requests
                pass
            else:
                # Base64
                image_bytes = base64.b64decode(image_data)
                pil_image = Image.open(io.BytesIO(image_bytes))
                pil_image = pil_image.resize((self.size, self.size), Image.Resampling.LANCZOS)
                ctk_image = ctk.CTkImage(pil_image, size=(self.size, self.size))
                self.configure(image=ctk_image)
        except Exception as e:
            print(f"Error cargando avatar: {e}")


class ScrollableFrame(ctk.CTkScrollableFrame):
    """Frame con scroll"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)


class ChannelButton(ctk.CTkButton):
    """Botón para canal en la sidebar"""
    
    def __init__(self, master, channel_name: str, channel_id: str, 
                 channel_type: str, command: Callable, **kwargs):
        self.channel_id = channel_id
        self.channel_type = channel_type
        
        # Icono según tipo
        icon = "#" if channel_type == "text" else "🔊" if channel_type == "voice" else "📹"
        text = f"{icon} {channel_name}"
        
        super().__init__(
            master,
            text=text,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            command=command,
            **kwargs
        )


class ServerButton(ctk.CTkButton):
    """Botón para servidor en la sidebar"""
    
    def __init__(self, master, server_name: str, server_id: str, 
                 command: Optional[Callable] = None, **kwargs):
        self.server_id = server_id
        
        super().__init__(
            master,
            text=server_name[:10],
            width=40,
            height=40,
            corner_radius=8,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            command=command,
            **kwargs
        )


class MessageBubble(ctk.CTkFrame):
    """Burbuja de mensaje"""
    
    def __init__(self, master, author: str, content: str, timestamp: str,
                 avatar_color: str = "#7289DA", is_own: bool = False, **kwargs):
        super().__init__(master, **kwargs)
        
        self.is_own = is_own
        
        # Configurar color de fondo según si es propio
        if is_own:
            self.configure(fg_color=("#DCF8C6", "#2B7D31"))
        else:
            self.configure(fg_color=("gray90", "gray15"))
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        
        # Avatar
        self.avatar = ctk.CTkLabel(
            self,
            text=author[:2].upper(),
            width=32,
            height=32,
            corner_radius=16,
            fg_color=avatar_color,
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.avatar.grid(row=0, column=0, padx=8, pady=8, sticky="nw")
        
        # Contenedor de texto
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        
        # Autor y timestamp
        header_frame = ctk.CTkFrame(text_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="w")
        
        self.author_label = ctk.CTkLabel(
            header_frame,
            text=author,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.author_label.pack(side="left", padx=(0, 8))
        
        self.time_label = ctk.CTkLabel(
            header_frame,
            text=timestamp,
            font=ctk.CTkFont(size=10),
            text_color="gray60",
            anchor="w"
        )
        self.time_label.pack(side="left")
        
        # Contenido
        self.content_label = ctk.CTkLabel(
            text_frame,
            text=content,
            wraplength=400,
            justify="left",
            anchor="w"
        )
        self.content_label.grid(row=1, column=0, sticky="w", pady=(4, 0))


class UserListItem(ctk.CTkFrame):
    """Item de usuario en la lista de miembros"""
    
    def __init__(self, master, username: str, status: str = "online", 
                 roles: list = None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.configure(fg_color="transparent", height=32)
        
        # Avatar pequeño
        avatar = ctk.CTkLabel(
            self,
            text=username[:2].upper(),
            width=24,
            height=24,
            corner_radius=12,
            fg_color="#7289DA",
            text_color="white",
            font=ctk.CTkFont(size=10)
        )
        avatar.pack(side="left", padx=(0, 8))
        
        # Nombre
        name_label = ctk.CTkLabel(
            self,
            text=username,
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)
        
        # Indicador de estado
        status_colors = {
            "online": "#43B581",
            "offline": "#747F8D",
            "idle": "#FAA61A",
            "dnd": "#F04747",
            "invisible": "#2C2F33"
        }
        status_color = status_colors.get(status, "#747F8D")
        
        status_dot = ctk.CTkLabel(
            self,
            text="",
            width=8,
            height=8,
            corner_radius=4,
            fg_color=status_color
        )
        status_dot.pack(side="right", padx=8)
