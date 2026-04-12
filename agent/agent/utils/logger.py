"""
Logger - 日志记录系统
线程安全版本，完整类型提示
"""
import time
import json
import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AgentLogger:
    _instance: Optional["AgentLogger"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentLogger":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger("AgentLogger")
        self.logger.setLevel(logging.DEBUG)
        self._lock = threading.RLock()

        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        self._log_file: Path = Path("data/agent/logs/agent.log")
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

        self._request_log_file: Path = Path("data/agent/logs/requests.jsonl")
        self._request_log_file.parent.mkdir(parents=True, exist_ok=True)

    def debug(self, message: str, **kwargs: Any) -> None:
        with self._lock:
            self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        with self._lock:
            self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        with self._lock:
            self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        with self._lock:
            self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        with self._lock:
            self.logger.critical(message, extra=kwargs)

    def log_request(
        self,
        session_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "message": message,
            "response": response[:500] if len(response) > 500 else response,
            "metadata": metadata or {}
        }

        try:
            with self._lock:
                with open(self._request_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except (OSError, IOError):
            pass

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }

        with self._lock:
            self.logger.error(f"{error_type}: {error_message}", extra=context)

        error_log_file: Path = Path(f"data/agent/logs/errors_{datetime.now().strftime('%Y%m%d')}.jsonl")
        error_log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self._lock:
                with open(error_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except (OSError, IOError):
            pass

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._request_log_file.exists():
            return []

        logs: List[Dict[str, Any]] = []
        try:
            with self._lock:
                with open(self._request_log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            logs.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except (OSError, IOError):
            return []

        return logs[-limit:]

    def get_error_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        error_file: Path = Path(f"data/agent/logs/errors_{datetime.now().strftime('%Y%m%d')}.jsonl")
        if not error_file.exists():
            return []

        errors: List[Dict[str, Any]] = []
        try:
            with self._lock:
                with open(error_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            errors.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except (OSError, IOError):
            return []

        return errors[-limit:]


class RequestLogger:
    def __init__(self) -> None:
        self.logger: AgentLogger = AgentLogger()

    def log(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        execution_time: float,
        tools_used: Optional[List[str]] = None,
        skills_used: Optional[List[str]] = None,
        context_used: bool = False,
        error: Optional[str] = None
    ) -> None:
        metadata: Dict[str, Any] = {
            "execution_time": round(execution_time, 3),
            "tools_used": tools_used or [],
            "skills_used": skills_used or [],
            "context_used": context_used,
            "response_length": len(assistant_response)
        }

        if error:
            self.logger.log_error(
                error_type="RequestError",
                error_message=error,
                context=metadata
            )
        else:
            self.logger.log_request(
                session_id=session_id,
                message=user_message,
                response=assistant_response,
                metadata=metadata
            )