@echo off
chcp 65001 >nul
title FL Simulation
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set "SERVER_ADDRESS=0.0.0.0:8080"
set "TOTAL_CLIENTS=10"
set "USE_SIMULATION=1"

:: Change directory to script location
cd /d "%~dp0"

:: Cleanup logs
del /f server.log tmaa_server_audit.log client_*.log 2>nul

echo 🚀 Starting Simulation (Windows)...
echo    - Server: 1
echo    - Clients: 10 (4 Bad, 6 Good)
echo    - Mode: Real Execution + Simulated L4 Monitor

:: 1. Start Server
echo -------------------------------------------
echo 🔵 Launching Server...
start /B "Server" cmd /c "python server/server.py > server.log 2>&1"
echo    Server launched in background.
timeout /t 5 /nobreak >nul

:: 2. Start Malicious Clients
echo -------------------------------------------
echo 🔴 Launching Malicious Clients...

:: Client 0: Label Flip
echo    [C0] Malicious: Label Flip
start /B "Client 0" cmd /c "set CLIENT_ID=0&& set ATTACK_TYPE=label_flip&& set POISON_RATE=0.5&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_0.log 2>&1"

:: Client 1: Backdoor
echo    [C1] Malicious: Backdoor
start /B "Client 1" cmd /c "set CLIENT_ID=1&& set ATTACK_TYPE=backdoor&& set POISON_RATE=0.2&& set TARGET_LABEL=0&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_1.log 2>&1"

:: Client 2: Clean Label
echo    [C2] Malicious: Clean Label
start /B "Client 2" cmd /c "set CLIENT_ID=2&& set ATTACK_TYPE=clean_label&& set POISON_RATE=0.5&& set TARGET_LABEL=0&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_2.log 2>&1"

:: Client 3: Semantic
echo    [C3] Malicious: Semantic
start /B "Client 3" cmd /c "set CLIENT_ID=3&& set ATTACK_TYPE=semantic&& set POISON_RATE=0.5&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_3.log 2>&1"

timeout /t 2 /nobreak >nul

:: 3. Start Honest Clients
echo -------------------------------------------
echo 🟢 Launching Honest Clients (C4 - C9)...

for /L %%i in (4,1,9) do (
   echo    [C%%i] Honest Node
   start /B "Client %%i" cmd /c "set CLIENT_ID=%%i&& set ATTACK_TYPE=none&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_%%i.log 2>&1"
)

echo -------------------------------------------
echo ✅ All processes launched in background.
echo    - Check logs: server.log, tmaa_server_audit.log, client_*.log
echo.
echo 📊 Starting Dashboard (Inline Mode)...
echo    (Press Ctrl+C inside the dashboard to stop simulation)
python dashboard.py

echo.
echo 🛑 Simulation stopped. Cleaning up...

:: Cleanup processes on exit
taskkill /F /IM python.exe /T 2>nul
