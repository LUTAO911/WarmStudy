"""
Unit tests for API authentication
"""
import time
import pytest
from typing import Dict, Any

from agent.api.auth import (
    AuthManager,
    require_auth,
    verify_token,
    get_auth_manager,
)


class TestAuthManager:
    """Tests for AuthManager."""

    def test_singleton_pattern(self) -> None:
        """Test that AuthManager is a singleton."""
        manager1 = AuthManager()
        manager2 = AuthManager()
        assert manager1 is manager2

    def test_register_api_key(self) -> None:
        """Test registering an API key."""
        manager = AuthManager()
        manager.reset_instance()

        key_hash = manager.register_api_key(
            api_key="test_key_123",
            name="Test Key",
            permissions=["chat", "rag"],
        )
        assert key_hash is not None

    def test_verify_api_key(self) -> None:
        """Test verifying an API key."""
        manager = AuthManager()
        manager.reset_instance()

        manager.register_api_key(
            api_key="my_secret_key",
            name="My Key",
            permissions=["chat"],
        )

        result = manager.verify_api_key("my_secret_key")
        assert result is not None
        assert result["name"] == "My Key"

    def test_verify_invalid_api_key(self) -> None:
        """Test verifying an invalid API key."""
        manager = AuthManager()
        manager.reset_instance()

        result = manager.verify_api_key("invalid_key")
        assert result is None

    def test_create_and_verify_token(self) -> None:
        """Test creating and verifying a token."""
        manager = AuthManager()
        manager.reset_instance()

        manager.register_api_key(
            api_key="key_for_token",
            name="Token Key",
            permissions=["chat"],
        )

        token = manager.create_token("key_for_token", session_id="session123")
        assert token is not None

        token_info = manager.verify_token(token)
        assert token_info is not None
        assert token_info["session_id"] == "session123"

    def test_verify_expired_token(self) -> None:
        """Test verifying an expired token."""
        manager = AuthManager()
        manager.reset_instance()

        manager.register_api_key(
            api_key="key_for_expiry",
            name="Expiry Key",
            permissions=["chat"],
        )

        token = manager.create_token(
            "key_for_expiry",
            session_id="session123",
            expires_in=1,
        )
        assert token is not None

        time.sleep(1.1)

        result = manager.verify_token(token)
        assert result is None

    def test_revoke_token(self) -> None:
        """Test revoking a token."""
        manager = AuthManager()
        manager.reset_instance()

        manager.register_api_key(
            api_key="key_for_revoke",
            name="Revoke Key",
            permissions=["chat"],
        )

        token = manager.create_token("key_for_revoke")
        assert manager.verify_token(token) is not None

        assert manager.revoke_token(token) is True
        assert manager.verify_token(token) is None

    def test_list_api_keys(self) -> None:
        """Test listing API keys."""
        manager = AuthManager()
        manager.reset_instance()

        manager.register_api_key(
            api_key="key1",
            name="Key 1",
            permissions=["chat"],
        )
        manager.register_api_key(
            api_key="key2",
            name="Key 2",
            permissions=["rag"],
        )

        keys = manager.list_api_keys()
        assert len(keys) >= 2


class TestGetAuthManager:
    """Tests for get_auth_manager function."""

    def test_returns_singleton(self) -> None:
        """Test that get_auth_manager returns singleton."""
        manager1 = get_auth_manager()
        manager2 = get_auth_manager()
        assert manager1 is manager2