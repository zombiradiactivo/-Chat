"""
Script para empaquetar la aplicación
"""
import sys
from pathlib import Path
import subprocess
import shutil

def package_app():
    """Empaqueta la aplicación como ejecutable"""
    print("=" * 50)
    print("EMPAQUETANDO APLICACIÓN")
    print("=" * 50)
    
    # Verificar PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("⚠️  PyInstaller no instalado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Crear spec file personalizado
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{Path(__file__).parent / "main.py"}'],
    pathex=[],
    binaries=[],
    datas=[
        ('{Path(__file__).parent / "config.py"}', '.'),
        ('{Path(__file__).parent / "src"}', 'src'),
        ('{Path(__file__).parent / "requirements.txt"}', '.')
    ],
    hiddenimports=[
        'customtkinter',
        'cryptography',
        'PIL',
        'cv2',
        'numpy'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChatApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False para sin consola, True para con consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    spec_file = Path("ChatApp.spec")
    spec_file.write_text(spec_content)
    
    print(f"✅ Spec file creado: {spec_file}")
    
    # Ejecutar PyInstaller
    print("\n🔨 Construyendo ejecutable...")
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)])
    
    if result.returncode == 0:
        print("\n✅ Ejecutable creado en: dist/ChatApp")
        print("   (o ChatApp.exe en Windows)")
    else:
        print("\n❌ Error construyendo ejecutable")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(package_app())
