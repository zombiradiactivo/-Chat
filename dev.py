"""
Script de desarrollo con recarga automática
"""
#!/usr/bin/env python3
"""
Ejecuta la aplicación con recarga automática en desarrollo
Requiere: pip install watchdog
"""

import sys
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import signal

class ReloadHandler(FileSystemEventHandler):
    """Maneja eventos de cambio de archivos"""
    
    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.restart()
    
    def restart(self):
        """Reinicia la aplicación"""
        if self.process:
            print("\n🔄 Reiniciando aplicación...")
            self.process.terminate()
            self.process.wait()
        
        print(f"🚀 Iniciando {self.script_path}...")
        self.process = subprocess.Popen([sys.executable, str(self.script_path)])
    
    def on_modified(self, event):
        """Maneja modificaciones de archivos"""
        if event.src_path.endswith('.py'): # type: ignore
            print(f"\n📝 Cambio detectado: {event.src_path}")
            self.restart()
    
    def on_created(self, event):
        """Maneja creación de archivos"""
        if event.src_path.endswith('.py'): # type: ignore
            print(f"\n📝 Archivo creado: {event.src_path}")
            self.restart()

def main():
    """Función principal"""
    script_path = Path(__file__).parent / "run.py"
    
    if not script_path.exists():
        print(f"❌ No se encuentra {script_path}")
        return 1
    
    print("=" * 50)
    print("MODO DESARROLLO - RECARGA AUTOMÁTICA")
    print("=" * 50)
    print("Presiona Ctrl+C para salir\n")
    
    handler = ReloadHandler(script_path)
    observer = Observer()
    observer.schedule(handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo...")
        observer.stop()
        if handler.process:
            handler.process.terminate()
            handler.process.wait()
        observer.join()
    
    return 0

if __name__ == "__main__":
    try:
        from watchdog.observers import Observer
    except ImportError:
        print("❌ watchdog no instalado. Ejecuta:")
        print("   pip install watchdog")
        sys.exit(1)
    
    sys.exit(main())
