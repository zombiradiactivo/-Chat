"""
Servicio de encriptación para mensajes y archivos
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
from typing import Tuple, Optional


class EncryptionService:
    """Servicio de encriptación para la aplicación"""
    
    def __init__(self, key: Optional[bytes] = None):
        """Inicializa el servicio de encriptación"""
        if key:
            self.key = key
        else:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> 'EncryptionService':
        """Crea un servicio de encriptación desde una contraseña"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return cls(key)
    
    def encrypt(self, data: bytes) -> bytes:
        """Encripta datos"""
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Desencripta datos"""
        return self.cipher.decrypt(encrypted_data)
    
    def encrypt_string(self, text: str) -> str:
        """Encripta un string y devuelve base64"""
        encrypted = self.encrypt(text.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Desencripta un string desde base64"""
        encrypted = base64.b64decode(encrypted_text.encode())
        decrypted = self.decrypt(encrypted)
        return decrypted.decode()
    
    def generate_file_key(self) -> Tuple[bytes, bytes]:
        """Genera una clave para archivos"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
        return key, salt
    
    def get_key(self) -> bytes:
        """Obtiene la clave actual"""
        return self.key
    
    def get_salt(self) -> bytes:
        """Obtiene el salt (para derivación de clave)"""
        # Extraer salt del key si es Fernet
        # Fernet keys son base64-encoded 32 bytes
        return b'fixed_salt_for_demo'  # En producción usar PBKDF2 con salt real


class AESEncryption:
    """Encriptación AES para archivos grandes"""
    
    def __init__(self, key: Optional[bytes] = None):
        if key:
            self.key = key[:32]  # Asegurar 32 bytes para AES-256
        else:
            self.key = os.urandom(32)
    
    def encrypt_file(self, input_path: str, output_path: str, chunk_size: int = 8192):
        """Encripta un archivo en chunks"""
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CFB8(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            outfile.write(iv)
            while True:
                chunk = infile.read(chunk_size)
                if not chunk:
                    break
                encrypted = encryptor.update(chunk)
                outfile.write(encrypted)
            outfile.write(encryptor.finalize())
    
    def decrypt_file(self, input_path: str, output_path: str, chunk_size: int = 8192):
        """Desencripta un archivo en chunks"""
        with open(input_path, 'rb') as infile:
            iv = infile.read(16)
            cipher = Cipher(algorithms.AES(self.key), modes.CFB8(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            with open(output_path, 'wb') as outfile:
                while True:
                    chunk = infile.read(chunk_size)
                    if not chunk:
                        break
                    decrypted = decryptor.update(chunk)
                    outfile.write(decrypted)
                outfile.write(decryptor.finalize())
    
    def compute_hash(self, filepath: str, chunk_size: int = 8192) -> str:
        """Calcula el hash SHA-256 de un archivo"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
