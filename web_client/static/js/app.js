// Chat App Web Client
const socket = io();

// Estado de la aplicacion
let currentUser = null;
let currentServer = null;
let currentChannel = null;
let servers = [];
let channels = [];
let messages = [];
let isTcpConnected = false;

// Promesas para respuestas del servidor
let pendingResponse = null;
let responseTimeout = null;

// ==================== CONEXION SOCKET ====================

socket.on('connect', () => {
    console.log('WebSocket conectado');
});

socket.on('disconnect', () => {
    console.log('WebSocket desconectado');
    isTcpConnected = false;
});

socket.on('tcp_connected', (data) => {
    if (data.success) {
        isTcpConnected = true;
        console.log('Conectado al servidor TCP');
    } else {
        showError('login-error', data.error || 'Error de conexion');
    }
});

socket.on('server_message', (message) => {
    console.log('Mensaje del servidor:', message);
    handleServerMessage(message);
});

socket.on('disconnected', () => {
    isTcpConnected = false;
    console.log('Desconectado del servidor TCP');
});

// ==================== MANEJO DE MENSAJES ====================

function handleServerMessage(message) {
    switch (message.type) {
        case 'login_response':
            handleLoginResponse(message.data);
            break;
        case 'register_response':
            handleRegisterResponse(message.data);
            break;
        case 'get_user_servers_response':
            handleServersResponse(message.data);
            break;
        case 'get_server_channels_response':
            handleChannelsResponse(message.data);
            break;
        case 'get_channel_messages_response':
            handleMessagesResponse(message.data);
            break;
        case 'send_message_response':
            handleSendMessageResponse(message.data);
            break;
        case 'create_server_response':
            handleCreateServerResponse(message.data);
            break;
        case 'create_channel_response':
            handleCreateChannelResponse(message.data);
            break;
        case 'get_roles_response':
            handleRolesResponse(message.data);
            break;
        case 'create_role_response':
            handleCreateRoleResponse(message.data);
            break;
        case 'delete_role_response':
            handleDeleteRoleResponse(message.data);
            break;
        case 'message_broadcast':
            handleBroadcast(message.data);
            break;
        case 'check_permission_response':
            break;
        default:
            console.log('Tipo de mensaje no manejado:', message.type);
    }
}

function sendTcpMessage(type, data) {
    return new Promise((resolve, reject) => {
        const message = {
            type: type,
            data: data,
            sender_id: currentUser ? currentUser.id : 'web_client',
            timestamp: Date.now() / 1000
        };

        if (responseTimeout) {
            clearTimeout(responseTimeout);
        }

        pendingResponse = { resolve, reject };

        socket.emit('tcp_send', message);

        responseTimeout = setTimeout(() => {
            if (pendingResponse) {
                pendingResponse.reject(new Error('Timeout'));
                pendingResponse = null;
            }
        }, 5000);
    });
}

function resolveResponse(data) {
    if (responseTimeout) {
        clearTimeout(responseTimeout);
        responseTimeout = null;
    }
    if (pendingResponse) {
        pendingResponse.resolve(data);
        pendingResponse = null;
    }
}

// ==================== UI HELPERS ====================

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showLogin() {
    showScreen('login-screen');
}

function showRegister() {
    showScreen('register-screen');
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = message;
}

function showSuccess(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = message;
}

function clearErrors() {
    document.querySelectorAll('.error-msg, .success-msg').forEach(el => el.textContent = '');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// ==================== LOGIN ====================

function handleLogin() {
    clearErrors();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const host = document.getElementById('login-host').value.trim() || '127.0.0.1';
    const port = document.getElementById('login-port').value || '5555';

    if (!email || !password) {
        showError('login-error', 'Completa usuario y contrasena');
        return;
    }

    // Conectar al servidor TCP primero
    socket.emit('tcp_connect', { host, port });

    // Esperar un poco y luego enviar login
    setTimeout(() => {
        if (!isTcpConnected) {
            showError('login-error', 'No se pudo conectar al servidor');
            return;
        }

        sendTcpMessage('login', { email, password })
            .then(data => handleLoginResponse(data))
            .catch(err => {
                showError('login-error', 'Error de conexion');
            });
    }, 500);
}

function handleLoginResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        const error = data ? data.error : 'Error desconocido';
        showError('login-error', 'Error de login: ' + error);
        return;
    }

    currentUser = data.user;
    console.log('Usuario autenticado:', currentUser);

    // Guardar usuario recordado
    if (document.getElementById('remember-me').checked) {
        localStorage.setItem('lastUsername', document.getElementById('login-email').value);
    }

    showScreen('chat-screen');
    loadUserServers();
}

// ==================== REGISTRO ====================

function handleRegister() {
    clearErrors();
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;

    if (!username || !email || !password) {
        showError('register-error', 'Completa todos los campos');
        return;
    }

    sendTcpMessage('register', { username, email, password })
        .then(data => handleRegisterResponse(data))
        .catch(err => {
            showError('register-error', 'Error de conexion');
        });
}

function handleRegisterResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        const error = data ? data.error : 'Error desconocido';
        showError('register-error', 'Error de registro: ' + error);
        return;
    }

    showSuccess('register-success', 'Cuenta creada exitosamente!');
    setTimeout(() => showLogin(), 1500);
}

// ==================== SERVIDORES ====================

function loadUserServers() {
    if (!currentUser) return;

    sendTcpMessage('get_user_servers', { user_id: currentUser.id })
        .then(data => handleServersResponse(data))
        .catch(err => console.error('Error cargando servidores:', err));
}

function handleServersResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        console.error('Error obteniendo servidores');
        return;
    }

    servers = data.servers || [];
    renderServerList();
}

function renderServerList() {
    const container = document.getElementById('server-list');
    container.innerHTML = '<button class="server-add-btn" onclick="showCreateServer()" title="Crear Servidor">+</button>';

    servers.forEach(server => {
        const btn = document.createElement('button');
        btn.className = 'server-btn';
        btn.textContent = server.name.charAt(0).toUpperCase();
        btn.title = server.name;
        btn.onclick = () => selectServer(server);

        if (currentServer && currentServer.id === server.id) {
            btn.classList.add('active');
        }

        container.appendChild(btn);
    });
}

function selectServer(server) {
    currentServer = server;
    currentChannel = null;
    document.getElementById('server-name').textContent = server.name;
    document.getElementById('channel-name').textContent = 'Selecciona un canal';
    document.getElementById('messages-container').innerHTML = '';

    // Habilitar botones
    const isOwner = currentUser && server.owner_id === currentUser.id;
    document.getElementById('settings-btn').disabled = !isOwner;
    document.getElementById('roles-btn').disabled = !isOwner;
    document.getElementById('create-channel-btn').disabled = false;

    renderServerList();
    loadServerChannels();
}

// ==================== CANALES ====================

function loadServerChannels() {
    if (!currentServer) return;

    sendTcpMessage('get_server_channels', { server_id: currentServer.id })
        .then(data => handleChannelsResponse(data))
        .catch(err => console.error('Error cargando canales:', err));
}

function handleChannelsResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        console.error('Error obteniendo canales');
        return;
    }

    channels = data.channels || [];
    renderChannelList();
}

function renderChannelList() {
    const container = document.getElementById('channel-list');
    container.innerHTML = '<button class="btn btn-sm btn-outline" onclick="showCreateChannel()" id="create-channel-btn">+ Crear Canal</button>';

    const textChannels = channels.filter(c => c.type === 'text');
    const voiceChannels = channels.filter(c => c.type === 'voice');

    if (textChannels.length > 0) {
        const title = document.createElement('div');
        title.className = 'channel-section-title';
        title.textContent = 'CANALES DE TEXTO';
        container.appendChild(title);

        textChannels.forEach(channel => {
            container.appendChild(createChannelItem(channel));
        });
    }

    if (voiceChannels.length > 0) {
        const title = document.createElement('div');
        title.className = 'channel-section-title';
        title.textContent = 'CANALES DE VOZ';
        container.appendChild(title);

        voiceChannels.forEach(channel => {
            container.appendChild(createChannelItem(channel));
        });
    }
}

function createChannelItem(channel) {
    const btn = document.createElement('button');
    btn.className = 'channel-item';
    if (currentChannel && currentChannel.id === channel.id) {
        btn.classList.add('active');
    }

    const icon = channel.type === 'voice' ? '&#127908;' : '#';
    btn.innerHTML = `<span class="channel-icon">${icon}</span> ${channel.name}`;
    btn.onclick = () => selectChannel(channel);

    return btn;
}

function selectChannel(channel) {
    currentChannel = channel;
    document.getElementById('channel-name').textContent = channel.name;
    renderChannelList();
    loadChannelMessages();
}

// ==================== MENSAJES ====================

function loadChannelMessages() {
    if (!currentChannel) return;

    sendTcpMessage('get_channel_messages', { channel_id: currentChannel.id })
        .then(data => handleMessagesResponse(data))
        .catch(err => console.error('Error cargando mensajes:', err));
}

function handleMessagesResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        console.error('Error obteniendo mensajes');
        return;
    }

    messages = data.messages || [];
    renderMessages();
}

function renderMessages() {
    const container = document.getElementById('messages-container');
    container.innerHTML = '';

    messages.forEach(msg => {
        container.appendChild(createMessageElement(msg));
    });

    scrollToBottom();
}

function createMessageElement(msg) {
    const div = document.createElement('div');
    div.className = 'message';

    const isOwn = currentUser && msg.author_id === currentUser.id;
    if (isOwn) div.classList.add('own');

    const authorName = msg.author_id ? msg.author_id.substring(0, 8) : 'Desconocido';
    const initial = authorName.charAt(0).toUpperCase();
    const time = formatTime(msg.created_at);

    div.innerHTML = `
        <div class="message-avatar">${initial}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-text">${escapeHtml(msg.content)}</div>
        </div>
    `;

    return div;
}

function sendMessage() {
    if (!currentChannel || !currentUser) return;

    const input = document.getElementById('message-input');
    const content = input.value.trim();
    if (!content) return;

    sendTcpMessage('send_message', {
        content: content,
        channel_id: currentChannel.id,
        author_id: currentUser.id
    })
        .then(data => {
            if (data && data.success && data.message) {
                messages.push(data.message);
                addMessageToUI(data.message);
            }
        })
        .catch(err => console.error('Error enviando mensaje:', err));

    input.value = '';
}

function addMessageToUI(msg) {
    const container = document.getElementById('messages-container');
    container.appendChild(createMessageElement(msg));
    scrollToBottom();
}

function handleSendMessageResponse(data) {
    resolveResponse(data);
}

function handleBroadcast(data) {
    if (!currentChannel || !currentUser) return;

    if (data.channel_id === currentChannel.id) {
        if (data.message) {
            messages.push(data.message);
            addMessageToUI(data.message);
        }
    }
}

function handleMessageKeypress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// ==================== CREAR SERVIDOR ====================

function showCreateServer() {
    openModal('create-server-modal');
}

function createServer() {
    const name = document.getElementById('new-server-name').value.trim();
    const description = document.getElementById('new-server-description').value.trim();

    if (!name) {
        alert('Ingresa un nombre para el servidor');
        return;
    }

    sendTcpMessage('create_server', {
        user_id: currentUser.id,
        name: name,
        description: description
    })
        .then(data => handleCreateServerResponse(data))
        .catch(err => console.error('Error creando servidor:', err));

    closeModal('create-server-modal');
    document.getElementById('new-server-name').value = '';
    document.getElementById('new-server-description').value = '';
}

function handleCreateServerResponse(data) {
    resolveResponse(data);

    if (data && data.success) {
        loadUserServers();
    } else {
        alert('Error creando servidor: ' + (data ? data.error : 'Error desconocido'));
    }
}

// ==================== CREAR CANAL ====================

function showCreateChannel() {
    if (!currentServer) return;
    openModal('create-channel-modal');
}

function createChannel() {
    const name = document.getElementById('new-channel-name').value.trim();
    const type = document.getElementById('new-channel-type').value;

    if (!name) {
        alert('Ingresa un nombre para el canal');
        return;
    }

    sendTcpMessage('create_channel', {
        server_id: currentServer.id,
        channel_name: name,
        channel_type: type,
        user_id: currentUser.id
    })
        .then(data => handleCreateChannelResponse(data))
        .catch(err => console.error('Error creando canal:', err));

    closeModal('create-channel-modal');
    document.getElementById('new-channel-name').value = '';
}

function handleCreateChannelResponse(data) {
    resolveResponse(data);

    if (data && data.success) {
        loadServerChannels();
    } else {
        alert('Error creando canal: ' + (data ? data.error : 'Error desconocido'));
    }
}

// ==================== CONFIGURACION SERVIDOR ====================

function showServerSettings() {
    if (!currentServer) return;

    document.getElementById('settings-server-name').value = currentServer.name || '';
    document.getElementById('settings-server-desc').value = currentServer.description || '';
    openModal('server-settings-modal');
}

function saveServerSettings() {
    const name = document.getElementById('settings-server-name').value.trim();
    const description = document.getElementById('settings-server-desc').value.trim();

    if (!name) {
        alert('El nombre es obligatorio');
        return;
    }

    sendTcpMessage('update_server', {
        server_id: currentServer.id,
        user_id: currentUser.id,
        name: name,
        description: description
    })
        .then(data => {
            if (data && data.success) {
                currentServer = data.server;
                document.getElementById('server-name').textContent = currentServer.name;
                loadUserServers();
            }
        })
        .catch(err => console.error('Error actualizando servidor:', err));

    closeModal('server-settings-modal');
}

// ==================== ROLES ====================

function showManageRoles() {
    if (!currentServer) return;
    loadRoles();
    openModal('manage-roles-modal');
}

function loadRoles() {
    sendTcpMessage('get_server_roles', { server_id: currentServer.id })
        .then(data => handleRolesResponse(data))
        .catch(err => console.error('Error cargando roles:', err));
}

function handleRolesResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        console.error('Error obteniendo roles');
        return;
    }

    const roles = data.roles || [];
    renderRolesList(roles);
}

function renderRolesList(roles) {
    const container = document.getElementById('roles-list');
    container.innerHTML = '';

    roles.forEach(role => {
        const div = document.createElement('div');
        div.className = 'role-item';
        div.innerHTML = `
            <div class="role-color" style="background: ${role.color || '#99AAB5'}"></div>
            <span class="role-name">${escapeHtml(role.name)}</span>
            <button class="role-delete" onclick="deleteRole('${role.id}')" title="Eliminar">&#10005;</button>
        `;
        container.appendChild(div);
    });
}

function createRole() {
    const name = document.getElementById('new-role-name').value.trim();
    const color = document.getElementById('new-role-color').value;

    if (!name) {
        alert('Ingresa un nombre para el rol');
        return;
    }

    sendTcpMessage('create_role', {
        server_id: currentServer.id,
        user_id: currentUser.id,
        name: name,
        color: color
    })
        .then(data => handleCreateRoleResponse(data))
        .catch(err => console.error('Error creando rol:', err));

    document.getElementById('new-role-name').value = '';
}

function handleCreateRoleResponse(data) {
    resolveResponse(data);

    if (data && data.success) {
        loadRoles();
    } else {
        alert('Error creando rol: ' + (data ? data.error : 'Error desconocido'));
    }
}

function deleteRole(roleId) {
    if (!confirm('Seguro que deseas eliminar este rol?')) return;

    sendTcpMessage('delete_role', {
        role_id: roleId,
        server_id: currentServer.id,
        user_id: currentUser.id
    })
        .then(data => handleDeleteRoleResponse(data))
        .catch(err => console.error('Error eliminando rol:', err));
}

function handleDeleteRoleResponse(data) {
    resolveResponse(data);

    if (data && data.success) {
        loadRoles();
    } else {
        alert('Error eliminando rol: ' + (data ? data.error : 'Error desconocido'));
    }
}

// ==================== UTILIDADES ====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
}

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    container.scrollTop = container.scrollHeight;
}

// ==================== INICIALIZACION ====================

document.addEventListener('DOMContentLoaded', () => {
    // Cargar usuario recordado
    const lastUsername = localStorage.getItem('lastUsername');
    if (lastUsername) {
        document.getElementById('login-email').value = lastUsername;
        document.getElementById('remember-me').checked = true;
    }

    // Focus en el campo de email
    document.getElementById('login-email').focus();
});
