"""
Servicio de streaming de video/audio
"""
import threading
import time
import queue
import json
import base64
from typing import Callable, Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageTk
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None
    Image = None
    ImageTk = None

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    mss = None
    MSS_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False


@dataclass
class VideoFrame:
    """Frame de video"""
    data: bytes
    timestamp: float
    width: int
    height: int
    frame_num: int = 0


@dataclass
class AudioFrame:
    """Frame de audio"""
    data: bytes
    timestamp: float
    sample_rate: int = 16000
    channels: int = 1
    samples: int = 0


@dataclass
class ScreenShareConfig:
    """Configuración de screen share"""
    source_type: str = "screen"  # "screen", "window", "application"
    source_id: str = ""
    display_id: int = 0
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    quality: int = 80
    bitrate: int = 2500000


class VideoStreamService:
    """Servicio de streaming de video"""
    
    def __init__(self, network_service, fps: int = 15, quality: int = 70):
        self.network = network_service
        self.fps = fps
        self.quality = quality
        self.streaming = False
        self.capture = None
        self.broadcasting = False
        self.watching: Dict[str, Any] = {}
        self.frame_queue = queue.Queue(maxsize=30)
        self.callbacks: Dict[str, list] = {
            'frame': [],
            'error': [],
            'stopped': []
        }
        
        self.network.register_callback('message', self._handle_message)
    
    def start_camera(self, camera_index: int = 0) -> bool:
        """Inicia la cámara"""
        if not CV2_AVAILABLE:
            print("OpenCV not available")
            return False
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
    """Servicio de streaming de audio"""
    
    def __init__(self, network_service):
        self.network = network_service
        self.streaming = False
        self.broadcasting = False
        self.listening = False
        self.sample_rate = 16000
        self.channels = 1
        self.callbacks: Dict[str, list] = {}
        
        self.audio_queue: Dict[str, queue.Queue] = {}
        
        self.network.register_callback('message', self._handle_message)
    
    def start_stream(self, channel_id: str, user_id: str) -> bool:
        """Inicia streaming de audio"""
        self.streaming = True
        self.channel_id = channel_id
        self.user_id = user_id
        return True
    
    def stop_stream(self):
        """Detiene streaming de audio"""
        self.streaming = False
        self.broadcasting = False
        self.listening = False
    
    def start_broadcasting(self, channel_id: str, user_id: str):
        """Inicia transmisión de audio del micrófono"""
        self.broadcasting = True
        self.channel_id = channel_id
        self.user_id = user_id
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
    
    def stop_broadcasting(self):
        """Detiene transmisión de audio"""
        self.broadcasting = False
    
    def start_listening(self, user_id: str, channel_id: str):
        """Inicia escucha de audio de un usuario"""
        self.audio_queue[user_id] = queue.Queue(maxsize=30)
        self.listening = True
    
    def stop_listening(self, user_id: str):
        """Detiene escucha de audio"""
        if user_id in self.audio_queue:
            del self.audio_queue[user_id]
    
    def get_audio(self, user_id: str) -> Optional[AudioFrame]:
        """Obtiene el próximo frame de audio"""
        if user_id not in self.audio_queue:
            return None
        try:
            return self.audio_queue[user_id].get(timeout=1.0)
        except queue.Empty:
            return None
    
    def _broadcast_loop(self):
        """Loop de transmisión de audio"""
        while self.broadcasting:
            try:
                time.sleep(0.02)
            except Exception as e:
                print(f"Error in audio broadcast: {e}")
                break
        self.broadcasting = False
    
    def send_audio_frame(self, audio_data: bytes, timestamp: float):
        """Envía un frame de audio"""
        message = {
            'type': 'audio_frame',
            'data': {
                'audio_data': base64.b64encode(audio_data).decode(),
                'timestamp': timestamp,
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'channel_id': self.channel_id,
                'sender_id': self.user_id
            }
        }
        self.network.broadcast(message, exclude=[self.user_id])
    
    def _handle_message(self, data: Dict[str, Any]):
        """Maneja mensajes de audio"""
        message = data.get('message')
        if not message:
            return
        
        msg_type = message.data.get('type', '')
        
        if msg_type == 'audio_frame':
            audio_data = message.data
            user_id = message.sender_id
            
            if user_id in self.audio_queue:
                try:
                    audio_bytes = base64.b64decode(audio_data['audio_data'])
                    audio_frame = AudioFrame(
                        data=audio_bytes,
                        timestamp=audio_data['timestamp'],
                        sample_rate=audio_data.get('sample_rate', 16000),
                        channels=audio_data.get('channels', 1),
                        samples=len(audio_bytes)
                    )
                    self.audio_queue[user_id].put(audio_frame, block=False)
                except queue.Full:
                    pass
                except Exception as e:
                    print(f"Error processing audio frame: {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)


class ScreenShareService:
    """Servicio de screen share"""
    
    def __init__(self, network_service):
        self.network = network_service
        self.sharing = False
        self.watching: Dict[str, Any] = {}
        self.screenshots = mss.mss() if MSS_AVAILABLE else None
        self.callbacks: Dict[str, list] = {}
        
        self.config = ScreenShareConfig()
        
        self.network.register_callback('message', self._handle_message)
    
    def get_displays(self) -> List[Dict[str, Any]]:
        """Obtiene lista de monitores/displays"""
        if not MSS_AVAILABLE or not self.screenshots:
            return [{'id': 0, 'name': 'Display 1', 'width': 1920, 'height': 1080}]
        
        displays = []
        for i, monitor in enumerate(self.screenshots.monitors):
            if i == 0:
                continue
            displays.append({
                'id': i,
                'name': f"Display {i}",
                'width': monitor['width'],
                'height': monitor['height'],
                'x': monitor['x'],
                'y': monitor['y']
            })
        return displays
    
    def get_windows(self) -> List[Dict[str, Any]]:
        """Obtiene lista de ventanas disponibles"""
        return []
    
    def get_applications(self) -> List[Dict[str, Any]]:
        """Obtiene lista de aplicaciones disponibles"""
        return []
    
    def start_sharing(self, channel_id: str, user_id: str, config: ScreenShareConfig = None) -> bool:
        """Inicia screen share"""
        if not MSS_AVAILABLE:
            print("mss library not available")
            return False
        
        if config:
            self.config = config
        
        self.sharing = True
        self.channel_id = channel_id
        self.user_id = user_id
        
        threading.Thread(target=self._capture_loop, daemon=True).start()
        return True
    
    def stop_sharing(self):
        """Detiene screen share"""
        self.sharing = False
    
    def start_watching(self, user_id: str, channel_id: str):
        """Inicia visualización de screen share"""
        self.watching[user_id] = {
            'channel_id': channel_id,
            'frames': queue.Queue(maxsize=30)
        }
    
    def stop_watching(self, user_id: str):
        """Detiene visualización"""
        if user_id in self.watching:
            del self.watching[user_id]
    
    def get_frame(self, user_id: str) -> Optional[VideoFrame]:
        """Obtiene el próximo frame"""
        if user_id not in self.watching:
            return None
        try:
            return self.watching[user_id]['frames'].get(timeout=1.0)
        except queue.Empty:
            return None
    
    def update_config(self, resolution: Tuple[int, int] = None, fps: int = None, quality: int = None):
        """Actualiza configuración de screen share"""
        if resolution:
            self.config.resolution = resolution
        if fps:
            self.config.fps = fps
        if quality:
            self.config.quality = quality
    
    def _capture_loop(self):
        """Loop de captura de pantalla"""
        if not MSS_AVAILABLE or not self.screenshots or not CV2_AVAILABLE:
            self.sharing = False
            return
        
        frame_num = 0
        frame_interval = 1.0 / self.config.fps
        
        try:
            monitor = self.screenshots.monitors[self.config.display_id]
        except (IndexError, KeyError):
            monitor = self.screenshots.monitors[1]
        
        while self.sharing:
            start_time = time.time()
            
            try:
                sct_img = self.screenshots.grab(monitor)
                
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img = img.convert("RGB")
                
                width, height = img.size
                if self.config.resolution != (width, height):
                    img = img.resize(self.config.resolution)
                
                img_np = np.array(img)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.config.quality]
                _, buffer = cv2.imencode('.jpg', img_np, encode_param)
                
                video_frame = VideoFrame(
                    data=buffer.tobytes(),
                    timestamp=time.time(),
                    width=img.width,
                    height=img.height,
                    frame_num=frame_num
                )
                
                message = {
                    'type': 'screen_frame',
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
                
                self.network.broadcast(message, exclude=[self.user_id])
                
                frame_num += 1
                
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Error in screen capture: {e}")
                break
        
        self.sharing = False
    
    def _handle_message(self, data: Dict[str, Any]):
        """Maneja mensajes de screen share"""
        message = data.get('message')
        if not message:
            return
        
        msg_type = message.data.get('type', '')
        
        if msg_type == 'screen_frame':
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
                    pass
                except Exception as e:
                    print(f"Error processing screen frame: {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
