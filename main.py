"""
Punto de entrada principal
"""
#!/usr/bin/env python3
"""
Chat App - Discord Clone
Aplicación de chat con interfaz gráfica, servidores, canales, roles y más.

Uso:
    python main.py              # Ejecuta la aplicación completa (cliente + opción de servidor integrado)
    python main.py client       # Ejecuta solo el cliente (conecta a servidor externo)
    python main.py server       # Ejecuta solo el servidor (sin interfaz gráfica)
"""

import sys
import argparse
from pathlib import Path

# Asegurar que el directorio src esté en el path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Chat App - Discord Clone',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                    # Ejecuta la aplicación completa
  %(prog)s client             # Ejecuta solo el cliente
  %(prog)s server --host 0.0.0.0 --port 5555  # Ejecuta solo el servidor
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['client', 'server'],
        help='Modo de ejecución: client (solo interfaz gráfica) o server (solo servidor)'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host para el servidor (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5555,
        help='Puerto para el servidor (default: 5555)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        # Ejecutar solo el servidor
        from server import ChatServer, main as server_main
        server = ChatServer(args.host, args.port)
        server.start()
        return 0
    elif args.mode == 'client':
        # Ejecutar solo el cliente
        from client import ChatClient, main as client_main
        client = ChatClient()
        return client.start()
    else:
        # Modo completo (por defecto)
        from src.app import ChatApp
        app = ChatApp()
        return app.run()


if __name__ == "__main__":
    sys.exit(main())
