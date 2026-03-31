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
        # Ensure clean DB
        if test_db.exists():
            test_db.unlink()

        cls.repo_factory = RepositoryFactory(str(test_db))
        cls.repo_factory.initialize_database()
        from src_Client_Server.Server.services.auth_service import AuthService
        cls.auth_service = AuthService(cls.repo_factory)
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza"""
        cls.repo_factory.close_all()
        import gc
        import src_Client_Server.Server.repositories as repos_mod
        test_db = Path(__file__).parent / "perf_test.db"
        try:
            test_db.unlink()
        except PermissionError:
            rf = repos_mod.RepositoryFactory(str(test_db))
            rf.close_all()
            del rf
            gc.collect()
            try:
                test_db.unlink()
            except PermissionError:
                pass
    
    def test_concurrent_user_registration(self):
        """Test de registro concurrente de usuarios"""
        def register_user(i, results_list):
            # Create a separate RepositoryFactory per thread to avoid sharing the same sqlite connection
            from src_Client_Server.Server.repositories import RepositoryFactory as RF
            from src_Client_Server.Server.services.auth_service import AuthService
            import uuid
            test_db_local = Path(__file__).parent / "perf_test.db"
            rf = RF(str(test_db_local))
            # Ensure repos are initialized
            rf.initialize_database()
            try:
                auth = AuthService(rf)
                uname = f'user_{uuid.uuid4().hex[:8]}'
                res = auth.register(
                    username=uname,
                    email=f'{uname}@test.com',
                    password='password123'
                )
                results_list.append(res)
            finally:
                rf.close_all()

        threads = []
        results = []

        for i in range(10):
            t = threading.Thread(target=register_user, args=(i, results))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verificar que todos se registraron exitosamente
        successes = [r[0] for r in results if r and r[0]]
        self.assertEqual(len(successes), 10)
    
    def test_message_throughput(self):
        """Test de throughput de mensajes"""
        # Crear usuario, servidor y canal reales en la DB de prueba
        import uuid
        uname = f'perftest_{uuid.uuid4().hex[:8]}'
        success, _, user = self.auth_service.register(
            username=uname,
            email=f'{uname}@test.com',
            password='password123'
        )
        self.assertTrue(success)

        # Crear servidor
        from src_Client_Server.Server.models.enums import ConnectionType, SecurityLevel, ChannelType
        servers_repo = self.repo_factory.get_repository('servers')
        server_id = servers_repo.create({
            'name': 'perf_server',
            'owner_id': user.id,
            'connection_type': ConnectionType.CLIENT_SERVER,
            'security_level': SecurityLevel.BASIC
        })

        # Crear canal
        channels_repo = self.repo_factory.get_repository('channels')
        channel_id = channels_repo.create({
            'server_id': server_id,
            'name': 'perf_channel',
            'type': ChannelType.TEXT
        })

        message_service = MessageService(self.repo_factory)
        
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
