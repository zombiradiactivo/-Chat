"""
Documentación de API interna
"""

# API de Servicios

## AuthService
```python
class AuthService:
    def register(username: str, email: str, password: str) -> tuple[bool, Optional[str], Optional[User]]
    def login(identifier: str, password: str) -> tuple[bool, Optional[str], Optional[User]]
    def logout() -> None
    def get_current_user() -> Optional[User]
    def update_profile(user_id: str, **kwargs) -> tuple[bool, Optional[str], Optional[User]]
    def delete_account(user_id: str) -> bool
    def get_user_servers(user_id: str) -> List[Dict[str, Any]]
```

## ServerService
```python
class ServerService:
    def create_server(owner_id: str, **kwargs) -> tuple[bool, Optional[str], Optional[Server]]
    def update_server(server_id: str, user_id: str, **kwargs) -> tuple[bool, Optional[str], Optional[Server]]
    def delete_server(server_id: str, user_id: str) -> tuple[bool, Optional[str]]
    def get_server(server_id: str) -> Optional[Server]
    def get_user_servers(user_id: str) -> List[Server]
    def get_server_channels(server_id: str) -> List[Channel]
    def create_channel(server_id: str, creator_id: str, **kwargs) -> tuple[bool, Optional[str], Optional[Channel]]
    def delete_channel(channel_id: str, user_id: str) -> tuple[bool, Optional[str]]
    def create_role(server_id: str, creator_id: str, **kwargs) -> tuple[bool, Optional[str], Optional[Role]]
    def update_role(role_id: str, user_id: str, **kwargs) -> tuple[bool, Optional[str], Optional[Role]]
    def delete_role(role_id: str, user_id: str) -> tuple[bool, Optional[str]]
    def join_server(user_id: str, server_id: str) -> tuple[bool, Optional[str]]
    def leave_server(user_id: str, server_id: str) -> tuple[bool, Optional[str]]
    def get_server_members(server_id: str) -> List[Dict[str, Any]]
```

## MessageService
```python
class MessageService:
    def send_message(**kwargs) -> tuple[bool, Optional[str], Optional[Message]]
    def edit_message(message_id: str, user_id: str, content: str) -> tuple[bool, Optional[str], Optional[Message]]
    def delete_message(message_id: str, user_id: str, is_admin: bool = False) -> tuple[bool, Optional[str]]
    def get_channel_messages(channel_id: str, limit: int = 50, before: Optional[str] = None) -> List[Message]
    def get_message(message_id: str) -> Optional[Message]
    def add_reaction(message_id: str, user_id: str, emoji: str) -> tuple[bool, Optional[str]]
    def remove_reaction(message_id: str, user_id: str, emoji: str) -> tuple[bool, Optional[str]]
    def pin_message(message_id: str, user_id: str, server_id: str, has_permission: bool) -> tuple[bool, Optional[str]]
    def unpin_message(message_id: str, user_id: str, server_id: str, has_permission: bool) -> tuple[bool, Optional[str]]
    def get_pinned_messages(channel_id: str) -> List[Message]
```

## InviteService
```python
class InviteService:
    def create_invite(server_id: str, creator_id: str, max_uses: Optional[int] = None, 
                     expires_in_hours: Optional[int] = None, is_temporary: bool = False) -> tuple[bool, Optional[str], Optional[Invite]]
    def accept_invite(user_id: str, code: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]
    def revoke_invite(invite_id: str, user_id: str) -> tuple[bool, Optional[str]]
    def get_server_invites(server_id: str, user_id: str) -> List[Invite]
```

## PermissionService
```python
class PermissionService:
    def has_permission(user_id: str, server_id: str, permission: Permission, channel_id: Optional[str] = None) -> bool
    def get_user_permissions(user_id: str, server_id: str) -> Set[Permission]
    def get_highest_role_position(user_id: str, server_id: str) -> int
    def can_manage_role(user_id: str, server_id: str, target_role_id: str) -> bool
    def can_manage_channel(user_id: str, channel_id: str) -> bool
    def can_send_message(user_id: str, channel_id: str) -> bool
```

# API de Red

## TCPServer
```python
class TCPServer(NetworkService):
    def start() -> None
    def stop() -> None
    def send(target_id: str, message: NetworkMessage) -> bool
    def broadcast(message: NetworkMessage, exclude: Optional[List[str]] = None) -> None
    def is_connected() -> bool
    def get_connected_clients() -> List[str]
    def register_callback(event_type: str, callback: Callable) -> None
```

## TCPClient
```python
class TCPClient(NetworkService):
    def connect(host: str, port: int = 5555) -> bool
    def disconnect() -> None
    def send(message: NetworkMessage) -> bool
    def broadcast(message: NetworkMessage, exclude: Optional[List[str]] = None) -> None
    def is_connected() -> bool
    def register_callback(event_type: str, callback: Callable) -> None
    def start_processing() -> None
```

## NetworkMessage
```python
@dataclass
class NetworkMessage:
    type: str
    data: Dict[str, Any]
    sender_id: str
    timestamp: float = None
    
    def to_json() -> str
    @classmethod
    def from_json(json_str: str) -> NetworkMessage
```

# API de Repositorios

Todos los repositorios heredan de `CRUDRepository`:

```python
class CRUDRepository:
    def create(data: Dict[str, Any]) -> str
    def get_by_id(id: str) -> Optional[Dict[str, Any]]
    def get_all() -> List[Dict[str, Any]]
    def update(id: str, data: Dict[str, Any]) -> bool
    def delete(id: str) -> bool
```

Repositorios específicos:
- `UserRepository`: Usuarios
- `ServerRepository`: Servidores
- `ChannelRepository`: Canales
- `MessageRepository`: Mensajes
- `RoleRepository`: Roles
- `ServerMemberRepository`: Miembros de servidor
- `InviteRepository`: Invitaciones
- `FileTransferRepository`: Transferencias de archivos
