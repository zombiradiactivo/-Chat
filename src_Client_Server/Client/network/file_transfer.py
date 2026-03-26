"""
Servicio de transferencia de archivos
"""
import os
import hashlib
import time
from typing import Callable, Optional, Dict, Any
from pathlib import Path
from threading import Thread, Lock
from queue import Queue
from .service import NetworkService, NetworkMessage
from utils.encryption import AESEncryption


class FileTransferService:
    """Servicio para transferencia de archivos"""
    
    def __init__(self, network_service: NetworkService, encryption_service=None):
        self.network = network_service
        self.encryption = encryption_service
        self.transfers: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.callbacks: Dict[str, list] = {
            'progress': [],
            'completed': [],
            'error': []
        }
        self.chunk_size = 8192
        
        # Registrar callback para mensajes de red
        self.network.register_callback('message', self._handle_network_message)
    
    def upload_file(self, filepath: str, channel_id: str, user_id: str, 
                   encrypted: bool = False, callback: Optional[Callable] = None) -> str:
        """Inicia la subida de un archivo"""
        transfer_id = self._generate_transfer_id()
        
        file_size = os.path.getsize(filepath)
        file_hash = self._compute_file_hash(filepath)
        filename = os.path.basename(filepath)
        file_type = self._get_mime_type(filename)
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        transfer_info = {
            'transfer_id': transfer_id,
            'filepath': filepath,
            'filename': filename,
            'file_size': file_size,
            'file_hash': file_hash,
            'file_type': file_type,
            'channel_id': channel_id,
            'sender_id': user_id,
            'encrypted': encrypted,
            'total_chunks': total_chunks,
            'uploaded_chunks': 0,
            'status': 'uploading',
            'callback': callback
        }
        
        with self.lock:
            self.transfers[transfer_id] = transfer_info
        
        # Iniciar subida en hilo separado
        Thread(target=self._upload_worker, args=(transfer_id,), daemon=True).start()
        
        return transfer_id
    
    def download_file(self, transfer_info: Dict[str, Any], save_path: str,
                     callback: Optional[Callable] = None) -> str:
        """Inicia la descarga de un archivo"""
        transfer_id = transfer_info['id']
        
        download_info = {
            'transfer_id': transfer_id,
            'save_path': save_path,
            'filename': transfer_info['filename'],
            'file_size': transfer_info['file_size'],
            'file_hash': transfer_info['file_hash'],
            'encrypted': transfer_info.get('encrypted', False),
            'total_chunks': transfer_info['total_chunks'],
            'downloaded_chunks': 0,
            'status': 'downloading',
            'callback': callback,
            'download_url': transfer_info.get('download_url')
        }
        
        with self.lock:
            self.transfers[transfer_id] = download_info
        
        # Iniciar descarga en hilo separado
        Thread(target=self._download_worker, args=(transfer_id,), daemon=True).start()
        
        return transfer_id
    
    def _upload_worker(self, transfer_id: str):
        """Worker para subir archivos en chunks"""
        transfer = None
        try:
            with self.lock:
                transfer = self.transfers.get(transfer_id)
                if not transfer:
                    return
            
            filepath = transfer['filepath']
            total_chunks = transfer['total_chunks']
            
            with open(filepath, 'rb') as f:
                for chunk_num in range(total_chunks):
                    chunk = f.read(self.chunk_size)
                    
                    # Encriptar si es necesario
                    if transfer['encrypted'] and self.encryption:
                        chunk = self.encryption.encrypt(chunk)
                    
                    # Enviar chunk
                    message = NetworkMessage(
                        type='file_chunk',
                        data={
                            'transfer_id': transfer_id,
                            'chunk_num': chunk_num,
                            'chunk_data': chunk.hex(),
                            'total_chunks': total_chunks
                        },
                        sender_id=transfer['sender_id']
                    )
                    
                    success = self.network.send(transfer['channel_id'], message)
                    if not success:
                        raise Exception(f"Failed to send chunk {chunk_num}")
                    
                    # Actualizar progreso
                    with self.lock:
                        if transfer_id in self.transfers:
                            self.transfers[transfer_id]['uploaded_chunks'] = chunk_num + 1
                            progress = (chunk_num + 1) / total_chunks * 100
                            self._notify_callbacks('progress', {
                                'transfer_id': transfer_id,
                                'progress': progress,
                                'filename': transfer['filename']
                            })
                    
                    time.sleep(0.01)  # Pequeña pausa para no saturar
            
            # Subida completada
            with self.lock:
                if transfer_id in self.transfers:
                    self.transfers[transfer_id]['status'] = 'completed'
                    self._notify_callbacks('completed', {
                        'transfer_id': transfer_id,
                        'filename': transfer['filename']
                    })
                    
                    if transfer['callback']:
                        transfer['callback'](transfer_id, 'completed', None)
        
        except Exception as e:
            with self.lock:
                if transfer_id in self.transfers:
                    self.transfers[transfer_id]['status'] = 'error'
                    self.transfers[transfer_id]['error'] = str(e)
                    self._notify_callbacks('error', {
                        'transfer_id': transfer_id,
                        'error': str(e),
                        'filename': transfer['filename'] if transfer else 'unknown'
                    })
                    
                    if transfer and transfer.get('callback'):
                        transfer['callback'](transfer_id, 'error', str(e))
    
    def _download_worker(self, transfer_id: str):
        """Worker para descargar archivos en chunks"""
        transfer = None
        try:
            with self.lock:
                transfer = self.transfers.get(transfer_id)
                if not transfer:
                    return
            
            save_path = transfer['save_path']
            total_chunks = transfer['total_chunks']
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk_num in range(total_chunks):
                    # Solicitar chunk (en una implementación real, se manejaría mejor)
                    # Por ahora asumimos que el servidor envía los chunks automáticamente
                    # y se almacenan en un buffer
                    
                    # Simular progreso
                    with self.lock:
                        if transfer_id in self.transfers:
                            self.transfers[transfer_id]['downloaded_chunks'] = chunk_num + 1
                            progress = (chunk_num + 1) / total_chunks * 100
                            self._notify_callbacks('progress', {
                                'transfer_id': transfer_id,
                                'progress': progress,
                                'filename': transfer['filename']
                            })
                    
                    time.sleep(0.01)
            
            # Verificar hash
            file_hash = self._compute_file_hash(save_path)
            if file_hash != transfer['file_hash']:
                raise Exception("Hash mismatch - file corrupted")
            
            # Descarga completada
            with self.lock:
                if transfer_id in self.transfers:
                    self.transfers[transfer_id]['status'] = 'completed'
                    self._notify_callbacks('completed', {
                        'transfer_id': transfer_id,
                        'filename': transfer['filename']
                    })
                    
                    if transfer['callback']:
                        transfer['callback'](transfer_id, 'completed', None)
        
        except Exception as e:
            with self.lock:
                if transfer_id in self.transfers:
                    self.transfers[transfer_id]['status'] = 'error'
                    self.transfers[transfer_id]['error'] = str(e)
                    self._notify_callbacks('error', {
                        'transfer_id': transfer_id,
                        'error': str(e),
                        'filename': transfer['filename'] if transfer else 'unknown'
                    })
                    
                    if transfer and transfer.get('callback'):
                        transfer['callback'](transfer_id, 'error', str(e))
    
    def _handle_network_message(self, data: Dict[str, Any]):
        """Maneja mensajes de red relacionados con archivos"""
        message = data.get('message')
        if not message:
            return
        
        msg_data = message.data
        
        if message.type == 'file_chunk':
            transfer_id = msg_data.get('transfer_id')
            chunk_data = bytes.fromhex(msg_data['chunk_data'])
            
            # Guardar chunk en buffer temporal
            # En una implementación real, se manejaría un buffer por transferencia
            pass
        
        elif message.type == 'file_complete':
            transfer_id = msg_data.get('transfer_id')
            with self.lock:
                if transfer_id in self.transfers:
                    self.transfers[transfer_id]['status'] = 'completed'
    
    def _generate_transfer_id(self) -> str:
        """Genera un ID de transferencia único"""
        import uuid
        return str(uuid.uuid4())
    
    def _compute_file_hash(self, filepath: str) -> str:
        """Calcula el hash SHA-256 de un archivo"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _get_mime_type(self, filename: str) -> str:
        """Obtiene el MIME type de un archivo"""
        import mimetypes
        mime, _ = mimetypes.guess_type(filename)
        return mime or 'application/octet-stream'
    
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
                    print(f"Error in file transfer callback: {e}")
    
    def get_transfer_info(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una transferencia"""
        with self.lock:
            return self.transfers.get(transfer_id)
    
    def cancel_transfer(self, transfer_id: str):
        """Cancela una transferencia"""
        with self.lock:
            if transfer_id in self.transfers:
                self.transfers[transfer_id]['status'] = 'cancelled'
                # En una implementación real, se notificaría al otro lado
