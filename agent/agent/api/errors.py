"""
API Error Handling - 统一错误处理
版本: v5.0
提供标准化的错误响应格式
"""
from flask import Blueprint, request, jsonify
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)

# ========== 错误码定义 ==========

class ErrorCode:
    """错误码常量"""
    # 通用错误 (1000-1999)
    INTERNAL_ERROR = ("INTERNAL_ERROR", 500, "An unexpected error occurred")
    VALIDATION_ERROR = ("VALIDATION_ERROR", 400, "Request validation failed")
    NOT_FOUND = ("NOT_FOUND", 404, "Resource not found")
    UNAUTHORIZED = ("UNAUTHORIZED", 401, "Authentication required")
    FORBIDDEN = ("FORBIDDEN", 403, "Access denied")
    RATE_LIMITED = ("RATE_LIMITED", 429, "Too many requests")
    SERVICE_UNAVAILABLE = ("SERVICE_UNAVAILABLE", 503, "Service temporarily unavailable")

    # Agent错误 (2000-2999)
    AGENT_INIT_FAILED = ("AGENT_INIT_FAILED", 500, "Failed to initialize agent")
    AGENT_TIMEOUT = ("AGENT_TIMEOUT", 504, "Agent response timeout")
    AGENT_NOT_FOUND = ("AGENT_NOT_FOUND", 404, "Agent not found")

    # RAG错误 (3000-3999)
    RAG_INIT_FAILED = ("RAG_INIT_FAILED", 500, "Failed to initialize RAG")
    RAG_RETRIEVE_FAILED = ("RAG_RETRIEVE_FAILED", 500, "RAG retrieval failed")
    RAG_EMPTY_RESULT = ("RAG_EMPTY_RESULT", 404, "No relevant documents found")

    # 心理学模块错误 (4000-4999)
    PSYCHOLOGY_INIT_FAILED = ("PSYCHOLOGY_INIT_FAILED", 500, "Failed to initialize psychology module")
    EMOTION_DETECT_FAILED = ("EMOTION_DETECT_FAILED", 500, "Emotion detection failed")
    CRISIS_DETECT_FAILED = ("CRISIS_DETECT_FAILED", 500, "Crisis detection failed")

    # 工具错误 (5000-5999)
    TOOL_NOT_FOUND = ("TOOL_NOT_FOUND", 404, "Tool not found")
    TOOL_EXEC_FAILED = ("TOOL_EXEC_FAILED", 500, "Tool execution failed")
    TOOL_TIMEOUT = ("TOOL_TIMEOUT", 504, "Tool execution timeout")

    # 知识库错误 (6000-6999)
    KB_INIT_FAILED = ("KB_INIT_FAILED", 500, "Failed to initialize knowledge base")
    KB_INGEST_FAILED = ("KB_INGEST_FAILED", 500, "Failed to ingest document")
    KB_QUERY_FAILED = ("KB_QUERY_FAILED", 500, "Knowledge base query failed")


# ========== AppError 异常类 ==========

class AppError(Exception):
    """应用异常基类"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.field = field
        self.request_id = None
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.field:
            result["field"] = self.field
        if self.details:
            result["details"] = self.details
        return result

    @classmethod
    def from_code(cls, error_code: tuple, message: Optional[str] = None, **kwargs) -> "AppError":
        """从错误码创建异常"""
        code, status_code, default_message = error_code
        return cls(
            code=code,
            message=message or default_message,
            status_code=status_code,
            **kwargs
        )


# ========== 便捷异常类 ==========

class ValidationError(AppError):
    """验证错误"""
    def __init__(self, field: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            field=field,
            details=details
        )


class NotFoundError(AppError):
    """资源不存在"""
    def __init__(self, resource: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="NOT_FOUND",
            message=f"Resource not found: {resource}",
            status_code=404,
            details=details
        )


class UnauthorizedError(AppError):
    """认证错误"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401
        )


class RateLimitError(AppError):
    """限流错误"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMITED",
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=429,
            details={"retry_after": retry_after}
        )


class ServiceUnavailableError(AppError):
    """服务不可用"""
    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=f"Service unavailable: {service}",
            status_code=503,
            details=details
        )


class AgentError(AppError):
    """Agent错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AGENT_INIT_FAILED",
            message=message,
            status_code=500,
            details=details
        )


class RAGError(AppError):
    """RAG错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RAG_RETRIEVE_FAILED",
            message=message,
            status_code=500,
            details=details
        )


# ========== 错误处理器 ==========

def _build_error_response(
    error: AppError,
    request_id: str,
    include_details: bool = True
) -> tuple:
    """构建错误响应"""
    response = {
        "status": "error",
        "error": error.to_dict(),
        "request_id": request_id
    }

    if include_details and error.details:
        response["error"]["details"] = error.details

    return jsonify(response), error.status_code


def _get_request_id() -> str:
    """获取或生成请求ID"""
    return request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])


# ========== 全局错误处理器注册 ==========

def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """处理AppError"""
        request_id = _get_request_id()

        logger.error(
            f"[{request_id}] AppError: {error.code} - {error.message}",
            extra={
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
                "details": error.details
            }
        )

        return _build_error_response(error, request_id)

    @app.errorhandler(400)
    def handle_bad_request(error):
        """处理400错误"""
        request_id = _get_request_id()

        return jsonify({
            "status": "error",
            "error": {
                "code": "BAD_REQUEST",
                "message": "Bad request"
            },
            "request_id": request_id
        }), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404错误"""
        request_id = _get_request_id()

        return jsonify({
            "status": "error",
            "error": {
                "code": "NOT_FOUND",
                "message": f"Endpoint not found: {request.path}"
            },
            "request_id": request_id
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理405错误"""
        request_id = _get_request_id()

        return jsonify({
            "status": "error",
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": f"Method not allowed: {request.method}"
            },
            "request_id": request_id
        }), 405

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """处理429错误"""
        request_id = _get_request_id()

        return jsonify({
            "status": "error",
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests"
            },
            "request_id": request_id
        }), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理500错误"""
        request_id = _get_request_id()

        logger.exception(f"[{request_id}] Internal server error")

        return jsonify({
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            },
            "request_id": request_id
        }), 500

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """处理未捕获的异常"""
        request_id = _get_request_id()

        logger.exception(f"[{request_id}] Unhandled exception: {error}")

        return jsonify({
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            },
            "request_id": request_id
        }), 500

    return app
