"""
Tests para utilidades
"""
import unittest
import sys
from pathlib import Path
import tempfile
import os

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_Client_Server"))

from src_Client_Server.Server.utils import (
    generate_id,
    generate_invite_code,
    format_file_size,
    sanitize_filename,
    is_valid_image,
    is_valid_video,
    compute_file_hash
)


class TestUtils(unittest.TestCase):
    """Tests para utilidades"""
    
    def test_generate_id(self):
        """Test generación de IDs"""
        id1 = generate_id()
        id2 = generate_id()
        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
    
    def test_generate_invite_code(self):
        """Test generación de códigos de invitación"""
        code = generate_invite_code(8)
        self.assertEqual(len(code), 8)
        self.assertTrue(code.isalnum())
        self.assertTrue(code.isupper())
    
    def test_format_file_size(self):
        """Test formateo de tamaño de archivo"""
        self.assertEqual(format_file_size(1024), "1.00 KB")
        self.assertEqual(format_file_size(1048576), "1.00 MB")
        self.assertEqual(format_file_size(500), "500.00 B")
    
    def test_sanitize_filename(self):
        """Test sanitización de nombres de archivo"""
        dangerous = 'file<>:"/\\|?*.txt'
        safe = sanitize_filename(dangerous)
        self.assertNotIn('<', safe)
        self.assertNotIn('>', safe)
        self.assertNotIn(':', safe)
    
    def test_is_valid_image(self):
        """Test validación de imágenes"""
        self.assertTrue(is_valid_image('photo.png'))
        self.assertTrue(is_valid_image('image.jpg'))
        self.assertTrue(is_valid_image('animation.gif'))
        self.assertFalse(is_valid_image('document.pdf'))
    
    def test_is_valid_video(self):
        """Test validación de videos"""
        self.assertTrue(is_valid_video('video.mp4'))
        self.assertTrue(is_valid_video('movie.avi'))
        self.assertFalse(is_valid_video('image.png'))
    
    def test_compute_file_hash(self):
        """Test cálculo de hash de archivo"""
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            file_hash = compute_file_hash(temp_path)
            self.assertIsInstance(file_hash, str)
            self.assertEqual(len(file_hash), 64)  # SHA-256 tiene 64 hex chars
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()
