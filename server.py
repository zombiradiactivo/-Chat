#!/usr/bin/env python3
"""
Servidor standalone de Chat App
Ejecuta solo el servidor sin interfaz gráfica
"""
import sys
import signal
import argparse
from pathlib import Path

# Asegurar que el directorio src esté en el path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.network.service import TCPServer
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatServer:
    """Servidor de chat independiente"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.server = TCPServer(host, port)
        self.running = False
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación"""
        logger.info("Recibida señal de terminación, deteniendo servidor...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Inicia el servidor"""
        logger.info(f"Iniciando servidor en {self.host}:{self.port}")
        self.running = True
        
        try:
            self.server.start(self.host, self.port)
            logger.info(f"Servidor escuchando en {self.host}:{self.port}")
            
            # Mantener el servidor corriendo
            while self.running:
                # Aquí se podrían manejar comandos de la consola
                # Por ahora solo esperamos
                import time
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupción de teclado recibida")
        except Exception as e:
            logger.error(f"Error en el servidor: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el servidor"""
        self.running = False
        self.server.stop()
        logger.info("Servidor detenido")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Servidor de Chat App')
    parser.add_argument('--host', default='0.0.0.0', help='Host para escuchar (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5555, help='Puerto para escuchar (default: 5555)')
    
    args = parser.parse_args()
    
    server = ChatServer(args.host, args.port)
    server.start()


if __name__ == "__main__":
    main()
