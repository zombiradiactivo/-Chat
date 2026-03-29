"""
Tests para repositorios
"""
import unittest
import sys
import os
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_Client_Server"))

# Configurar base de datos de test
test_db = Path(__file__).parent / "test.db"
os.environ['TEST_DB_PATH'] = str(test_db)

from src_Client_Server.Server.repositories.user_repository import UserRepository
from src_Client_Server.Server.repositories.server_repository import ServerRepository
from src_Client_Server.Server.models.user import UserCreate


class TestUserRepository(unittest.TestCase):
    """Tests para el repositorio de usuarios"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        cls.repo = UserRepository(str(test_db))
        cls.repo.initialize()
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza"""
        cls.repo.close()
        if test_db.exists():
            test_db.unlink()
    
    def test_create_user(self):
        """Test crear usuario"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }
        user_id = self.repo.create(user_data)
        self.assertIsNotNone(user_id)
        
        user = self.repo.get_by_id(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
    
    def test_get_by_username(self):
        """Test obtener usuario por nombre"""
        user = self.repo.get_by_username('testuser')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
    
    def test_verify_password(self):
        """Test verificación de contraseña"""
        user = self.repo.get_by_username('testuser')
        self.assertTrue(self.repo.verify_password(user.id, 'password123'))
        self.assertFalse(self.repo.verify_password(user.id, 'wrongpassword'))
    
    def test_update_user(self):
        """Test actualizar usuario"""
        user = self.repo.get_by_username('testuser')
        success = self.repo.update(user.id, {'description': 'Test description'})
        self.assertTrue(success)
        
        updated = self.repo.get_by_id(user.id)
        self.assertEqual(updated.description, 'Test description')
    
    def test_delete_user(self):
        """Test eliminar usuario (soft delete)"""
        user = self.repo.get_by_username('testuser')
        success = self.repo.delete(user.id)
        self.assertTrue(success)
        
        # El usuario debería existir pero no estar activo
        deleted = self.repo.get_by_id(user.id)
        self.assertFalse(deleted.is_active)


class TestServerRepository(unittest.TestCase):
    """Tests para el repositorio de servidores"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        cls.user_repo = UserRepository(str(test_db))
        cls.user_repo.initialize()
        cls.server_repo = ServerRepository(str(test_db))
        cls.server_repo.initialize()
        
        # Crear usuario de prueba
        cls.user_id = cls.user_repo.create({
            'username': 'serverowner',
            'email': 'owner@example.com',
            'password': 'password123'
        })
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza"""
        cls.server_repo.close()
        cls.user_repo.close()
        if test_db.exists():
            test_db.unlink()
    
    def test_create_server(self):
        """Test crear servidor"""
        server_data = {
            'name': 'Test Server',
            'owner_id': self.user_id,
            'connection_type': 'client_server',
            'security_level': 'encrypted'
        }
        server_id = self.server_repo.create(server_data)
        self.assertIsNotNone(server_id)
        
        server = self.server_repo.get_by_id(server_id)
        self.assertIsNotNone(server)
        self.assertEqual(server.name, 'Test Server')
    
    def test_get_by_owner(self):
        """Test obtener servidores por dueño"""
        servers = self.server_repo.get_by_owner(self.user_id)
        self.assertGreater(len(servers), 0)
    
    def test_update_server(self):
        """Test actualizar servidor"""
        servers = self.server_repo.get_by_owner(self.user_id)
        server = servers[0]
        
        success = self.server_repo.update(server.id, {'description': 'Updated description'})
        self.assertTrue(success)
        
        updated = self.server_repo.get_by_id(server.id)
        self.assertEqual(updated.description, 'Updated description')
    
    def test_delete_server(self):
        """Test eliminar servidor"""
        servers = self.server_repo.get_by_owner(self.user_id)
        server = servers[0]
        
        success = self.server_repo.delete(server.id)
        self.assertTrue(success)
        
        deleted = self.server_repo.get_by_id(server.id)
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()
