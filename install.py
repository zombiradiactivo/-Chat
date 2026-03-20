"""
Script de instalación y verificación de dependencias
"""
import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def install_package(package):
    """Instala un paquete con pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Error instalando {package}")
        return False

def check_and_install_dependencies():
    """Verifica e instala dependencias"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ No se encontró requirements.txt")
        return False
    
    print("\n📦 Verificando dependencias...")
    
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    all_installed = True
    for req in requirements:
        package = req.split('>=')[0].split('==')[0].strip()
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"⚠️  {package} no encontrado, instalando...")
            if not install_package(req):
                all_installed = False
    
    return all_installed

def create_directories():
    """Crea los directorios necesarios"""
    print("\n📁 Creando directorios...")
    
    directories = [
        "data",
        "data/uploads",
        "data/avatars",
        "data/banners",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ {directory}/")
    
    return True

def main():
    """Función principal de instalación"""
    print("=" * 50)
    print("CHAT APP - INSTALADOR")
    print("=" * 50)
    
    # Verificar Python
    if not check_python_version():
        return False
    
    # Instalar dependencias
    if not check_and_install_dependencies():
        print("\n❌ Algunas dependencias no se pudieron instalar")
        print("   Intenta ejecutar manualmente:")
        print("   pip install -r requirements.txt")
        return False
    
    # Crear directorios
    if not create_directories():
        return False
    
    print("\n" + "=" * 50)
    print("✅ INSTALACIÓN COMPLETADA")
    print("=" * 50)
    print("\nPara ejecutar la aplicación:")
    print("  python main.py")
    print("\nPara ejecutar tests:")
    print("  python run_tests.py")
    print("\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
