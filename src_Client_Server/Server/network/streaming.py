"""
Servicio de streaming de video/audio
"""
import threading
import time
import queue
from typing import Callable, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import cv2
import numpy as np
from PIL import Image, ImageTk


@dataclass
class VideoFrame:
    """Frame de video"""
    data: bytes  # Datos JPEG comprimidos
    timestamp: float
    width: int
    height: int
    frame_num: int = 0


class VideoStreamService:
    """Servicio de streaming de video"""
    
    def __init__(self, network_service, fps: int = 15, quality: int = 70):
        self.network = network_service
        self.fps = fps
        self.quality = quality  # Calidad JPEG 0-100
        self.streaming = False
        self.capture: Optional[cv2.VideoCapture] = None
        self.broadcasting = False
        self.watching: Dict[str, Any] = {}
        self.frame_queue = queue.Queue(maxsize=30)
        self.callbacks: Dict[str, list] = {
            'frame': [],
            'error': [],
            'stopped': []
        }
        
        # Registrar callback para mensajes de video
        self.network.register_callback('message', self._handle_message)
    
    def start_camera(self, camera_index: int = 0) -> bool:
        """Inicia la cámara"""
        try:
            self.capture = cv2.VideoCapture(camera_index)
            if not self.capture.isOpened():
                return False
            return True
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Detiene la cámara"""
        if self.capture:
            self.capture.release()
            self.capture = None
    
    def start_broadcast(self, channel_id: str, user_id: str) -> bool:
        """Inicia la transmisión de video"""
        if not self.capture or not self.capture.isOpened():
            if not self.start_camera():
                return False
        
        self.streaming = True
        self.broadcasting = True
        self.channel_id = channel_id
        self.user_id = user_id
        
        # Hilo para capturar frames
        threading.Thread(target=self._capture_loop, daemon=True).start()
        
        return True
    
    def stop_broadcast(self):
        """Detiene la transmisión"""
        self.streaming = False
        self.broadcasting = False
        time.sleep(0.1)
    
    def start_watching(self, user_id: str, channel_id: str):
        """Inicia la visualización de un stream"""
        self.watching[user_id] = {
            'channel_id': channel_id,
            'frames': queue.Queue(maxsize=30)
        }
    
    def stop_watching(self, user_id: str):
        """Detiene la visualización de un stream"""
        if user_id in self.watching:
            del self.watching[user_id]
    
    def get_frame(self, user_id: str) -> Optional[VideoFrame]:
        """Obtiene el próximo frame para un usuario"""
        if user_id not in self.watching:
            return None
        try:
            return self.watching[user_id]['frames'].get(timeout=1.0)
        except queue.Empty:
            return None
    
    def _capture_loop(self):
        """Loop principal de captura"""
        frame_num = 0
        frame_interval = 1.0 / self.fps
        
        while self.streaming and self.broadcasting:
            start_time = time.time()
            
            try:
                ret, frame = self.capture.read()
                if not ret:
                    break
                
                # Redimensionar si es necesario (optimización)
                height, width = frame.shape[:2]
                if width > 1280:
                    scale = 1280 / width
                    new_width = 1280
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # Comprimir a JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                video_frame = VideoFrame(
                    data=buffer.tobytes(),
                    timestamp=time.time(),
                    width=frame.shape[1],
                    height=frame.shape[0],
                    frame_num=frame_num
                )
                
                # Enviar frame
                message = {
                    'type': 'video_frame',
                    'data': {
                        'frame_data': video_frame.data.hex(),
                        'timestamp': video_frame.timestamp,
                        'width': video_frame.width,
                        'height': video_frame.height,
                        'frame_num': video_frame.frame_num,
                        'channel_id': self.channel_id,
                        'sender_id': self.user_id
                    }
                }
                
                # Enviar a todos en el canal (excepto a uno mismo)
                self.network.broadcast(message, exclude=[self.user_id])
                
                frame_num += 1
                
                # Controlar FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Error in capture loop: {e}")
                break
        
        self.streaming = False
    
    def _handle_message(self, data: Dict[str, Any]):
        """Maneja mensajes de red"""
        message = data.get('message')
        if not message:
            return
        
        msg_type = message.data.get('type', '')
        
        if msg_type == 'video_frame':
            frame_data = message.data
            user_id = message.sender_id
            
            if user_id in self.watching:
                try:
                    frame_bytes = bytes.fromhex(frame_data['frame_data'])
                    video_frame = VideoFrame(
                        data=frame_bytes,
                        timestamp=frame_data['timestamp'],
                        width=frame_data['width'],
                        height=frame_data['height'],
                        frame_num=frame_data['frame_num']
                    )
                    self.watching[user_id]['frames'].put(video_frame, block=False)
                except queue.Full:
                    pass  # Descartar frame si el buffer está lleno
                except Exception as e:
                    print(f"Error processing video frame: {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notifica a los callbacks"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in video callback: {e}")


class AudioStreamService:
    """Servicio de streaming de audio (simplificado)"""
    
    def __init__(self, network_service):
        self.network = network_service
        self.streaming = False
        self.callbacks: Dict[str, list] = {}
        
        self.network.register_callback('message', self._handle_message)
    
    def start_stream(self, channel_id: str, user_id: str) -> bool:
        """Inicia streaming de audio (placeholder)"""
        self.streaming = True
        self.channel_id = channel_id
        self.user_id = user_id
        # En una implementación real, se usaría PyAudio o similar
        return True
    
    def stop_stream(self):
        """Detiene streaming de audio"""
        self.streaming = False
    
    def _handle_message(self, data: Dict[str, Any]):
        """Maneja mensajes de audio"""
        pass
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
