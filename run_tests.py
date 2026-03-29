"""
Ejecutor de tests
"""
#!/usr/bin/env python3
"""
Ejecuta todos los tests de la aplicación
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src_Client_Server"))

if __name__ == "__main__":
    import unittest
    from tests_Client_Server.Server.run_tests import main
    
    sys.exit(main())
