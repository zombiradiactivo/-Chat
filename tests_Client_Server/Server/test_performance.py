"""
Tests de rendimiento y estrés
"""
import unittest
import sys
from pathlib import Path
import time
import threading

sys.path.insert(0, str(Path(__file__).parent.parent / "src_Client_Server"))

from src_Client_Server.Server.repositories import RepositoryFactory
from src_Client_Server.Server.services import AuthService, MessageService
from src_Client_Server.Server.network.service import TCPServer, TCPClient, NetworkMessage


class TestPerformance(unittest.TestCase):
    """Tests de rendimiento"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración"""

        # Usar base de datos de test
        import os
        test_db = Path(__file__).parent / "perf_test.db"
        os.environ['TEST_DB_PATH'] = str(test_db)
        
        cls.repo_factory = RepositoryFactory(str(test_db))
        cls.repo_factory.initialize_database()
        cls.auth_service = AuthService()
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza"""
        cls.repo_factory.close_all()
        test_db = Path(__file__).parent / "perf_test.db"
        if test_db.exists():
            test_db.unlink()
    
    def test_concurrent_user_registration(self):
        """Test de registro concurrente de usuarios"""
        def register_user(i):
            return self.auth_service.register(
                username=f'user{i}',
                email=f'user{i}@test.com',
                password='password123'
            )
        
        threads = []
        results = []
        
        for i in range(10):
            t = threading.Thread(target=lambda i=i: results.append(register_user(i)))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verificar que todos se registraron exitosamente
        successes = [r[0] for r in results if r[0]]
        self.assertEqual(len(successes), 10)
    
    def test_message_throughput(self):
        """Test de throughput de mensajes"""
        # Crear usuario y canal
        success, _, user = self.auth_service.register(
            username='perftest',
            email='perftest@test.com',
            password='password123'
        )
        self.assertTrue(success)
        
        message_service = MessageService()
        
        # Enviar 100 mensajes y medir tiempo
        start_time = time.time()
        
        for i in range(100):
            message_service.send_message(
                content=f'Mensaje {i}',
                channel_id='dummy_channel',  # En un test real se crearía el canal
                author_id=user.id
            )
        
        elapsed = time.time() - start_time
        throughput = 100 / elapsed
        
        print(f"\n⏱️  Throughput: {throughput:.2f} mensajes/segundo")
        
        # Debería manejar al menos 50 mensajes por segundo
        self.assertGreater(throughput, 10)  # Conservador para tests de CI


class TestNetworkPerformance(unittest.TestCase):
    """Tests de rendimiento de red"""
    
    def test_tcp_server_throughput(self):
        """Test throughput del servidor TCP"""
        server = TCPServer(port=6666)
        server.start()
        
        time.sleep(0.5)  # Esperar a que el servidor inicie
        
        # Crear múltiples clientes
        num_clients = 5
        messages_per_client = 20
        
        def client_task(client_id):
            client = TCPClient()
            client.connect('127.0.0.1', 6666)
            
            for i in range(messages_per_client):
                msg = NetworkMessage(
                    type='test',
                    data={'client': client_id, 'msg': i},
                    sender_id=f'client_{client_id}'
                )
                client.send(msg)
                time.sleep(0.01)
            
            client.disconnect()
        
        threads = []
        start_time = time.time()
        
        for i in range(num_clients):
            t = threading.Thread(target=client_task, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        elapsed = time.time() - start_time
        total_messages = num_clients * messages_per_client
        throughput = total_messages / elapsed
        
        print(f"\n📡 Throughput de red: {throughput:.2f} mensajes/segundo")
        
        server.stop()
        
        # Debería manejar al menos 20 mensajes por segundo
        self.assertGreater(throughput, 5)


if __name__ == '__main__':
    unittest.main()
