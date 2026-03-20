"""
Punto de entrada principal
"""
#!/usr/bin/env python3
"""
Chat App - Discord Clone
Aplicación de chat con interfaz gráfica, servidores, canales, roles y más.
"""

import sys
from pathlib import Path

# Asegurar que el directorio src esté en el path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.app import main

if __name__ == "__main__":
    sys.exit(main())
