@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo WarmStudy - RAG Agent (venv mode)
echo ========================================

set VENV_PYTHON=.venv\Scripts\python.exe

echo [1/5] Checking venv...
if not exist "%VENV_PYTHON%" (
    echo   Creating venv...
    python -m venv .venv
)

echo [2/5] Verifying Python...
"%VENV_PYTHON%" -c "import sys; print('Python ' + sys.version.split()[0])"
if errorlevel 1 (
    echo   ERROR: Python not working
    pause
    exit /b 1
)

echo [3/5] Checking dependencies...
"%VENV_PYTHON%" -m pip show flask flask-cors chromadb >nul 2>&1
if errorlevel 1 (
    echo   Installing dependencies...
    "%VENV_PYTHON%" -m pip install --upgrade pip
    "%VENV_PYTHON%" -m pip install -r requirements.txt
)

echo [4/5] Checking .env...
if not exist ".env" (
    (
        echo DASHSCOPE_API_KEY=your_key_here
        echo MINIMAX_API_KEY=your_key_here
        echo CHAT_MODEL=dashscope
        echo DASHSCOPE_MODEL=qwen-max
    ) > .env
)

echo [5/5] Starting RAG Agent...
echo.

netstat -ano | findstr ":5177 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo   Port 5177 is in use!
    echo   Please close existing service first
    pause
    exit /b 1
)

echo Starting...
start "RAG-Agent-5177" cmd /k "%VENV_PYTHON% app.py"

timeout /t 3 >nul

echo.
echo ========================================
echo  RAG Agent started!
echo ========================================
echo.
echo  RAG Admin: http://localhost:5177
echo  AI Chat:   http://localhost:8000
echo ========================================

start http://localhost:5177
pause
