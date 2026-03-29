"""
Configuración de tests
"""
import unittest
import sys
import os
from pathlib import Path

# Configurar path
test_dir = Path(__file__).parent
src_path = test_dir.parent / "src_Client_Server"
sys.path.insert(0, str(src_path))

# Configurar base de datos de test
os.environ['TEST_DB_PATH'] = str(test_dir / "test.db")

def main():
    """Función principal para ejecutar todos los tests"""
    # Descubrir y ejecutar todos los tests
    loader = unittest.TestLoader()
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Salir con código apropiado
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
