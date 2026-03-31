#!/usr/bin/env python3
"""
Cliente Web de Chat App
Ejecuta el cliente web basado en Flask + SocketIO
"""
import sys
import signal
import argparse
from pathlib import Path

# Asegurar que el directorio del proyecto esté en el path
project_path = Path(__file__).parent
if str(project_path) not in sys.path:
    sys.path.insert(0, str(project_path))


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Cliente Web de Chat App')
    parser.add_argument('--host', default='0.0.0.0', help='Host para el servidor web (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Puerto para el servidor web (default: 5000)')
    parser.add_argument('--tcp-host', default='127.0.0.1', help='Host del servidor TCP (default: 127.0.0.1)')
    parser.add_argument('--tcp-port', type=int, default=5555, help='Puerto del servidor TCP (default: 5555)')
    parser.add_argument('--debug', action='store_true', help='Modo debug')

    args = parser.parse_args()

    # Configurar el bridge TCP
    import web_client.app as web_app
    web_app.TCP_HOST = args.tcp_host
    web_app.TCP_PORT = args.tcp_port

    # Manejar señales de terminación
    def signal_handler(signum, frame):
        print("\nCerrando servidor web...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"""
╔══════════════════════════════════════════╗
║        Chat App - Cliente Web            ║
╠══════════════════════════════════════════╣
║  Web:    http://{args.host}:{args.port}         ║
║  TCP:    {args.tcp_host}:{args.tcp_port}              ║
╚══════════════════════════════════════════╝
    """)

    # Iniciar el servidor web
    web_app.socketio.run(
        web_app.app,
        host=args.host,
        port=args.port,
        debug=args.debug,
        allow_unsafe_werkzeug=True
    )


if __name__ == "__main__":
    main()
