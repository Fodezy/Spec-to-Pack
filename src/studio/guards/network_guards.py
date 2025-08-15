"""Network security guards for offline mode enforcement."""

import socket
import urllib3


_offline_mode_enabled = False
_original_socket_create_connection = socket.create_connection
_original_urllib3_request = None


def enforce_offline_mode(enabled: bool) -> None:
    """Enable or disable offline mode network blocking.
    
    Args:
        enabled: If True, block all network access. If False, restore normal access.
    """
    global _offline_mode_enabled, _original_urllib3_request
    
    _offline_mode_enabled = enabled
    
    if enabled:
        # Block socket connections
        socket.create_connection = _blocked_create_connection
        
        # Block urllib3/requests
        if hasattr(urllib3.poolmanager, 'PoolManager'):
            if _original_urllib3_request is None:
                _original_urllib3_request = urllib3.poolmanager.PoolManager.request
            urllib3.poolmanager.PoolManager.request = _blocked_urllib3_request
    else:
        # Restore original functions
        socket.create_connection = _original_socket_create_connection
        if _original_urllib3_request is not None:
            urllib3.poolmanager.PoolManager.request = _original_urllib3_request


def _blocked_create_connection(*args, **kwargs):
    """Replacement for socket.create_connection that blocks all connections."""
    raise ConnectionError("Network access blocked: offline mode is enabled")


def _blocked_urllib3_request(self, *args, **kwargs):
    """Replacement for urllib3 request that blocks all HTTP requests."""
    raise ConnectionError("HTTP requests blocked: offline mode is enabled")


def is_offline_mode_enabled() -> bool:
    """Check if offline mode is currently enabled.
    
    Returns:
        True if offline mode is enabled, False otherwise
    """
    return _offline_mode_enabled


class NetworkGuard:
    """Context manager for temporarily enabling offline mode."""
    
    def __init__(self, enabled: bool = True):
        """Initialize network guard.
        
        Args:
            enabled: Whether to enable offline mode in context
        """
        self.enabled = enabled
        self.was_enabled = False
        
    def __enter__(self):
        """Enter context and enable offline mode if requested."""
        self.was_enabled = is_offline_mode_enabled()
        if self.enabled and not self.was_enabled:
            enforce_offline_mode(True)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous offline mode state."""
        if self.enabled and not self.was_enabled:
            enforce_offline_mode(False)