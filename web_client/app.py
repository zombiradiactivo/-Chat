"""
Web Client App - Flask + SocketIO bridge to TCP Server
"""
import json
import socket
import threading
import time
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chat-web-client-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuración del servidor TCP
TCP_HOST = '127.0.0.1'
TCP_PORT = 5555

# Almacenar conexiones TCP por sesión
tcp_connections = {}
tcp_lock = threading.Lock()


class TCPBridge:
    """Puente entre WebSocket (navegador) y servidor TCP"""

    def __init__(self, session_id):
        self.session_id = session_id
        self.socket = None
        self.connected = False
        self.running = False
        self.receiver_thread = None

    def connect(self, host, port):
        """Conecta al servidor TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.running = True

            self.receiver_thread = threading.Thread(
                target=self._receive_messages,
                daemon=True
            )
            self.receiver_thread.start()
            return True
        except Exception as e:
            print(f"Error connecting to TCP server: {e}")
            return False

    def disconnect(self):
        """Desconecta del servidor TCP"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def send(self, message_dict):
        """Envía un mensaje al servidor TCP"""
        if not self.connected or not self.socket:
            return False
        try:
            json_str = json.dumps(message_dict)
            self.socket.send(json_str.encode())
            return True
        except Exception as e:
            print(f"Error sending to TCP: {e}")
            self.connected = False
            return False

    def _receive_messages(self):
        """Recibe mensajes del servidor TCP y los reenvía al WebSocket"""
        while self.running and self.socket:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break

                message = json.loads(data.decode())
                socketio.emit('server_message', message, room=self.session_id)

            except Exception as e:
                if self.running:
                    print(f"Error receiving from TCP: {e}")
                break

        self.connected = False
        socketio.emit('disconnected', {}, room=self.session_id)


def get_tcp_bridge(session_id):
    """Obtiene o crea un puente TCP para la sesión"""
    with tcp_lock:
        if session_id not in tcp_connections:
            tcp_connections[session_id] = TCPBridge(session_id)
        return tcp_connections[session_id]


def remove_tcp_bridge(session_id):
    """Elimina un puente TCP"""
    with tcp_lock:
        if session_id in tcp_connections:
            tcp_connections[session_id].disconnect()
            del tcp_connections[session_id]


# Rutas HTTP
@app.route('/')
def index():
    return render_template('index.html')


# Eventos SocketIO
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    print(f"Client disconnected: {session_id}")
    remove_tcp_bridge(session_id)


@socketio.on('tcp_connect')
def handle_tcp_connect(data):
    """Conecta al servidor TCP"""
    session_id = request.sid
    host = data.get('host', TCP_HOST)
    port = int(data.get('port', TCP_PORT))

    bridge = get_tcp_bridge(session_id)
    if bridge.connected:
        emit('tcp_connected', {'success': True})
        return

    if bridge.connect(host, port):
        emit('tcp_connected', {'success': True})
    else:
        emit('tcp_connected', {
            'success': False,
            'error': 'No se pudo conectar al servidor'
        })


@socketio.on('tcp_disconnect')
def handle_tcp_disconnect():
    """Desconecta del servidor TCP"""
    session_id = request.sid
    remove_tcp_bridge(session_id)
    emit('tcp_disconnected', {})


@socketio.on('tcp_send')
def handle_tcp_send(data):
    """Envía un mensaje al servidor TCP"""
    session_id = request.sid
    bridge = get_tcp_bridge(session_id)

    if not bridge.connected:
        emit('error', {'message': 'No conectado al servidor'})
        return

    if not bridge.send(data):
        emit('error', {'message': 'Error enviando mensaje'})


# Importar request para obtener sid
from flask import request

if __name__ == '__main__':
    print("Iniciando Web Client en http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
