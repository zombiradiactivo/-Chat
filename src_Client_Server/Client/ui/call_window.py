"""
Ventana de llamada estilo Discord
"""
import customtkinter as ctk
from typing import Dict, Any, Optional
import threading
import time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CallWindow(ctk.CTkToplevel):
    """Ventana de llamada en ventana separada"""
    
    def __init__(self, parent, channel_name: str, call_type: str = "voice", on_end_call=None):
        super().__init__(parent)
        
        self.channel_name = channel_name
        self.call_type = call_type
        self.on_end_call = on_end_call
        self.participants: Dict[str, Dict] = {}
        
        self.title(f"Llamada - {channel_name}")
        self.geometry("900x600")
        self.minsize(600, 400)
        
        self.configure(fg_color="#202225")
        
        self._build_ui()
        self._setup_closeProtocol()
        
        self.lift()
        self.focus()
    
    def _build_ui(self):
        """Construye la interfaz"""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="#202225", height=50)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header,
            text=f"📞 {self.channel_name}",
            text_color="#dcddde",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=12)
        
        ctk.CTkLabel(
            header,
            text="Conectado",
            text_color="#3ba55c",
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=1, sticky="e", padx=16)
        
        main = ctk.CTkFrame(self, fg_color="#2f3136")
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        
        self.video_grid = ctk.CTkFrame(main, fg_color="transparent")
        self.video_grid.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        sidebar = ctk.CTkFrame(main, width=220, fg_color="#202225")
        sidebar.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 8))
        
        ctk.CTkLabel(
            sidebar,
            text="Participantes",
            text_color="#96989d",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(12, 8), padx=12, anchor="w")
        
        self.participants_list = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.participants_list.pack(fill="both", expand=True, padx=8, pady=4)
        
        controls = ctk.CTkFrame(self, fg_color="#202225", height=70)
        controls.grid(row=2, column=0, sticky="ew")
        
        self.mute_btn = ctk.CTkButton(
            controls,
            text="🔊",
            width=44,
            height=44,
            fg_color="#4f545c",
            hover_color="#5d646d",
            command=self._on_toggle_mute
        )
        self.mute_btn.pack(side="left", padx=8, pady=12)
        
        if self.call_type == "video":
            self.video_btn = ctk.CTkButton(
                controls,
                text="📹",
                width=44,
                height=44,
                fg_color="#4f545c",
                hover_color="#5d646d",
                command=self._on_toggle_video
            )
            self.video_btn.pack(side="left", padx=4)
        
        self.screen_btn = ctk.CTkButton(
            controls,
            text="🖥️",
            width=44,
            height=44,
            fg_color="#4f545c",
            hover_color="#5d646d",
            command=self._on_screen_share
        )
        self.screen_btn.pack(side="left", padx=4)
        
        self.end_btn = ctk.CTkButton(
            controls,
            text="📴",
            width=80,
            height=44,
            fg_color="#ed4245",
            hover_color="#c93a3c",
            text_color="white",
            command=self._on_end_call_window
        )
        self.end_btn.pack(side="right", padx=8, pady=12)
    
    def _on_toggle_mute(self):
        """Alternar silencio"""
        if hasattr(self, 'muted') and self.muted:
            self.muted = False
            self.mute_btn.configure(text="🔊", fg_color="#4f545c")
        else:
            self.muted = True
            self.mute_btn.configure(text="🔇", fg_color="#ed4245")
    
    def _on_toggle_video(self):
        """Alternar video"""
        if hasattr(self, 'video_on') and self.video_on:
            self.video_on = False
            self.video_btn.configure(fg_color="#4f545c")
        else:
            self.video_on = True
            self.video_btn.configure(fg_color="#3ba55c")
    
    def _on_screen_share(self):
        """Compartir pantalla"""
        pass
    
    def _on_end_call_window(self):
        """Finalizar llamada"""
        if self.on_end_call:
            self.on_end_call()
        self.destroy()
    
    def add_participant(self, user_id: str, username: str, has_video: bool = False):
        """Añade un participante a la lista"""
        if user_id in self.participants:
            return
        
        self.participants[user_id] = {
            'id': user_id,
            'name': username,
            'has_video': has_video,
            'muted': False
        }
        self._update_participants_list()
    
    def remove_participant(self, user_id: str):
        """Elimina un participante"""
        if user_id in self.participants:
            del self.participants[user_id]
            self._update_participants_list()
    
    def _update_participants_list(self):
        """Actualiza la lista de participantes"""
        for widget in self.participants_list.winfo_children():
            widget.destroy()
        
        colors = ['#5865f2', '#57f287', '#fee75c', '#ed4245', '#faa61a']
        
        for i, participant in enumerate(self.participants.values()):
            item = ctk.CTkFrame(self.participants_list, fg_color="transparent")
            item.pack(fill="x", pady=2)
            
            color = participant.get('color', colors[i % len(colors)])
            
            initial = participant['name'][0].upper()
            
            ctk.CTkLabel(
                item,
                text=initial,
                width=32,
                height=32,
                fg_color=color,
                text_color="white",
                font=ctk.CTkFont(size=14, weight="bold"),
                corner_radius=16
            ).pack(side="left", padx=(0, 8))
            
            name_label = ctk.CTkLabel(
                item,
                text=participant['name'],
                text_color="#dcddde",
                font=ctk.CTkFont(size=13)
            )
            name_label.pack(side="left")
            
            if participant.get('muted'):
                ctk.CTkLabel(
                    item,
                    text="🔇",
                    text_color="#ed4245"
                ).pack(side="right", padx=4)
    
    def set_screen_sharing(self, user_id: str, sharing: bool):
        """Configura estado de compartir pantalla"""
        if sharing:
            self.screen_btn.configure(fg_color="#3ba55c")
        else:
            self.screen_btn.configure(fg_color="#4f545c")
    
    def add_video_tile(self, user_id: str, username: str):
        """Añade un tile de video"""
        colors = ['#5865f2', '#57f287', '#fee75c', '#ed4245', '#faa61a']
        
        frame = ctk.CTkFrame(
            self.video_grid,
            fg_color="#1e1f22",
            corner_radius=8
        )
        
        initial = username[0].upper()
        color = colors[hash(username) % len(colors)]
        
        avatar = ctk.CTkLabel(
            frame,
            text=initial,
            width=120,
            height=80,
            fg_color=color,
            text_color="white",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        avatar.pack(pady=20)
        
        name_label = ctk.CTkLabel(
            frame,
            text=username,
            text_color="white",
            font=ctk.CTkFont(size=12)
        )
        name_label.pack(pady=(0, 8))
        
        frame.pack(side="left", padx=4, pady=4, fill="both", expand=True)
        return frame