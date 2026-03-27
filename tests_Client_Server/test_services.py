"""
Tests para servicios
"""
import unittest
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.services.auth_service import AuthService
from src.services.server_service import ServerService
from src.utils.validation import validate_username, validate_email, validate_password


class TestAuthService(unittest.TestCase):
    """Tests para el servicio de autenticación"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        cls.auth_service = AuthService()
    
    def test_register_user(self):
        """Test registro de usuario"""
        success, error, user = self.auth_service.register(
            username='newuser',
            email='new@example.com',
            password='password123'
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(user)
    
    def test_register_duplicate_username(self):
        """Test registro con username duplicado"""
        success, error, user = self.auth_service.register(
            username='newuser',
            email='different@example.com',
            password='password123'
        )
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    def test_login_user(self):
        """Test login de usuario"""
        success, error, user = self.auth_service.login(
            identifier='newuser',
            password='password123'
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(user)
    
    def test_login_wrong_password(self):
        """Test login con contraseña incorrecta"""
        success, error, user = self.auth_service.login(
            identifier='newuser',
            password='wrongpassword'
        )
        self.assertFalse(success)
        self.assertIsNotNone(error)


class TestServerService(unittest.TestCase):
    """Tests para el servicio de servidores"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        cls.server_service = ServerService()
        cls.auth_service = AuthService()
        
        # Crear usuario de prueba
        success, _, user = cls.auth_service.register(
            username='serveradmin',
            email='admin@example.com',
            password='password123'
        )

        """Test login de usuario"""
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
