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
let messagesHasMore = false;
let loadingMoreMessages = false;

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
        case 'get_server_members_response':
            handleMembersResponse(message.data);
            break;
        case 'create_invite_response':
        case 'get_server_invites_response':
        case 'revoke_invite_response':
        case 'accept_invite_response':
            if (pendingResponse) {
                pendingResponse.resolve(message.data);
                pendingResponse = null;
            }
            break;
        case 'upload_file_response':
        case 'download_file_response':
            if (pendingResponse) {
                pendingResponse.resolve(message.data);
                pendingResponse = null;
            }
            break;
        case 'call_started':
        case 'call_user_joined':
        case 'call_user_left':
            console.log('Evento de llamada:', message.type, message.data);
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
    document.getElementById('channel-name').textContent = '# Selecciona un canal';
    document.getElementById('messages-container').innerHTML = '';

    // Habilitar botones
    const isOwner = currentUser && server.owner_id === currentUser.id;
    document.getElementById('settings-btn').disabled = !isOwner;
    document.getElementById('roles-btn').disabled = !isOwner;
    document.getElementById('create-channel-btn').disabled = false;
    document.getElementById('invite-btn').disabled = false;

    renderServerList();
    loadServerChannels();
    loadServerMembers();
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
    document.getElementById('channel-name').textContent = '# ' + channel.name;
    renderChannelList();
    loadChannelMessages();

    // Habilitar botones de llamada según tipo de canal
    const isVoice = channel.type === 'voice' || channel.type === 'video';
    const isVideo = channel.type === 'video';
    document.getElementById('voice-call-btn').disabled = !isVoice;
    document.getElementById('video-call-btn').disabled = !isVideo;
    document.getElementById('screen-share-btn').disabled = !isVoice;
}

// ==================== MENSAJES ====================

function loadChannelMessages() {
    if (!currentChannel) return;

    messages = [];
    messagesHasMore = false;
    loadingMoreMessages = false;
    document.getElementById('messages-container').innerHTML = '';

    sendTcpMessage('get_channel_messages', { channel_id: currentChannel.id, limit: 10 })
        .then(data => handleMessagesResponse(data))
        .catch(err => console.error('Error cargando mensajes:', err));
}

function handleMessagesResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        console.error('Error obteniendo mensajes');
        return;
    }

    const newMessages = data.messages || [];
    messagesHasMore = data.has_more || false;
    messages = newMessages;
    renderMessages();
}

function renderMessages() {
    const container = document.getElementById('messages-container');
    const wasAtTop = container.scrollTop <= 10;
    const previousHeight = container.scrollHeight;

    container.innerHTML = '';

    if (messagesHasMore) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'btn btn-sm btn-outline load-more-btn';
        loadMoreBtn.textContent = 'Cargar mensajes anteriores';
        loadMoreBtn.onclick = loadMoreMessages;
        container.appendChild(loadMoreBtn);
    }

    messages.forEach(msg => {
        container.appendChild(createMessageElement(msg));
    });

    if (wasAtTop && previousHeight > 0) {
        container.scrollTop = container.scrollHeight - previousHeight;
    } else {
        scrollToBottom();
    }
}

function loadMoreMessages() {
    if (!currentChannel || !messages.length || loadingMoreMessages) return;

    loadingMoreMessages = true;
    const oldestMessage = messages[0];
    const beforeId = oldestMessage.id;

    sendTcpMessage('get_channel_messages', {
        channel_id: currentChannel.id,
        limit: 10,
        before: beforeId
    })
        .then(data => {
            loadingMoreMessages = false;
            if (!data || !data.success) return;

            const olderMessages = data.messages || [];
            messagesHasMore = data.has_more || false;

            if (olderMessages.length > 0) {
                messages = [...olderMessages, ...messages];
                renderMessages();
            }
        })
        .catch(err => {
            loadingMoreMessages = false;
            console.error('Error cargando más mensajes:', err);
        });
}

function createMessageElement(msg) {
    const div = document.createElement('div');
    div.className = 'message';

    const isOwn = currentUser && msg.author_id === currentUser.id;
    if (isOwn) div.classList.add('own');

    const authorName = msg.author_id ? msg.author_id.substring(0, 8) : 'Desconocido';
    const initial = authorName.charAt(0).toUpperCase();
    const time = formatTime(msg.created_at);

    const messageType = msg.message_type || 'text';
    let contentHtml = '';

    if (messageType === 'file') {
        const attachments = msg.attachments || [];
        attachments.forEach(att => {
            const sizeText = att.file_size > 1024 * 1024
                ? (att.file_size / (1024 * 1024)).toFixed(1) + ' MB'
                : (att.file_size / 1024).toFixed(1) + ' KB';
            const downloadUrl = att.download_url || '';
            const filename = att.filename || 'archivo';
            contentHtml += `
                <div class="file-attachment">
                    <span class="file-icon">&#128206;</span>
                    <div class="file-info">
                        <span class="file-name">${escapeHtml(filename)}</span>
                        <span class="file-size">${sizeText}</span>
                    </div>
                    ${downloadUrl ? `<button class="btn btn-download" onclick="downloadFile('${escapeHtml(downloadUrl)}', '${escapeHtml(filename)}')">⬇ Descargar</button>` : ''}
                </div>`;
        });
    } else {
        contentHtml = `<div class="message-text">${escapeHtml(msg.content)}</div>`;
    }

    div.innerHTML = `
        <div class="message-avatar">${initial}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${time}</span>
            </div>
            ${contentHtml}
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
        name: name,
        type: type,
        creator_id: currentUser.id,
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

// ==================== MIEMBROS ====================

function loadServerMembers() {
    if (!currentServer) return;

    sendTcpMessage('get_server_members', { server_id: currentServer.id })
        .then(data => handleMembersResponse(data))
        .catch(err => console.error('Error cargando miembros:', err));
}

function handleMembersResponse(data) {
    resolveResponse(data);

    if (!data || !data.success) {
        console.error('Error obteniendo miembros');
        return;
    }

    const members = data.members || [];
    renderMembersList(members);
}

function renderMembersList(members) {
    const container = document.getElementById('members-list');
    container.innerHTML = '';

    if (members.length === 0) {
        container.innerHTML = '<div class="no-members">Sin miembros</div>';
        return;
    }

    members.forEach(memberInfo => {
        const user = memberInfo.user || {};
        const roles = memberInfo.roles || [];

        const div = document.createElement('div');
        div.className = 'member-item';

        const statusColor = {
            'online': '#43B581',
            'offline': '#747F8D',
            'idle': '#FAA61A',
            'dnd': '#F04747'
        }[user.status] || '#747F8D';

        const roleColor = roles.length > 0 ? (roles[0].color || '#99AAB5') : '#99AAB5';

        div.innerHTML = `
            <div class="member-avatar" style="background:${roleColor}">${(user.username || 'U').substring(0, 2).toUpperCase()}</div>
            <span class="member-name" style="color:${roleColor}">${escapeHtml(user.username || 'Usuario')}</span>
            <span class="member-status" style="background:${statusColor}"></span>
        `;
        container.appendChild(div);
    });
}

// ==================== INVITACIONES ====================

function showInviteModal() {
    if (!currentServer) return;
    loadInvites();
    openModal('invite-modal');
}

function loadInvites() {
    sendTcpMessage('get_server_invites', {
        server_id: currentServer.id,
        user_id: currentUser.id
    })
        .then(data => renderInvites(data))
        .catch(err => console.error('Error cargando invitaciones:', err));
}

function renderInvites(data) {
    const container = document.getElementById('invites-list');
    container.innerHTML = '';

    if (!data || !data.success) return;

    const invites = data.invites || [];

    if (invites.length === 0) {
        container.innerHTML = '<div class="no-invites">No hay invitaciones activas</div>';
        return;
    }

    invites.forEach(invite => {
        const div = document.createElement('div');
        div.className = 'invite-item';
        div.innerHTML = `
            <span class="invite-code">${invite.code}</span>
            <span class="invite-info">Usos: ${invite.uses || 0}/${invite.max_uses || '∞'}</span>
            <button class="btn btn-sm" onclick="copyInviteCode('${invite.code}')" title="Copiar">📋</button>
            <button class="btn btn-sm btn-danger" onclick="revokeInvite('${invite.id}')" title="Revocar">✕</button>
        `;
        container.appendChild(div);
    });
}

function createInvite() {
    const maxUses = document.getElementById('invite-max-uses').value || null;
    const expires = document.getElementById('invite-expires').value || null;

    sendTcpMessage('create_invite', {
        server_id: currentServer.id,
        user_id: currentUser.id,
        max_uses: maxUses ? parseInt(maxUses) : null,
        expires_in_hours: expires ? parseInt(expires) : null
    })
        .then(data => {
            if (data && data.success) {
                loadInvites();
                document.getElementById('invite-max-uses').value = '';
                document.getElementById('invite-expires').value = '';
            }
        })
        .catch(err => console.error('Error creando invitacion:', err));
}

function revokeInvite(inviteId) {
    sendTcpMessage('revoke_invite', {
        invite_id: inviteId,
        user_id: currentUser.id
    })
        .then(data => {
            if (data && data.success) loadInvites();
        })
        .catch(err => console.error('Error revocando invitacion:', err));
}

function copyInviteCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        alert('Codigo copiado: ' + code);
    });
}

function showJoinServer() {
    openModal('join-server-modal');
}

function acceptInvite() {
    const code = document.getElementById('invite-code').value.trim().toUpperCase();
    if (!code) return;

    sendTcpMessage('accept_invite', {
        user_id: currentUser.id,
        code: code
    })
        .then(data => {
            if (data && data.success) {
                closeModal('join-server-modal');
                document.getElementById('invite-code').value = '';
                loadUserServers();
            } else {
                alert('Error: ' + (data ? data.error : 'Codigo invalido'));
            }
        })
        .catch(err => console.error('Error aceptando invitacion:', err));
}

// ==================== ARCHIVOS ====================

function handleFileUpload(event) {
    if (!currentChannel || !currentUser) return;

    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
        alert('El archivo es demasiado grande (maximo 10MB)');
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        const base64 = e.target.result.split(',')[1];

        sendTcpMessage('upload_file', {
            file_data: base64,
            filename: file.name,
            channel_id: currentChannel.id,
            user_id: currentUser.id
        })
            .then(data => {
                if (!data || !data.success) {
                    alert('Error subiendo archivo: ' + (data ? data.error : 'Error'));
                }
            })
            .catch(err => console.error('Error subiendo archivo:', err));
    };
    reader.readAsDataURL(file);

    event.target.value = '';
}

function downloadFile(downloadUrl, filename) {
    sendTcpMessage('download_file', {
        download_url: downloadUrl,
        filename: filename,
        user_id: currentUser.id
    })
        .then(data => {
            if (data && data.success && data.file_data) {
                const byteChars = atob(data.file_data);
                const byteArray = new Uint8Array(byteChars.length);
                for (let i = 0; i < byteChars.length; i++) {
                    byteArray[i] = byteChars.charCodeAt(i);
                }
                const blob = new Blob([byteArray]);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } else {
                alert('Error descargando archivo: ' + (data ? data.error : 'Error'));
            }
        })
        .catch(err => console.error('Error descargando archivo:', err));
}

// ==================== LLAMADAS ====================

function startVoiceCall() {
    if (!currentChannel || !currentUser) return;
    sendTcpMessage('start_call', {
        channel_id: currentChannel.id,
        user_id: currentUser.id,
        call_type: 'voice'
    });
    document.getElementById('end-call-btn').style.display = 'inline-block';
    document.getElementById('voice-call-btn').disabled = true;
    document.getElementById('video-call-btn').disabled = true;
}

function startVideoCall() {
    if (!currentChannel || !currentUser) return;
    sendTcpMessage('start_call', {
        channel_id: currentChannel.id,
        user_id: currentUser.id,
        call_type: 'video'
    });
    sendTcpMessage('join_call', {
        channel_id: currentChannel.id,
        user_id: currentUser.id
    });
    document.getElementById('end-call-btn').style.display = 'inline-block';
    document.getElementById('voice-call-btn').disabled = true;
    document.getElementById('video-call-btn').disabled = true;
}

function startScreenShare() {
    if (!currentChannel || !currentUser) return;
    sendTcpMessage('screen_share_start', {
        channel_id: currentChannel.id,
        user_id: currentUser.id
    });
    document.getElementById('end-call-btn').style.display = 'inline-block';
    document.getElementById('screen-share-btn').disabled = true;
}

function endCall() {
    if (!currentChannel || !currentUser) return;
    sendTcpMessage('leave_call', {
        channel_id: currentChannel.id,
        user_id: currentUser.id
    });
    document.getElementById('end-call-btn').style.display = 'none';
    document.getElementById('voice-call-btn').disabled = false;
    document.getElementById('video-call-btn').disabled = false;
    document.getElementById('screen-share-btn').disabled = false;
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
