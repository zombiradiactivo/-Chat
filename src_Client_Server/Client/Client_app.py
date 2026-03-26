"""
Aplicación principal de Chat - Discord Clone
"""
import sys
import os
import signal
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "Client"))

from src_Client_Server.Client.ui.main_window import MainWindow
from src_Client_Server.Client.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatApp:
    """Clase principal de la aplicación"""
    
    def __init__(self):
        self.root = None
        self.main_window = None
        self.repo_factory = None
            
    
    def run(self):
        """Ejecuta la aplicación"""
        try:
           
            # Crear ventana principal
            self.main_window = MainWindow()
            
            # Configurar cierre
            self.main_window.protocol("WM_DELETE_WINDOW")
            
            # Iniciar loop de eventos
            logger.info("Iniciando loop de eventos...")
            self.main_window.mainloop()
            
            return 0
            
        except Exception as e:
            logger.error(f"Error ejecutando aplicación: {e}")
            return 1

def main():
    """Función principal"""
    app = ChatApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
