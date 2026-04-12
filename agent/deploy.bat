@echo off
REM 暖学帮部署脚本
echo ============================================
echo   暖学帮 Agent 系统部署
echo ============================================
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker未安装，请先安装Docker
    pause
    exit /b 1
)

echo [1/4] 构建Docker镜像...
docker build -t nuanxuebang-agent:latest .
if %errorlevel% neq 0 (
    echo [ERROR] 镜像构建失败
    pause
    exit /b 1
)
echo [OK] 镜像构建成功

echo.
echo [2/4] 创建数据目录...
if not exist "data\agent\memory" mkdir "data\agent\memory"
if not exist "data\cache" mkdir "data\cache"
if not exist "logs" mkdir "logs"
echo [OK] 目录创建成功

echo.
echo [3/4] 启动容器...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] 容器启动失败
    pause
    exit /b 1
)
echo [OK] 容器启动成功

echo.
echo [4/4] 检查服务状态...
timeout /t 5 /nobreak >nul
curl -f http://localhost:5177/api/v5/status >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 服务运行正常
) else (
    echo [WARN] 服务可能未就绪，请稍后检查
)

echo.
echo ============================================
echo   部署完成!
echo ============================================
echo.
echo   API地址: http://localhost:5177
echo   API文档: http://localhost:5177/api/docs/ui
echo.
echo   常用命令:
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo.
pause
