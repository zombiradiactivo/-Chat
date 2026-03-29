"""
Tests unitarios
"""
import unittest
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_Client_Server"))

from src_Client_Server.Server.models.user import User, UserCreate
from src_Client_Server.Server.models.server import Server, ServerCreate
from src_Client_Server.Server.models.channel import Channel, ChannelCreate
from src_Client_Server.Server.models.message import Message, MessageCreate
from src_Client_Server.Server.models.role import Role, RoleCreate
from src_Client_Server.Server.utils.validation import validate_username, validate_email, validate_password


class TestModels(unittest.TestCase):
    """Tests para los modelos"""
    
    def test_user_creation(self):
        """Test creación de usuario"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }
        user_create = UserCreate(**user_data)
        self.assertEqual(user_create.username, 'testuser')
        self.assertEqual(user_create.email, 'test@example.com')
    
    def test_user_validation(self):
        """Test validación de usuario"""
        # Username válido
        is_valid, error = validate_username('valid_user')
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Username inválido (corto)
        is_valid, error = validate_username('ab')
        self.assertFalse(is_valid)
        
        # Username inválido (caracteres especiales)
        is_valid, error = validate_username('user@name')
        self.assertFalse(is_valid)
    
    def test_email_validation(self):
        """Test validación de email"""
        is_valid, error = validate_email('valid@email.com')
        self.assertTrue(is_valid)
        
        is_valid, error = validate_email('invalid-email')
        self.assertFalse(is_valid)
    
    def test_password_validation(self):
        """Test validación de contraseña"""
        is_valid, error = validate_password('longenough')
        self.assertTrue(is_valid)
        
        is_valid, error = validate_password('short')
        self.assertFalse(is_valid)


class TestServerModel(unittest.TestCase):
    """Tests para el modelo de servidor"""
    
    def test_server_creation(self):
        """Test creación de servidor"""
        server_data = {
            'name': 'Test Server',
            'owner_id': 'user123',
            'connection_type': 'client_server',
            'security_level': 'encrypted'
        }
        server = ServerCreate(**server_data)
        self.assertEqual(server.name, 'Test Server')
        self.assertEqual(server.owner_id, 'user123')


if __name__ == '__main__':
    unittest.main()
