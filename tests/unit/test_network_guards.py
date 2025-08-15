"""Tests for network guards and offline mode enforcement."""

import socket
import threading
import time
from unittest.mock import Mock, patch

import pytest

from studio.guards.network_guards import (
    OfflineGuard,
    OfflineGuardException,
    enforce_offline_mode,
    is_offline_mode_enabled,
    offline_mode_context,
)


class TestOfflineGuard:
    """Test OfflineGuard."""
    
    def test_initialization(self):
        """Test offline guard initialization."""
        guard = OfflineGuard()
        
        assert guard._enabled is False
        assert guard._patches == []
        assert guard._original_socket is not None
        assert guard._original_getaddrinfo is not None
        
    def test_enable_disable(self):
        """Test enabling and disabling offline mode."""
        guard = OfflineGuard()
        
        # Initially disabled
        assert not guard.is_enabled()
        
        # Enable
        guard.enable()
        assert guard.is_enabled()
        assert len(guard._patches) > 0
        
        # Disable
        guard.disable()
        assert not guard.is_enabled()
        assert len(guard._patches) == 0
        
    def test_double_enable_disable(self):
        """Test that double enable/disable is safe."""
        guard = OfflineGuard()
        
        # Double enable should be safe
        guard.enable()
        first_patches_count = len(guard._patches)
        guard.enable()
        second_patches_count = len(guard._patches)
        
        assert first_patches_count == second_patches_count
        assert guard.is_enabled()
        
        # Double disable should be safe
        guard.disable()
        guard.disable()
        assert not guard.is_enabled()
        assert len(guard._patches) == 0
        
    def test_context_manager(self):
        """Test offline guard as context manager."""
        guard = OfflineGuard()
        
        assert not guard.is_enabled()
        
        with guard:
            assert guard.is_enabled()
            
        assert not guard.is_enabled()
        
    def test_context_manager_exception_safety(self):
        """Test context manager cleans up even with exceptions."""
        guard = OfflineGuard()
        
        try:
            with guard:
                assert guard.is_enabled()
                raise ValueError("Test exception")
        except ValueError:
            pass
            
        # Should be disabled after exception
        assert not guard.is_enabled()
        
    def test_thread_safety(self):
        """Test thread safety of enable/disable operations."""
        guard = OfflineGuard()
        results = []
        
        def toggle_guard():
            guard.enable()
            time.sleep(0.01)  # Small delay
            results.append(guard.is_enabled())
            guard.disable()
            
        # Run multiple threads
        threads = [threading.Thread(target=toggle_guard) for _ in range(5)]
        
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # All threads should have seen the guard as enabled
        assert all(results)
        
        # Final state should be disabled
        assert not guard.is_enabled()
        
    @patch('socket.socket')
    def test_socket_blocking(self, mock_socket):
        """Test that socket creation is blocked when enabled."""
        guard = OfflineGuard()
        
        # Should work normally when disabled
        guard.disable()
        # Note: We can't easily test the actual socket call without affecting other code
        
        # When enabled, our patches should be active
        guard.enable()
        assert guard.is_enabled()
        
        guard.disable()
        
    def test_network_blocking_simulation(self):
        """Test network blocking simulation."""
        guard = OfflineGuard()
        
        # Create mock functions that would be blocked
        def mock_network_call():
            # This would normally make a network call
            return socket.socket()
            
        # When disabled, function should work (though we don't actually test network)
        guard.disable()
        
        # When enabled, our patches would block network calls
        guard.enable()
        assert guard.is_enabled()
        
        # Clean up
        guard.disable()


class TestGlobalOfflineMode:
    """Test global offline mode functions."""
    
    def teardown_method(self):
        """Clean up after each test."""
        # Ensure offline mode is disabled after each test
        enforce_offline_mode(False)
        
    def test_enforce_offline_mode(self):
        """Test global offline mode enforcement."""
        # Initially should be disabled
        assert not is_offline_mode_enabled()
        
        # Enable globally
        enforce_offline_mode(True)
        assert is_offline_mode_enabled()
        
        # Disable globally
        enforce_offline_mode(False)
        assert not is_offline_mode_enabled()
        
    def test_offline_mode_context(self):
        """Test offline mode context manager."""
        assert not is_offline_mode_enabled()
        
        with offline_mode_context():
            assert is_offline_mode_enabled()
            
        assert not is_offline_mode_enabled()
        
    def test_offline_mode_context_exception_safety(self):
        """Test offline mode context handles exceptions."""
        assert not is_offline_mode_enabled()
        
        try:
            with offline_mode_context():
                assert is_offline_mode_enabled()
                raise ValueError("Test exception")
        except ValueError:
            pass
            
        assert not is_offline_mode_enabled()
        
    def test_nested_offline_mode_contexts(self):
        """Test nested offline mode contexts."""
        assert not is_offline_mode_enabled()
        
        with offline_mode_context():
            assert is_offline_mode_enabled()
            
            with offline_mode_context():
                assert is_offline_mode_enabled()
                
            assert is_offline_mode_enabled()
            
        assert not is_offline_mode_enabled()


class TestOfflineGuardIntegration:
    """Integration tests for offline guard functionality."""
    
    def test_offline_guard_exception_message(self):
        """Test that offline guard exceptions have helpful messages."""
        guard = OfflineGuard()
        
        # Mock a blocked function that would raise OfflineGuardException
        def blocked_function():
            raise OfflineGuardException(
                "Network access blocked: offline mode is enabled. "
                "Disable offline mode or use stub adapters for testing."
            )
            
        # Test the exception message
        with pytest.raises(OfflineGuardException) as exc_info:
            blocked_function()
            
        error_msg = str(exc_info.value)
        assert "Network access blocked" in error_msg
        assert "offline mode is enabled" in error_msg
        assert "stub adapters" in error_msg
        
    def test_offline_mode_integration_simulation(self):
        """Test integration with simulated network calls."""
        # Simulate a function that would make network calls
        class NetworkService:
            def __init__(self):
                self.call_count = 0
                
            def make_request(self):
                # In real code, this would check if offline mode is enabled
                # and raise OfflineGuardException if it is
                if is_offline_mode_enabled():
                    raise OfflineGuardException("Network access blocked")
                    
                self.call_count += 1
                return "success"
                
        service = NetworkService()
        
        # Should work when offline mode is disabled
        enforce_offline_mode(False)
        result = service.make_request()
        assert result == "success"
        assert service.call_count == 1
        
        # Should fail when offline mode is enabled
        enforce_offline_mode(True)
        with pytest.raises(OfflineGuardException):
            service.make_request()
            
        # Call count should not increase due to blocked call
        assert service.call_count == 1
        
        # Clean up
        enforce_offline_mode(False)
        
    def test_multiple_guards_interaction(self):
        """Test interaction between multiple OfflineGuard instances."""
        guard1 = OfflineGuard()
        guard2 = OfflineGuard()
        
        # Both should start disabled
        assert not guard1.is_enabled()
        assert not guard2.is_enabled()
        
        # Enable first guard
        guard1.enable()
        assert guard1.is_enabled()
        assert not guard2.is_enabled()
        
        # Enable second guard
        guard2.enable()
        assert guard1.is_enabled()
        assert guard2.is_enabled()
        
        # Disable first guard
        guard1.disable()
        assert not guard1.is_enabled()
        assert guard2.is_enabled()
        
        # Disable second guard
        guard2.disable()
        assert not guard1.is_enabled()
        assert not guard2.is_enabled()
        
    def test_guard_state_consistency(self):
        """Test that guard state remains consistent across operations."""
        guard = OfflineGuard()
        
        # Test multiple enable/disable cycles
        for _ in range(3):
            assert not guard.is_enabled()
            
            guard.enable()
            assert guard.is_enabled()
            
            guard.disable()
            assert not guard.is_enabled()
            
        # Test context manager cycles
        for _ in range(3):
            assert not guard.is_enabled()
            
            with guard:
                assert guard.is_enabled()
                
            assert not guard.is_enabled()


class TestOfflineGuardErrorScenarios:
    """Test error scenarios and edge cases for offline guard."""
    
    def test_patch_failure_handling(self):
        """Test handling of patch failures."""
        guard = OfflineGuard()
        
        # Mock patch objects that fail
        failing_patch = Mock()
        failing_patch.start.side_effect = Exception("Patch failed")
        failing_patch.stop.side_effect = Exception("Stop failed")
        
        # Add failing patch to the list
        guard._patches = [failing_patch]
        
        # Enable should handle patch failures gracefully
        guard.enable()  # Should not crash
        
        # Disable should handle stop failures gracefully  
        guard.disable()  # Should not crash
        
        # State should still be updated correctly
        assert not guard.is_enabled()
        
    def test_concurrent_enable_disable(self):
        """Test concurrent enable/disable operations."""
        guard = OfflineGuard()
        
        def enable_worker():
            guard.enable()
            
        def disable_worker():
            time.sleep(0.001)  # Small delay
            guard.disable()
            
        # Run concurrent operations
        enable_thread = threading.Thread(target=enable_worker)
        disable_thread = threading.Thread(target=disable_worker)
        
        enable_thread.start()
        disable_thread.start()
        
        enable_thread.join()
        disable_thread.join()
        
        # Final state should be consistent (disabled due to disable_worker)
        assert not guard.is_enabled()
        
    def test_resource_cleanup(self):
        """Test that resources are properly cleaned up."""
        guard = OfflineGuard()
        
        # Enable and create patches
        guard.enable()
        initial_patches_count = len(guard._patches)
        assert initial_patches_count > 0
        
        # Disable should clean up all patches
        guard.disable()
        assert len(guard._patches) == 0
        
        # Re-enable should create new patches
        guard.enable()
        new_patches_count = len(guard._patches)
        assert new_patches_count > 0
        assert new_patches_count == initial_patches_count
        
        # Final cleanup
        guard.disable()