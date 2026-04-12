@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo WarmStudy - Docker Mode
echo ========================================

echo [1/5] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Docker not found!
    echo   Please install Docker Desktop
    pause
    exit /b 1
)

echo [2/5] Checking .env...
if not exist ".env" (
    copy .env.example .env 2>nul
    if not exist ".env" (
        (
            echo DASHSCOPE_API_KEY=your_key_here
            echo MINIMAX_API_KEY=your_key_here
            echo CHAT_MODEL=dashscope
            echo DASHSCOPE_MODEL=qwen-max
        ) > .env
    )
)

echo [3/5] Building Docker image...
docker build -t nuanxuebang-rag:latest .
if errorlevel 1 (
    echo   ERROR: Build failed!
    pause
    exit /b 1
)

echo [4/5] Stopping old containers...
docker stop rag-server api-gateway >nul 2>&1
docker rm rag-server api-gateway >nul 2>&1

echo [5/5] Starting services...
echo.

echo Starting RAG Agent (5177)...
docker run -d --name rag-server -p 5177:5177 ^
  -v "%cd%\data:/app/data" ^
  -v "%cd%\uploads:/app/uploads" ^
  -v "%cd%\logs:/app/logs" ^
  --env-file .env nuanxuebang-rag:latest python app.py

echo Starting API Gateway (8000)...
docker run -d --name api-gateway -p 8000:8000 ^
  -e RAG_AGENT_URL=http://rag-server:5177 ^
  --env-file .env nuanxuebang-rag:latest python api_gateway.py

timeout /t 5 >nul

docker ps | findstr "rag-server api-gateway" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: Containers failed to start
    echo   Check logs: docker logs rag-server
    echo                docker logs api-gateway
) else (
    echo.
    echo ========================================
    echo  Docker services started!
    echo ========================================
    echo.
    echo  AI Chat:   http://localhost:8000
    echo  RAG Admin: http://localhost:5177
    echo.
    echo  Stop: docker stop rag-server api-gateway
    echo ========================================
    start http://localhost:8000
)

pause
