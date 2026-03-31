"""
Tests de integración
"""
import unittest
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_Client_Server"))

from src_Client_Server.Server.services.auth_service import AuthService
from src_Client_Server.Server.services.server_service import ServerService
from src_Client_Server.Server.services.message_service import MessageService
from src_Client_Server.Server.services.invite_service import InviteService
from src_Client_Server.Server.repositories import RepositoryFactory


class TestIntegration(unittest.TestCase):
    """Tests de integración"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        # Usar base de datos de test
        import os
        test_db = Path(__file__).parent / "integration_test.db"
        os.environ['TEST_DB_PATH'] = str(test_db)
        
        cls.repo_factory = RepositoryFactory(str(test_db))
        cls.repo_factory.initialize_database()
        
        cls.auth_service = AuthService(cls.repo_factory)
        cls.server_service = ServerService(cls.repo_factory)
        cls.message_service = MessageService(cls.repo_factory)
        cls.invite_service = InviteService(cls.repo_factory)
        # Monkeypatch internal RepositoryFactory usage inside invite_service module
        import src_Client_Server.Server.services.invite_service as _invite_mod
        _invite_mod.RepositoryFactory = lambda *a, **k: cls.repo_factory
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza"""
        cls.repo_factory.close_all()
        # Try to force-close any stray connections, then remove DB
        import gc
        import src_Client_Server.Server.repositories as repos_mod
        test_db = Path(__file__).parent / "integration_test.db"
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
    
    def test_full_workflow(self):
        """Test flujo completo: registro -> crear servidor -> crear canal -> enviar mensaje"""
        # 1. Registrar usuario
        import uuid
        uname = f'integration_{uuid.uuid4().hex[:8]}'
        success, error, user = self.auth_service.register(
            username=uname,
            email=f'{uname}@test.com',
            password='password123'
        )
        self.assertTrue(success)
        self.assertIsNotNone(user)
        
        # 2. Crear servidor
        success, error, server = self.server_service.create_server(
            owner_id=user.id,
            name='Integration Test Server',
            description='Testing full workflow'
        )
        self.assertTrue(success)
        self.assertIsNotNone(server)
        
        # 3. Crear canal
        from src_Client_Server.Server.models.enums import ChannelType
        success, error, channel = self.server_service.create_channel(
            server_id=server.id,
            creator_id=user.id,
            name='test-channel',
            type=ChannelType.TEXT
        )
        self.assertTrue(success)
        self.assertIsNotNone(channel)
        
        # 4. Enviar mensaje
        success, error, message = self.message_service.send_message(
            content='Hello, World!',
            channel_id=channel.id,
            author_id=user.id
        )
        self.assertTrue(success)
        self.assertIsNotNone(message)
        self.assertEqual(message.content, 'Hello, World!')
        
        # 5. Obtener mensajes del canal
        messages = self.message_service.get_channel_messages(channel.id)
        self.assertGreater(len(messages), 0)
        self.assertEqual(messages[0].content, 'Hello, World!')
        
        # 6. Crear invitación
        success, error, invite = self.invite_service.create_invite(
            server_id=server.id,
            creator_id=user.id,
            max_uses=5
        )
        self.assertTrue(success)
        self.assertIsNotNone(invite)
        self.assertEqual(invite.max_uses, 5)
        
        # 7. Aceptar invitación (con otro usuario)
        uname2 = f'second_{uuid.uuid4().hex[:8]}'
        success2, error2, user2 = self.auth_service.register(
            username=uname2,
            email=f'{uname2}@test.com',
            password='password123'
        )
        self.assertTrue(success2)
        
        success, error, joined_server = self.invite_service.accept_invite(
            user_id=user2.id,
            code=invite.code
        )
        self.assertTrue(success)
        self.assertIsNotNone(joined_server)
        
        # 8. Verificar que la invitación se consumió (aceptada)
        invites_repo = self.repo_factory.get_repository('invites')
        stored_invite = invites_repo.get_by_code(invite.code)
        self.assertIsNotNone(stored_invite)
        self.assertGreater(stored_invite.uses, 0)


if __name__ == '__main__':
    unittest.main()
