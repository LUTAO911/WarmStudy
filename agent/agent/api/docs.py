"""
OpenAPI Documentation - API接口文档
暖学帮 Agent API v5.0

访问地址: /api/docs
"""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "暖学帮 Agent API",
        "description": """
## 暖学帮 - 青少年心理关怀AI系统

### 主要功能
- **智能对话**: 支持多种对话模式（普通聊天、心理陪伴、教育辅导、危机干预）
- **情绪识别**: 实时检测用户情绪状态
- **危机检测**: 识别自杀/自伤等危机信号
- **知识库检索**: RAG增强的知识问答
- **工具调用**: 支持计算器、时间查询等工具

### 对话模式
| 模式 | 说明 | 触发条件 |
|------|------|---------|
| `chat` | 普通聊天 | 默认模式 |
| `psychology` | 心理陪伴 | 检测到心理学关键词 |
| `education` | 教育辅导 | 检测到学习相关关键词 |
| `crisis` | 危机干预 | 检测到危机关键词 |

### 认证方式
使用 `X-API-Key` 头进行认证。

### 错误码
| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | VALIDATION_ERROR | 请求参数错误 |
| 401 | UNAUTHORIZED | 未认证 |
| 404 | NOT_FOUND | 资源不存在 |
| 429 | RATE_LIMITED | 请求过于频繁 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
        """,
        "version": "5.0.0",
        "contact": {
            "name": "暖学帮技术支持",
            "email": "support@nuanxuebang.com"
        }
    },
    "servers": [
        {
            "url": "http://localhost:5177",
            "description": "本地开发环境"
        }
    ],
    "tags": [
        {
            "name": "v5 - 对话",
            "description": "基于Orchestrator的v5对话接口"
        },
        {
            "name": "v5 - 心理学",
            "description": "情绪识别与危机检测"
        },
        {
            "name": "v5 - 系统",
            "description": "系统状态与上下文管理"
        },
        {
            "name": "v1 - 原有接口",
            "description": "保持向后兼容的原有API"
        }
    ],
    "paths": {
        # ========== v5 Chat ==========
        "/api/v5/chat": {
            "post": {
                "tags": ["v5 - 对话"],
                "summary": "对话接口 (v5)",
                "description": "使用新的Orchestrator处理对话请求，支持多种对话模式",
                "operationId": "chat_v5",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ChatRequest"
                            },
                            "example": {
                                "message": "最近学习压力好大，晚上都睡不好觉",
                                "session_id": "sess_abc123",
                                "user_type": "student",
                                "use_rag": True,
                                "use_tools": True
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "对话成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ChatResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "参数错误",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "服务器错误",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        },

        # ========== v5 Intent ==========
        "/api/v5/intent/route": {
            "post": {
                "tags": ["v5 - 对话"],
                "summary": "意图路由",
                "description": "智能判断用户意图，返回对话模式建议",
                "operationId": "route_intent",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "用户消息",
                                        "example": "最近学习压力好大"
                                    },
                                    "session_id": {
                                        "type": "string",
                                        "description": "会话ID"
                                    },
                                    "user_type": {
                                        "type": "string",
                                        "enum": ["student", "parent", "teacher"],
                                        "default": "student"
                                    }
                                },
                                "required": ["message"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "路由成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "data": {
                                            "type": "object",
                                            "properties": {
                                                "primary_intent": {"type": "string"},
                                                "confidence": {"type": "number"},
                                                "mode": {"type": "string"},
                                                "reasoning": {"type": "string"}
                                            }
                                        },
                                        "request_id": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },

        # ========== v5 Emotion ==========
        "/api/v5/emotion/detect": {
            "post": {
                "tags": ["v5 - 心理学"],
                "summary": "情绪检测",
                "description": "检测用户情绪状态，返回情绪类型、强度和建议",
                "operationId": "detect_emotion",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/EmotionCheckRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "检测成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/EmotionResponse"
                                }
                            }
                        }
                    }
                }
            }
        },

        # ========== v5 Crisis ==========
        "/api/v5/crisis/check": {
            "post": {
                "tags": ["v5 - 心理学"],
                "summary": "危机检测",
                "description": "检测自杀/自伤等危机信号，返回危机等级和干预建议",
                "operationId": "check_crisis",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CrisisCheckRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "检测成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/CrisisResponse"
                                }
                            }
                        }
                    }
                }
            }
        },

        # ========== v5 Status ==========
        "/api/v5/status": {
            "get": {
                "tags": ["v5 - 系统"],
                "summary": "v5架构状态",
                "description": "获取v5架构各组件状态",
                "operationId": "v5_status",
                "responses": {
                    "200": {
                        "description": "状态获取成功"
                    }
                }
            }
        },

        # ========== v5 Context Stats ==========
        "/api/v5/context/lifecycle/stats": {
            "get": {
                "tags": ["v5 - 系统"],
                "summary": "上下文生命周期统计",
                "description": "获取当前上下文的使用统计",
                "operationId": "context_stats",
                "responses": {
                    "200": {
                        "description": "统计获取成功"
                    }
                }
            }
        },

        # ========== 原有API ==========
        "/api/agent/chat": {
            "post": {
                "tags": ["v1 - 原有接口"],
                "summary": "对话接口 (v1)",
                "description": "原有的Agent对话接口，保持向后兼容",
                "operationId": "chat_v1",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"},
                                    "session_id": {"type": "string"},
                                    "use_rag": {"type": "boolean"},
                                    "use_tools": {"type": "boolean"},
                                    "use_skills": {"type": "boolean"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "对话成功"
                    }
                }
            }
        },
        "/api/status": {
            "get": {
                "tags": ["v1 - 原有接口"],
                "summary": "系统状态",
                "description": "获取系统整体状态",
                "operationId": "status_v1",
                "responses": {
                    "200": {
                        "description": "状态获取成功"
                    }
                }
            }
        },
        "/api/search": {
            "get": {
                "tags": ["v1 - 原有接口"],
                "summary": "知识库搜索",
                "description": "检索知识库内容",
                "operationId": "search",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "搜索查询"
                    },
                    {
                        "name": "n",
                        "in": "query",
                        "schema": {"type": "integer", "default": 5},
                        "description": "返回结果数量"
                    },
                    {
                        "name": "hybrid",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["true", "false"]},
                        "description": "是否使用混合搜索"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "搜索成功"
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "ChatRequest": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "用户消息",
                        "minLength": 1,
                        "maxLength": 2000
                    },
                    "session_id": {
                        "type": "string",
                        "description": "会话ID，不提供则自动创建"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户ID"
                    },
                    "user_type": {
                        "type": "string",
                        "enum": ["student", "parent", "teacher"],
                        "default": "student",
                        "description": "用户类型"
                    },
                    "use_rag": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否使用知识库检索"
                    },
                    "use_tools": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否使用工具调用"
                    }
                },
                "required": ["message"]
            },
            "ChatResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "answer": {
                                "type": "string",
                                "description": "AI回复"
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["chat", "psychology", "education", "crisis"],
                                "description": "处理模式"
                            },
                            "emotion": {
                                "type": "object",
                                "properties": {
                                    "emotion": {"type": "string"},
                                    "intensity": {"type": "number"},
                                    "icon": {"type": "string"}
                                }
                            },
                            "crisis_level": {"type": "string"},
                            "sources": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"},
                                        "source": {"type": "string"},
                                        "similarity": {"type": "number"}
                                    }
                                }
                            },
                            "session_id": {"type": "string"},
                            "execution_time": {"type": "number"}
                        }
                    },
                    "request_id": {"type": "string"},
                    "timestamp": {"type": "string"}
                }
            },
            "EmotionCheckRequest": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "待检测文本",
                        "minLength": 1,
                        "maxLength": 1000
                    }
                },
                "required": ["text"]
            },
            "EmotionResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "emotion": {
                                "type": "string",
                                "enum": ["happy", "sad", "anxious", "angry", "fearful", "neutral"]
                            },
                            "intensity": {"type": "number"},
                            "icon": {"type": "string"},
                            "keywords": {"type": "array", "items": {"type": "string"}},
                            "suggestion": {"type": "string"}
                        }
                    },
                    "request_id": {"type": "string"}
                }
            },
            "CrisisCheckRequest": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "待检测文本",
                        "minLength": 1,
                        "maxLength": 1000
                    }
                },
                "required": ["text"]
            },
            "CrisisResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "string",
                                "enum": ["safe", "low", "medium", "high", "critical"]
                            },
                            "signals": {"type": "array"},
                            "message": {"type": "string"},
                            "action": {"type": "string"},
                            "hotlines": {"type": "array", "items": {"type": "string"}},
                            "requires_intervention": {"type": "boolean"}
                        }
                    },
                    "request_id": {"type": "string"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "error"},
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                            "field": {"type": "string"},
                            "details": {"type": "object"}
                        }
                    },
                    "request_id": {"type": "string"}
                }
            }
        },
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API认证密钥"
            }
        }
    }
}


def get_openapi_spec() -> dict:
    """获取OpenAPI规范"""
    return OPENAPI_SPEC
