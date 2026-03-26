# Chat App - Discord Clone

Aplicación de chat estilo Discord completa desarrollada en Python con interfaz gráfica moderna usando CustomTkinter.

## Características

### ✅ Funcionalidades Implementadas

- **Sistema de Autenticación**
  - Registro de usuarios con validación
  - Login con username/email
  - Perfiles de usuario (foto, descripción, banner)
  - Gestión de sesiones

- **Servidores/Grupos**
  - Crear servidores con configuración completa
  - Opciones de configuración:
    - Nombre e icono personalizado
    - Tipo de conectividad: Cliente-Servidor, P2P, Híbrido
    - Nivel de seguridad: None, Basic, Encrypted, End-to-End
    - Límite de miembros
    - Transferencia de archivos (activar/desactivar)
    - Video/audio streaming (activar/desactivar)
    - Verificación requerida para unirse
  - Unirse/abandonar servidores
  - Sistema de invitaciones con códigos

- **Canales**
  - Canales de texto
  - Canales de voz
  - Canales de video (transmisión de cámara/pantalla)
  - Canales privados con roles específicos
  - Jerarquía de canales (categorías)

- **Sistema de Roles y Permisos**
  - Roles personalizables por servidor
  - Jerarquía de roles (posición)
  - Permisos granulares:
    - Gestión de servidor
    - Gestión de canales
    - Gestión de roles
    - Gestión de miembros (kick/ban)
    - Gestión de mensajes
    - Permisos de texto
    - Permisos de voz/video
    - Permisos de archivos
  - Rol @everyone por defecto
  - Roles mencionables y destacados

- **Mensajería**
  - Envío de mensajes de texto
  - Edición y eliminación de mensajes
  - Reacciones a mensajes
  - Mensajes fijados
  - Respuestas a mensajes
  - Menciones a usuarios
  - Adjuntar archivos

- **Transferencia de Archivos**
  - Subida y descarga de archivos
  - Encriptación opcional
  - Transferencia en chunks
  - Verificación de integridad (hash SHA-256)
  - Soporte para cualquier tipo de archivo

- **Streaming de Video/Audio**
  - Transmisión de cámara en tiempo real
  - Compartición de pantalla (placeholder)
  - Audio streaming (placeholder)
  - Calidad y FPS configurables
  - Múltiples espectadores por canal

- **Seguridad**
  - Encriptación de mensajes (Fernet)
  - Encriptación de archivos (AES-256)
  - Hash de archivos para verificación
  - Sistema de roles y permisos
  - Baneo de usuarios
  - Timeouts temporales

- **Interfaz Gráfica**
  - Interfaz moderna con CustomTkinter
  - Tema oscuro estilo Discord
  - Panel de servidores lateral
  - Panel de canales
  - Chat principal con burbujas de mensaje
  - Lista de miembros en línea
  - Ventanas modales para crear servidores/canales
  - Responsive design

## Arquitectura

El proyecto sigue una **Arquitectura Limpia (Clean Architecture)** con separación clara de responsabilidades:

```
src_Client_Server
│
├───Client
│   ├───data          # Almacenamiento de configuraciones
│   ├───models        # Modelos de datos (Pydantic)
│   ├───network       # Comunicación en red
│   ├───ui            # Interfaz gráfica
│   └───utils         # Utilidades
│
└───Server
    ├───data          # Almacenamiento de Base de datos
    ├───models        # Modelos de datos (Pydantic)
    ├───network       # Comunicación en red
    ├───repositories  # Acceso a datos (SQLite)
    ├───services      # Lógica de negocio
    └───utils         # Utilidades
```

### Patrones Implementados

- **Repository Pattern**: Abstracción del acceso a datos
- **Service Layer**: Lógica de negocio separada
- **Dependency Injection**: Inyección de dependencias
- **Factory Pattern**: Creación de repositorios
- **Observer Pattern**: Callbacks en servicios de red

## Instalación

1. **Clonar o descargar el proyecto**
```bash
cd Chat_GitHub
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

## Modos de Ejecución

La aplicación ahora soporta **tres modos** de ejecución independientes:


### 1. Modo Cliente Solo
Ejecuta solo la interfaz gráfica. Se conecta a un servidor externo (debe estar corriendo por separado).

```bash
python client_app.py client
```


### 2. Modo Servidor Solo
Ejecuta solo el servidor sin interfaz gráfica. Corre en consola y acepta conexiones de clientes.

```bash
python server_app.py --host 0.0.0.0 --port 5555
```


**Opciones del servidor:**
- `--host`: Dirección IP a escuchar (por defecto: 0.0.0.0 - todas las interfaces)
- `--port`: Puerto de escucha (por defecto: 5555)

**Ejemplos:**
```bash
# Servidor en localhost, puerto 5555
python server_app.py --host 127.0.0.1 --port 5555

# Servidor accesible desde red local, puerto 8080
python server_app.py --host 0.0.0.0 --port 8080
```

## Flujo de Trabajo Recomendado

1. **Inicia el servidor** (en una terminal):
```bash
python server_app.py --host 127.0.0.1 --port 5555
```

2. **Inicia el cliente** (en otra terminal):
```bash
python client_app.py
```

3. En la ventana de login del cliente:
   - El host ya estará preconfigurado como `127.0.0.1`
   - El puerto como `5555`
   - Inicia sesión con tu usuario

4. **¡Listo!** Ya puedes chatear, crear servidores, canales, etc.

## Uso

### Primer Inicio

1. Al ejecutar la aplicación, verás la ventana de login
2. Haz clic en "Crear Cuenta" para registrarte
3. Completa el formulario con:
   - Nombre de usuario (2-32 caracteres, solo letras/números/guiones)
   - Email válido
   - Contraseña (mínimo 8 caracteres)

### Crear un Servidor

1. Haz clic en el botón "+" en la barra lateral de servidores
2. Completa la configuración:
   - **Nombre**: Nombre del servidor
   - **Descripción**: Descripción opcional
   - **Icono**: URL de imagen (opcional)                        # No funcional todavia
   - **Tipo de conectividad**:
     - `client_server`: Cliente conecta a servidor central 
     - `p2p`: Conexión directa entre pares                      # No implementado todavia
     - `hybrid`: Combinación de ambos                           # No implementado todavia
   - **Nivel de seguridad**:
     - `none`: Sin encriptación
     - `basic`: Encriptación básica
     - `encrypted`: Encriptación completa
     - `e2e`: End-to-end encryption                             # No implementado todavia
   - **Máximo de miembros**: Límite de usuarios
   - **Transferencia de archivos**: Activar/desactivar          # No funcional todavia
   - **Video streaming**: Activar/desactivar                    # No funcional todavia
   - **Verificación requerida**: Aprobación manual para unirse  # No funcional todavia

3. Haz clic en "Crear Servidor"

### Crear Canales

1. Selecciona un servidor
2. Haz clic en "+ Crear Canal"
3. Configura:
   - **Nombre**: Nombre del canal
   - **Tipo**: Texto, Voz o Video
   - **Tema**: Descripción del canal
   - **Privado**: Si es privado, especifica roles permitidos
   - **Posición**: Orden en la lista

### Gestionar Roles # Medio implementado

1. En futuras versiones se añadirá UI para gestión de roles         
2. Por ahora, los roles se crean automáticamente:
   - `@everyone`: Rol por defecto para todos los miembros
   - `Admin`: Rol para el dueño del servidor

### Enviar Mensajes

1. Selecciona un canal de texto
2. Escribe tu mensaje en el campo inferior
3. Presiona Enter o clic en "Enviar"

### Invitaciones  # No funcional todavia

1. En futuras versiones se añadirá UI para generar invitaciones     
2. Los usuarios podrán unirse con un código de invitación

### Streaming de Video # No funcional todavia

1. Selecciona un canal de video
2. Haz clic en el botón de transmitir (se añadirá en UI)
3. Selecciona cámara o pantalla
4. Los demás miembros podrán ver la transmisión

### Transferencia de Archivos # No funcional todavia

1. En un canal de texto, arrastra un archivo o usa el botón de adjuntar
2. El archivo se subirá en chunks
3. Se notificará cuando esté completo
4. Los demás miembros podrán descargarlo

## Estructura de Archivos

        TODO Actualizar Estructura
```


Chat/
├── main.py              # Punto de entrada
├── requirements.txt     # Dependencias
├── config.py           # Configuración
├── src/
│   ├── app.py          # Aplicación principal
│   ├── models/         # Modelos de datos
│   ├── repositories/   # Repositorios SQLite
│   ├── services/       # Lógica de negocio
│   ├── network/        # Servicios de red
│   ├── ui/             # Interfaz gráfica
│   ├── utils/          # Utilidades
│   └── constants.py    # Constantes
├── data/               # Base de datos y archivos (se crea automáticamente)
│   ├── chat.db
│   ├── uploads/
│   ├── avatars/
│   └── banners/
└── logs/              # Logs de la aplicación (se crea automáticamente)
```

## Características Técnicas

### Base de Datos
- **SQLite** para almacenamiento local
- Tablas normalizadas con relaciones
- Transacciones seguras
- Backup automático

### Networking
- **TCP/IP** para comunicación
- **JSON** para serialización de mensajes
- **Threading** para operaciones concurrentes
- **P2P** y **Cliente-Servidor** soportados
- Callbacks para eventos

### Encriptación
- **Fernet** (AES-128) para mensajes
- **AES-256-CFB** para archivos grandes
- **PBKDF2** para derivación de claves
- **SHA-256** para verificación de integridad

### UI/UX
- **CustomTkinter** para interfaz moderna
- **Tema oscuro** por defecto
- **Responsive** a diferentes tamaños
- **Scroll** en paneles
- **Modales** para formularios

## Próximas Funcionalidades (TODO)

- [ ] Interfaz completa para gestión de roles
- [ ] Panel de configuración de servidor
- [ ] Búsqueda de usuarios/servidores
- [ ] Mensajes directos (DM)
- [ ] Notificaciones push
- [ ] Emojis personalizados
- [ ] Integración con APIs externas
- [ ] Sincronización en la nube
- [ ] Aplicación móvil
- [ ] Soporte para temas claros
- [ ] Traducciones múltiples
- [ ] Logs detallados de administrador
- [ ] Backup/restore automático
- [ ] Estadísticas de uso
- [ ] API REST para integraciones

## Desarrollo

### Estructura de Clean Code

1. **Models**: Entidades de datos con validación (Pydantic)
2. **Repositories**: Acceso a datos, una fuente por entidad
3. **Services**: Lógica de negocio, orquestación
4. **Network**: Comunicaciones, independiente de UI
5. **UI**: Solo presentación, sin lógica de negocio
6. **Utils**: Funciones auxiliares reutilizables

### Convenciones

- **Snake case** para funciones y variables
- **PascalCase** para clases
- **UPPER_SNAKE_CASE** para constantes
- Docstrings en todos los módulos y clases
- Type hints en todas las funciones
- Logging estructurado

### Testing  # No actualizado todavia a version actual

Para ejecutar pruebas (cuando estén implementadas):
```bash
pytest tests/
```

## Solución de Problemas

### Error: "No module named 'customtkinter'"
```bash
pip install customtkinter
```

### Error: Base de datos bloqueada
Cierra otras instancias de la aplicación. La base de datos SQLite solo permite una escritura a la vez.

### Error: Puerto en uso
Cambia el puerto en `config.py` o mata el proceso que usa el puerto 5555.

### Logs # No implementado todavia
Los logs se guardan en `logs/chat_YYYYMMDD.log`

## Licencia

Este proyecto es de código abierto para fines educativos.

## Autor

Desarrollado con ❤️ usando Python y CustomTkinter.

---

**Versión**: 0.0.1
**Fecha**: Marzo 2026
