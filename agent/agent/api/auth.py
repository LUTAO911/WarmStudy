"""
API Authentication - 身份验证与授权机制
线程安全版本，完整类型提示
"""
import time
import uuid
import hashlib
import threading
from functools import wraps
from typing import Optional, Dict, Any, List, Callable
from flask import request, jsonify


class AuthManager:
    _instance: Optional["AuthManager"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "AuthManager":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._lock: threading.RLock = threading.RLock()
        self._setup_default_keys()

    def _setup_default_keys(self) -> None:
        import os
        default_key = os.getenv("AGENT_API_KEY", "agent_dev_key_12345")
        self.register_api_key(
            api_key=default_key,
            name="Default Development Key",
            permissions=["chat", "rag", "tools", "skills", "admin"]
        )

    def register_api_key(
        self,
        api_key: str,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_in: Optional[int] = None
    ) -> str:
        key_hash = self._hash_key(api_key)

        with self._lock:
            self._api_keys[key_hash] = {
                "name": name,
                "permissions": permissions or ["chat"],
                "created_at": time.time(),
                "expires_at": time.time() + expires_in if expires_in else None
            }

        return key_hash

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not api_key:
            return None

        key_hash = self._hash_key(api_key)

        with self._lock:
            key_info = self._api_keys.get(key_hash)
            if not key_info:
                return None

            if key_info.get("expires_at"):
                if time.time() > key_info["expires_at"]:
                    return None

            return key_info.copy()

    def create_token(
        self,
        api_key: str,
        session_id: Optional[str] = None,
        expires_in: int = 3600
    ) -> Optional[str]:
        key_info = self.verify_api_key(api_key)
        if not key_info:
            return None

        token = uuid.uuid4().hex[:32]

        with self._lock:
            self._tokens[token] = {
                "api_key_hash": self._hash_key(api_key),
                "session_id": session_id,
                "created_at": time.time(),
                "expires_at": time.time() + expires_in,
                "permissions": key_info["permissions"]
            }

        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None

        with self._lock:
            token_info = self._tokens.get(token)
            if not token_info:
                return None

            if token_info.get("expires_at"):
                if time.time() > token_info["expires_at"]:
                    del self._tokens[token]
                    return None

            return token_info.copy()

    def revoke_token(self, token: str) -> bool:
        with self._lock:
            if token in self._tokens:
                del self._tokens[token]
                return True
            return False

    def list_api_keys(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": info["name"],
                    "permissions": info["permissions"],
                    "created_at": info["created_at"],
                    "expires_at": info.get("expires_at")
                }
                for info in self._api_keys.values()
            ]

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None


_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def require_auth(permission: Optional[str] = None) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any):
            auth_header = request.headers.get("Authorization", "")

            token: Optional[str] = None
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            else:
                token = request.args.get("token")

            if not token:
                api_key = request.headers.get("X-API-Key")
                if api_key:
                    auth_manager = get_auth_manager()
                    token_info = auth_manager.verify_api_key(api_key)
                    if token_info:
                        if permission and permission not in token_info.get("permissions", []):
                            return jsonify({"ok": False, "error": "Insufficient permissions"}), 403
                        return f(*args, **kwargs)

                return jsonify({"ok": False, "error": "Authentication required"}), 401

            auth_manager = get_auth_manager()
            token_info = auth_manager.verify_token(token)

            if not token_info:
                return jsonify({"ok": False, "error": "Invalid or expired token"}), 401

            if permission and permission not in token_info.get("permissions", []):
                return jsonify({"ok": False, "error": "Insufficient permissions"}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    auth_manager = get_auth_manager()
    return auth_manager.verify_token(token)