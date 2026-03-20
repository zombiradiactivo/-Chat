#!/usr/bin/env python3
"""
Script de verificación de instalación
"""

import sys
import importlib.util
from pathlib import Path

def check_module(module_name, import_name=None):
    """Verifica si un módulo está instalado"""
    if import_name is None:
        import_name = module_name
    
    spec = importlib.util.find_spec(import_name)
    if spec is not None:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'desconocida')
            print(f"✅ {module_name}: {version}")
            return True
        except ImportError:
            print(f"❌ {module_name}: Error al importar")
            return False
    else:
        print(f"❌ {module_name}: No instalado")
        return False

def main():
    print("=" * 60)
    print("VERIFICACIÓN DE INSTALACIÓN - Chat App")
    print("=" * 60)
    print()
    
    modules_to_check = [
        ("Python", None),  # Se verifica aparte
        ("CustomTkinter", "customtkinter"),
        ("Cryptography", "cryptography"),
        ("Pillow", "PIL"),
        ("OpenCV", "cv2"),
        ("NumPy", "numpy"),
    ]
    
    all_ok = True
    
    # Verificar Python
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python: {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"❌ Python: Se requiere 3.8+, tienes {version.major}.{version.minor}.{version.micro}")
        all_ok = False
    
    # Verificar módulos
    for name, import_name in modules_to_check:
        if import_name:
            if not check_module(name, import_name):
                all_ok = False
    
    print()
    print("-" * 60)
    
    # Verificar directorios
    print("\n📁 Verificando directorios...")
    directories = [
        "src",
        "src/models",
        "src/repositories",
        "src/services",
        "src/network",
        "src/ui",
        "src/utils",
        "data",
        "logs",
        "tests",
    ]
    
    for directory in directories:
        if Path(directory).exists():
            print(f"✅ {directory}/")
        else:
            print(f"❌ {directory}/ - No encontrado")
            all_ok = False
    
    print()
    print("-" * 60)
    
    # Verificar archivos principales
    print("\n📄 Verificando archivos principales...")
    files = [
        "main.py",
        "src/app.py",
        "requirements.txt",
        "config.py",
        "README.md",
    ]
    
    for file in files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - No encontrado")
            all_ok = False
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✅ ¡TODO ESTÁ CORRECTO!")
        print("\nPuedes ejecutar la aplicación con:")
        print("  python main.py")
        print("\nO en modo desarrollo:")
        print("  python dev.py")
    else:
        print("❌ HAY PROBLEMAS DE INSTALACIÓN")
        print("\nEjecuta el instalador:")
        print("  python install.py")
        print("\nO instala manualmente:")
        print("  pip install -r requirements.txt")
    
    print("=" * 60)
    print()
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
