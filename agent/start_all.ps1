# WarmStudy Quick Start Script
$ErrorActionPreference = "Stop"
$AgentDir = "C:\Users\34206\OneDrive\Desktop\项目\暖学帮\agent"
$VenvPython = Join-Path $AgentDir ".venv\Scripts\python.exe"

Set-Location $AgentDir
Write-Host "========================================"
Write-Host "WarmStudy - Quick Start"
Write-Host "========================================"
Write-Host ""

# Check venv
Write-Host "[1/4] Checking venv..."
if (-not (Test-Path $VenvPython)) {
    Write-Host "   Creating venv..."
    & python -m venv .venv
}
Write-Host "   OK"

# Install deps
Write-Host "[2/4] Installing dependencies..."
& $VenvPython -m pip install --upgrade pip -q
& $VenvPython -m pip install flask flask-cors chromadb dashscope -q
Write-Host "   OK"

# Check .env
Write-Host "[3/4] Checking .env..."
$EnvFile = Join-Path $AgentDir ".env"
if (-not (Test-Path $EnvFile)) {
    @"
DASHSCOPE_API_KEY=your_key_here
MINIMAX_API_KEY=your_key_here
CHAT_MODEL=dashscope
DASHSCOPE_MODEL=qwen-max
"@ | Out-File -FilePath $EnvFile -Encoding UTF8
    Write-Host "   NOTE: .env created, please edit to add API keys"
} else {
    Write-Host "   OK"
}

# Start services
Write-Host "[4/4] Starting services..."
Write-Host ""

# Check port 5177
$Port5177 = Get-NetTCPConnection -LocalPort 5177 -ErrorAction SilentlyContinue
if ($Port5177) {
    Write-Host "Port 5177 is in use, skipping RAG Agent"
} else {
    Write-Host "Starting RAG Agent (5177)..."
    Start-Process cmd -ArgumentList "/k $VenvPython app.py" -WindowStyle Normal
}

Start-Sleep -Seconds 2

# Check port 8000
$Port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($Port8000) {
    Write-Host "Port 8000 is in use, skipping API Gateway"
} else {
    Write-Host "Starting API Gateway (8000)..."
    Start-Process cmd -ArgumentList "/k $VenvPython api_gateway.py" -WindowStyle Normal
}

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================"
Write-Host " All services started!"
Write-Host "========================================"
Write-Host ""
Write-Host " AI Chat:   http://localhost:8000"
Write-Host " RAG Admin: http://localhost:5177"
Write-Host ""
Write-Host " Close windows to stop services"
Write-Host "========================================"

Start-Process "http://localhost:8000"
