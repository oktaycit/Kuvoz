"""HTTP and Socket.IO route registration package."""

from .http_routes import register_http_routes
from .monitoring_routes import register_monitoring_routes
from .socket_routes import register_basic_socket_routes
from .socket_settings_routes import register_settings_socket_routes
from .socket_system_routes import register_system_socket_routes
from .socket_tailscale_routes import register_tailscale_socket_routes
from .socket_wifi_routes import register_wifi_socket_routes

__all__ = [
    'register_basic_socket_routes',
    'register_http_routes',
    'register_monitoring_routes',
    'register_settings_socket_routes',
    'register_system_socket_routes',
    'register_tailscale_socket_routes',
    'register_wifi_socket_routes',
]
