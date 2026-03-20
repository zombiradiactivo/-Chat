"""
Script para ejecutar la aplicación con argumentos
"""
#!/usr/bin/env python3
"""
Ejecutor de la aplicación con opciones
"""

import sys
import argparse
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    parser = argparse.ArgumentParser(description="Chat App - Discord Clone")
    parser.add_argument('--debug', action='store_true', help='Modo debug con logs detallados')
    parser.add_argument('--no-db-init', action='store_true', help='No inicializar la base de datos')
    parser.add_argument('--reset-db', action='store_true', help='Resetear la base de datos')
    parser.add_argument('--test', action='store_true', help='Ejecutar tests')
    parser.add_argument('--test-coverage', action='store_true', help='Ejecutar tests con coverage')
    
    args = parser.parse_args()
    
    if args.test or args.test_coverage:
        # Ejecutar tests
        import subprocess
        test_cmd = [sys.executable, "run_tests.py"]
        if args.test_coverage:
            try:
                import coverage
                test_cmd = ["coverage", "run", "-m", "tests.run_tests"]
            except ImportError:
                print("⚠️  Coverage no instalado, ejecutando sin coverage")
        
        result = subprocess.run(test_cmd)
        sys.exit(result.returncode)
    
    # Configurar logging según modo
    if args.debug:
        import os
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # Resetear DB si se solicita
    if args.reset_db:
        from pathlib import Path
        db_path = Path("data/chat.db")
        if db_path.exists():
            db_path.unlink()
            print("✅ Base de datos eliminada")
    
    # Ejecutar aplicación
    from src.app import main
    sys.exit(main())

if __name__ == "__main__":
    main()
