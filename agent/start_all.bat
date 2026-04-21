@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo WarmStudy - Quick Start
echo ========================================

set VENV_PYTHON=.venv\Scripts\python.exe
set REQUIREMENTS=requirements.txt

echo [1/4] Checking venv...
if not exist "%VENV_PYTHON%" (
    python -m venv .venv
)

echo [2/4] Installing dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip -q
if exist "%REQUIREMENTS%" (
    "%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS%" -q
) else (
    "%VENV_PYTHON%" -m pip install flask flask-cors chromadb dashscope requests python-dotenv -q
)

echo [3/4] Checking .env config...
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
    ) else (
        echo # WarmStudy environment example>.env
        echo CHAT_MODEL=qwen>>.env
        echo DASHSCOPE_API_KEY=your_key_here>>.env
        echo DASHSCOPE_MODEL=qwen-plus>>.env
        echo MINIMAX_API_KEY=your_key_here>>.env
        echo RAG_AGENT_URL=http://localhost:5177>>.env
        echo FLASK_ENV=production>>.env
        echo LOG_LEVEL=INFO>>.env
    )
)

echo [4/4] Starting services...

echo Starting RAG Agent (5177)...
start "RAG-Agent-5177" cmd /k "%VENV_PYTHON% app.py"

timeout /t 2 >nul

echo Starting API Gateway (8000)...
start "API-Gateway-8000" cmd /k "%VENV_PYTHON% api_gateway.py"

timeout /t 3 >nul

echo.
echo All services started!
echo AI Chat: http://localhost:8000
echo RAG Admin: http://localhost:5177

start http://localhost:8000
pause
