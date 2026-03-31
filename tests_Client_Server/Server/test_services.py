"""
Tests para servicios
"""
import os
import unittest
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_Client_Server"))

# Configurar base de datos de test
test_db = Path(__file__).parent / "test.db"
os.environ['TEST_DB_PATH'] = str(test_db)

from src_Client_Server.Server.repositories import RepositoryFactory
from src_Client_Server.Server.services.auth_service import AuthService
from src_Client_Server.Server.services.server_service import ServerService
from src_Client_Server.Server.utils.validation import validate_username, validate_email, validate_password


class TestAuthService(unittest.TestCase):
    """Tests para el servicio de autenticación"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        # Ensure a clean test database
        import os
        if test_db.exists():
            test_db.unlink()

        cls.repo_factory = RepositoryFactory(str(test_db))
        cls.repo_factory.initialize_database()
        cls.auth_service = AuthService(cls.repo_factory)
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza"""
        cls.repo_factory.close_all()
        import gc
        import src_Client_Server.Server.repositories as repos_mod
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



    def test_register_user(self):
        """Test registro de usuario"""
        import uuid
        username = f"user_{uuid.uuid4().hex[:8]}"
        success, error, user = self.auth_service.register(
            username=username,
            email=f'{username}@example.com',
            password='password123'
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(user)
    
    def test_register_duplicate_username(self):
        """Test registro con username duplicado"""
        # Register a user, then attempt to register another with same username
        username = 'dupuser'
        success, error, user = self.auth_service.register(
            username=username,
            email='dup1@example.com',
            password='password123'
        )
        self.assertTrue(success)

        success2, error2, user2 = self.auth_service.register(
            username=username,
            email='dup2@example.com',
            password='password123'
        )
        self.assertFalse(success2)
        self.assertIsNotNone(error2)
    
    def test_login_user(self):
        """Test login de usuario"""
        # Create a user specifically for login test
        username = 'loginuser'
        self.auth_service.register(username=username, email='login@example.com', password='password123')
        success, error, user = self.auth_service.login(
            identifier=username,
            password='password123'
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(user)
    
    def test_login_wrong_password(self):
        """Test login con contraseña incorrecta"""
        # Ensure user exists
        username = 'loginuser2'
        self.auth_service.register(username=username, email='login2@example.com', password='password123')
        success, error, user = self.auth_service.login(
            identifier=username,
            password='wrongpassword'
        )
        self.assertFalse(success)
        self.assertIsNotNone(error)


class TestServerService(unittest.TestCase):
    """Tests para el servicio de servidores"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        # Use the test database for services
        cls.repo_factory = RepositoryFactory(str(test_db))
        cls.repo_factory.initialize_database()
        cls.server_service = ServerService(cls.repo_factory)
        cls.auth_service = AuthService(cls.repo_factory)
        
        # Crear usuario de prueba
        # Create and login a test user
        success, _, user = cls.auth_service.register(
            username='serveradmin',
            email='admin@example.com',
            password='password123'
        )

        if not success:
            cls.user_id = None
            return

        success, _, user = cls.auth_service.login(
            identifier='serveradmin',
            password='password123'
        )

        cls.user_id = user.id if success else None
    
    def test_create_server(self):
        """Test crear servidor"""
        if not self.user_id:
            self.skipTest("No se pudo crear usuario de prueba")
        
        success, error, server = self.server_service.create_server(
            owner_id=self.user_id,
            name='Test Server',
            description='A test server'
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(server)
    
    def test_get_user_servers(self):
        """Test obtener servidores de usuario"""
        servers = self.server_service.get_user_servers(self.user_id)
        self.assertIsInstance(servers, list)


if __name__ == '__main__':
    unittest.main()
