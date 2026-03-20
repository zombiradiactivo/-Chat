"""
Aplicación principal de Chat - Discord Clone
"""
import sys
import os
import signal
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui.main_window import MainWindow
from repositories import RepositoryFactory
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatApp:
    """Clase principal de la aplicación"""
    
    def __init__(self):
        self.root = None
        self.main_window = None
        self.repo_factory = None
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación"""
        logger.info("Recibida señal de terminación, cerrando aplicación...")
        self.cleanup()
        sys.exit(0)
    
    def initialize(self):
        """Inicializa la aplicación"""
        try:
            logger.info("Iniciando Chat App...")
            
            # Crear directorios necesarios
            self._create_directories()
            
            # Inicializar base de datos
            self.repo_factory = RepositoryFactory()
            self.repo_factory.initialize_database()
            
            logger.info("Aplicación inicializada correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando aplicación: {e}")
            return False
    
    def _create_directories(self):
        """Crea los directorios necesarios"""
        from utils import get_app_data_dir, get_uploads_dir, get_avatars_dir, get_banners_dir
        
        get_app_data_dir()
        get_uploads_dir()
        get_avatars_dir()
        get_banners_dir()
    
    def run(self):
        """Ejecuta la aplicación"""
        try:
            if not self.initialize():
                print("Error inicializando la aplicación")
                return 1
            
            # Crear ventana principal
            self.main_window = MainWindow()
            
            # Configurar cierre
            self.main_window.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            # Iniciar loop de eventos
            logger.info("Iniciando loop de eventos...")
            self.main_window.mainloop()
            
            return 0
            
        except Exception as e:
            logger.error(f"Error ejecutando aplicación: {e}")
            return 1
        finally:
            self.cleanup()
    
    def _on_closing(self):
        """Maneja el cierre de la ventana"""
        logger.info("Cerrando aplicación...")
        self.cleanup()
        if self.main_window:
            self.main_window.quit()
    
    def cleanup(self):
        """Limpia recursos"""
        try:
            if self.repo_factory:
                self.repo_factory.close_all()
                logger.info("Conexiones de base de datos cerradas")
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")


def main():
    """Función principal"""
    app = ChatApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
