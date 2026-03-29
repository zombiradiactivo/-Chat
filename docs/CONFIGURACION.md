# Sistema de Configuración de Aplicación

## Descripción

El sistema de configuración permite guardar y cargar las preferencias de la aplicación en un archivo JSON (`data/app_config.json`).

## Funcionalidades

### 1. Configuración del Servidor
- **Host**: Dirección IP o dominio del servidor (default: 127.0.0.1)
- **Puerto**: Puerto de conexión (default: 5555)
- Las configuraciones se guardan automáticamente al hacer login

### 2. Preferencias de UI
- **Recordar usuario**: Checkbox para recordar el último usuario utilizado
- **Último usuario**: Se guarda solo si "Recordar usuario" está marcado
- **Último login**: Timestamp del último acceso exitoso

## Estructura del Archivo de Configuración

```json
{
    "server": {
        "host": "127.0.0.1",
        "port": 5555
    },
    "ui": {
        "remember_username": false,
        "last_username": null
    },
    "last_login": "2026-03-24T23:15:30.123456"
}
```

## Uso Programático

### Cargar configuración
```python
from ..utils.config_manager import ConfigManager

# Obtener toda la configuración
config = ConfigManager.load_config()

# Obtener solo configuración del servidor
server_config = ConfigManager.get_server_config()
# Returns: {'host': '127.0.0.1', 'port': 5555}

# Obtener último usuario recordado
last_user = ConfigManager.get_last_username()
```

### Guardar configuración
```python
from ..utils.config_manager import ConfigManager

# Guardar configuración del servidor
ConfigManager.set_server_config('192.168.1.100', 5555)

# Guardar usuario recordado
ConfigManager.set_last_username('usuario123', remember=True)

# Actualizar clave específica
ConfigManager.update_config('theme', 'dark')
```

## Ubicación del Archivo

El archivo de configuración se encuentra en:
```
data/app_config.json
```

Se crea automáticamente al iniciar la aplicación si no existe.

## Login - Nueva Interfaz

El login ahora incluye:
- Campos de Usuario y Contraseña (igual que antes)
- **Campos de Servidor**: Host y Puerto
- **Checkbox Recordar Usuario**: Para guardar el usuario automáticamente
- Validación de campos y puerto
- Carga automática de configuración guardada

## Ejemplo de Flujo

1. Usuario abre la aplicación
2. Se carga el login
3. Se cargan automáticamente las configuraciones guardadas (si existen)
4. Usuario ingresa credenciales y configura servidor si lo desea
5. Al hacer login, todo se guarda automáticamente
6. Próximo login usa la misma configuración

