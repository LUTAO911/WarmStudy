# 编码规范与代码风格指南

## 暖学帮 Agent 项目

**版本**: 1.0.0
**最后更新**: 2026-04-11

---

## 1. Python 版本与依赖

- **Python 版本**: >= 3.10
- **依赖管理**: Poetry 或 pip-tools
- **虚拟环境**: 必须使用 venv 或 conda

---

## 2. 代码格式化

### 2.1 格式化工具

| 工具 | 用途 | 配置文件 |
|------|------|----------|
| **Black** | 代码格式化 | `pyproject.toml` |
| **isort** | import 排序 | `pyproject.toml` |
| **mdformat** | Markdown 格式化 | `.mdformat.toml` |

### 2.2 格式化规则

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["agent"]
known_third_party = ["flask", "dashscope"]
```

---

## 3. 类型提示规范

### 3.1 必须使用类型提示的场景

- 所有公共函数和方法的参数、返回值
- 类实例变量和类变量
- 模块级变量（尽量）

### 3.2 类型提示示例

```python
# ✅ 正确示例
def process_data(items: List[Dict[str, Any]], config: Optional[Config] = None) -> Iterator[Result]:
    ...

# ❌ 错误示例
def process_data(items, config=None):
    ...
```

### 3.3 类型约定

| 类型 | 约定 |
|------|------|
| 列表 | `List[T]` 而非 `list` |
| 字典 | `Dict[K, V]` 而非 `dict` |
| 可选字符串 | `Optional[str]` 而非 `str \| None` |
| 无返回 | `None` 而非 `void` |

---

## 4. 命名规范

### 4.1 命名风格

| 元素 | 风格 | 示例 |
|------|------|------|
| 模块 | lowercase + underscore | `memory_manager.py` |
| 类 | PascalCase | `ShortTermMemory` |
| 函数 | lowercase + underscore | `get_context()` |
| 变量 | lowercase + underscore | `session_id` |
| 常量 | UPPERCASE + underscore | `MAX_RETRIES` |
| 类型变量 | PascalCase | `T`, `K`, `V` |

### 4.2 命名规则

```python
# 类名：名词或名词短语
class Agent: ...
class MemoryEntry: ...

# 函数：动词或动词短语
def add_message(): ...
def search_memories(): ...

# 布尔变量：is/has/can/should 前缀
is_active: bool
has_permission: bool
can_execute: bool

# 私有成员：单下划线前缀
def _private_method(self): ...
_lock: threading.RLock  # 实例变量
```

---

## 5. 函数设计原则

### 5.1 函数长度

- **最大行数**: 100 行
- **理想行数**: 30-50 行
- **单一职责**: 每个函数只做一件事

### 5.2 参数规范

- **最大参数**: 5 个（使用 dataclass 或字典传递更多参数）
- **参数验证**: 在函数开头验证参数有效性
- **默认值**: 尽量使用不可变默认值（`None`, `tuple` 而非 `list`）

```python
# ✅ 正确示例
def create_agent(
    name: str,
    config: Optional[AgentConfig] = None,
    memory: Optional[MemoryManager] = None
) -> Agent:
    if name is None:
        raise ValueError("name cannot be None")
    ...

# ❌ 错误示例
def create_agent(name=None, config=None):
    if not name:
        raise ValueError("name cannot be None")
    ...
```

---

## 6. 类设计原则

### 6.1 类结构顺序

```python
class MyClass:
    # 1. 类变量和实例变量（类型注解）
    name: str
    _private_var: int

    # 2. @property 装饰器
    @property
    def id(self) -> str: ...

    # 3. 生命周期方法 (__new__, __init__, __del__)
    def __init__(self) -> None: ...

    # 4. 公共方法
    def public_method(self) -> None: ...

    # 5. 私有方法
    def _private_method(self) -> None: ...

    # 6. 静态方法
    @staticmethod
    def utility() -> None: ...
```

### 6.2 数据类规则

```python
# ✅ 使用 frozen=True 保证不可变性
@dataclass(frozen=True)
class MemoryEntry:
    id: str
    content: str
    timestamp: float

# ✅ tuple 优于 list 用于固定数据
@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    metadata: tuple = field(default_factory=tuple)  # 而非 list
```

---

## 7. 异常处理

### 7.1 异常层次

```python
class AgentError(Exception):
    """基础异常类"""
    pass

class ConfigurationError(AgentError):
    """配置错误"""
    pass

class ToolExecutionError(AgentError):
    """工具执行错误"""
    pass

class MemoryError(AgentError):
    """记忆管理错误"""
    pass
```

### 7.2 异常处理规则

- **精确捕获**: 捕获具体异常而非 `Exception`
- **资源清理**: 使用 `try/finally` 或上下文管理器
- **异常链**: 使用 `raise ... from original` 保留原异常

```python
# ✅ 正确示例
try:
    result = tool.execute(**params)
except ToolExecutionError as e:
    logger.error(f"Tool execution failed: {e}")
    raise ToolExecutionError(f"Failed to execute {tool.name}") from e

# ❌ 错误示例
try:
    result = tool.execute(**params)
except Exception as e:
    print(e)
```

---

## 8. 文档字符串

### 8.1 Docstring 格式

使用 Google 风格的 docstring：

```python
def calculate(expression: str) -> Union[float, str]:
    """Calculate a mathematical expression safely.

    Uses AST parsing to safely evaluate mathematical expressions
    without using eval().

    Args:
        expression: A mathematical expression string (e.g., "2 + 3 * 4")

    Returns:
        The calculated result as float, or error message as str.

    Raises:
        ValueError: If expression contains invalid characters.

    Example:
        >>> calculate("2 + 3")
        5.0
    """
```

### 8.2 文档要求

| 元素 | 要求 |
|------|------|
| 模块 | 每个 `.py` 文件顶部的模块 docstring |
| 类 | 公共类的 docstring |
| 公共函数 | 所有公共函数的 docstring |
| 复杂逻辑 | 复杂代码块的行内注释 |

---

## 9. 测试要求

### 9.1 测试覆盖率目标

| 模块 | 最低覆盖率 |
|------|------------|
| 核心模块 (agent) | 90% |
| API 路由 | 80% |
| 工具模块 | 85% |

### 9.2 测试命名

```python
# 测试文件: tests/test_memory.py
# 测试类: TestShortTermMemory
# 测试函数: test_add_entry_success, test_add_entry_with_metadata

class TestShortTermMemory:
    def test_add_entry_success(self) -> None: ...
    def test_add_entry_with_metadata(self) -> None: ...
    def test_get_recent_returns_latest_first(self) -> None: ...
```

---

## 10. Git 提交规范

### 10.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 10.2 类型标识

| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构（不是新功能或修复） |
| test | 测试相关 |
| chore | 构建/工具相关 |

### 10.3 示例

```
feat(memory): add thread-safe LongTermMemory implementation

- Add RLock for concurrent access protection
- Implement atomic file operations
- Add temp file + rename pattern for data safety

Closes #123
```

---

## 11. 代码审查清单

### 11.1 必需项

- [ ] 所有函数/方法有类型注解
- [ ] 所有公共 API 有 docstring
- [ ] 无未处理的异常
- [ ] 测试覆盖新增代码
- [ ] 通过所有 CI 检查

### 11.2 推荐项

- [ ] 函数长度 < 100 行
- [ ] 圈复杂度 < 10
- [ ] 无重复代码（DRY 原则）
- [ ] 错误信息有意义

---

## 12. 违规处理

| 级别 | 处罚 |
|------|------|
| **Error** | 阻塞合并，必须修复 |
| **Warning** | 建议修复，code owner 决定 |
| **Info** | 建议参考，无需强制 |

---

## 附录: 工具配置参考

- **Black**: `pyproject.toml` `[tool.black]`
- **isort**: `pyproject.toml` `[tool.isort]`
- **flake8**: `setup.cfg` 或 `.flake8`
- **mypy**: `pyproject.toml` `[tool.mypy]`
- **pylint**: `pyproject.toml` `[tool.pylint]`
- **pytest**: `pyproject.toml` `[tool.pytest]`

---

**维护者**: Development Team
**审核周期**: 每个 PR 必须通过审查