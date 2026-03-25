#!/usr/bin/env python3
"""
Cliente standalone de Chat App
Ejecuta solo la interfaz gráfica y se conecta a un servidor externo
"""
import sys
import signal
from pathlib import Path

# Asegurar que el directorio src esté en el path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.app import ChatApp
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatClient:
    """Cliente de chat independiente"""
    
    def __init__(self):
        self.app = None
        self.running = False
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación"""
        logger.info("Recibida señal de terminación, cerrando cliente...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Inicia el cliente"""
        logger.info("Iniciando cliente de chat...")
        self.running = True
        
        try:
            # Crear y ejecutar la aplicación
            self.app = ChatApp()
            exit_code = self.app.run()
            return exit_code
        except KeyboardInterrupt:
            logger.info("Interrupción de teclado recibida")
        except Exception as e:
            logger.error(f"Error en el cliente: {e}")
        finally:
            self.stop()
        
        return 1
    
    def stop(self):
        """Detiene el cliente"""
        self.running = False
        if self.app:
            self.app.cleanup()
        logger.info("Cliente detenido")


def main():
    """Función principal"""
    client = ChatClient()
    sys.exit(client.start())


if __name__ == "__main__":
    main()
