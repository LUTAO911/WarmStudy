@echo off
chcp 65001 >nul
echo ========================================
echo   暖学帮 - 环境配置脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

echo [1/4] 检测 Python...
python --version
echo.

REM 创建虚拟环境
echo [2/4] 创建虚拟环境 (.venv)...
if exist .venv (
    echo    .venv 已存在，跳过创建
) else (
    python -m venv .venv
    echo    虚拟环境创建成功
)
echo.

REM 激活虚拟环境并安装依赖
echo [3/4] 安装依赖包...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
echo.

REM 复制环境变量文件
echo [4/4] 配置环境变量...
if not exist .env (
    copy .env.example .env
    echo    已创建 .env 文件，请编辑填入你的 API Key
) else (
    echo    .env 已存在
)
echo.

echo ========================================
echo   配置完成！
echo ========================================
echo.
echo 下一步:
echo   1. 编辑 .env 填入你的 API Key
echo   2. 运行 start_venv.bat 启动服务
echo.
pause
