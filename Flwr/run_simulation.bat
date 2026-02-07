@echo off
chcp 65001 >nul
title FL Simulation
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set "SERVER_ADDRESS=0.0.0.0:8080"
set "TOTAL_CLIENTS=10"
set "USE_SIMULATION=1"

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 清理旧日志
del /f server.log tmaa_server_audit.log client_*.log 2>nul

echo 🚀 正在启动仿真 (Windows)...
echo    - 服务器: 1
echo    - 客户端: 10 (4个恶意, 6个诚实)
echo    - 模式: 真实执行 + 模拟 L4 监控

:: 1. 启动服务器
echo -------------------------------------------
echo 🔵 正在启动服务器...
start /B "Server" cmd /c "python server/server.py > server.log 2>&1"
echo    服务器已在后台启动。
timeout /t 5 /nobreak >nul

:: 2. 启动恶意客户端
echo -------------------------------------------
echo 🔴 正在启动恶意客户端...

:: Client 0: 标签翻转
echo    [C0] 恶意: 标签翻转 (Label Flip)
start /B "Client 0" cmd /c "set CLIENT_ID=0&& set ATTACK_TYPE=label_flip&& set POISON_RATE=0.5&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_0.log 2>&1"

:: Client 1: 后门攻击
echo    [C1] 恶意: 后门攻击 (Backdoor)
start /B "Client 1" cmd /c "set CLIENT_ID=1&& set ATTACK_TYPE=backdoor&& set POISON_RATE=0.2&& set TARGET_LABEL=0&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_1.log 2>&1"

:: Client 2: 干净标签攻击
echo    [C2] 恶意: 干净标签攻击 (Clean Label)
start /B "Client 2" cmd /c "set CLIENT_ID=2&& set ATTACK_TYPE=clean_label&& set POISON_RATE=0.5&& set TARGET_LABEL=0&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_2.log 2>&1"

:: Client 3: 语义攻击
echo    [C3] 恶意: 语义攻击 (Semantic)
start /B "Client 3" cmd /c "set CLIENT_ID=3&& set ATTACK_TYPE=semantic&& set POISON_RATE=0.5&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_3.log 2>&1"

timeout /t 2 /nobreak >nul

:: 3. 启动诚实客户端
echo -------------------------------------------
echo 🟢 正在启动诚实客户端 (C4 - C9)...

for /L %%i in (4,1,9) do (
   echo    [C%%i] 诚实节点
   start /B "Client %%i" cmd /c "set CLIENT_ID=%%i&& set ATTACK_TYPE=none&& set TOTAL_CLIENTS=10&& set USE_SIMULATION=1&& python Client/client.py > client_%%i.log 2>&1"
)

echo -------------------------------------------
echo ✅ 所有进程已在后台启动。
echo    - 检查日志: server.log, tmaa_server_audit.log, client_*.log
echo.
echo -------------------------------------------
echo 📺 查看实时仪表板:
echo    1. 打开一个新的终端窗口 (或 SSH 会话)
echo    2. 进入此目录
echo    3. 运行: python dashboard.py
echo -------------------------------------------

echo.
echo 🛑 仿真正在运行中。
echo    按任意键停止所有进程并退出。
echo -------------------------------------------
pause >nul

echo.
echo 🛑 仿真已停止。正在清理...

:: 退出时清理进程
taskkill /F /IM python.exe /T 2>nul
