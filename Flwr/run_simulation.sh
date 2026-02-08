#!/bin/bash
set -e

# ================= 配置 =================
SERVER_ADDRESS="0.0.0.0:8080"
TOTAL_CLIENTS=10
USE_SIMULATION=1  # 启用基于数据库的 L4 模拟监控

# 确保在正确目录
cd "$(dirname "$0")"

# 清理旧环境
echo "🧹 正在清理旧进程和日志..."
pkill -f "python server/server.py" || true
pkill -f "python Client/client.py" || true
wait # 等待进程完全退出

# 清理旧日志
rm -f server.log tmaa_server_audit.log client_*.log dashboard_debug.log

echo "🚀 正在启动仿真..."
echo "   - 服务器: 1"
echo "   - 客户端: 10 (4个恶意, 6个诚实)"
echo "   - 模式: 真实执行 + 模拟 L4 监控"
echo "   - 数据库管理器: 已启用 (状态跟踪)"

# 1. 启动服务器 (GPU 0)
echo "-------------------------------------------"
echo "🔵 正在启动服务器 (GPU 0)..."
CUDA_VISIBLE_DEVICES=0 python server/server.py > server.log 2>&1 &
SERVER_PID=$!
echo "   服务器 PID: $SERVER_PID"
echo "   正在等待服务器初始化..."
sleep 5

# 2. 启动恶意客户端 (4个节点)
echo "-------------------------------------------"
echo "🔴 正在启动恶意客户端..."

# Client 0: 标签翻转 (GPU 0)
echo "   [C0] 恶意: 标签翻转 (GPU 0)"
CUDA_VISIBLE_DEVICES=0 CLIENT_ID=0 ATTACK_TYPE=label_flip POISON_RATE=0.5 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
python Client/client.py > client_0.log 2>&1 &

# Client 1: 后门攻击 (GPU 0)
echo "   [C1] 恶意: 后门攻击 (GPU 0)"
CUDA_VISIBLE_DEVICES=0 CLIENT_ID=1 ATTACK_TYPE=backdoor POISON_RATE=0.2 TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
python Client/client.py > client_1.log 2>&1 &

# Client 2: 干净标签攻击 (GPU 1)
echo "   [C2] 恶意: 干净标签攻击 (GPU 1)"
CUDA_VISIBLE_DEVICES=1 CLIENT_ID=2 ATTACK_TYPE=clean_label POISON_RATE=0.5 TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
python Client/client.py > client_2.log 2>&1 &

# Client 3: 语义攻击 (GPU 1)
echo "   [C3] 恶意: 语义攻击 (GPU 1)"
CUDA_VISIBLE_DEVICES=1 CLIENT_ID=3 ATTACK_TYPE=semantic POISON_RATE=0.5 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
python Client/client.py > client_3.log 2>&1 &

sleep 2

# 3. 启动诚实客户端 (6个节点, 分布在 GPU 2, 3, 4)
echo "-------------------------------------------"
echo "🟢 正在启动诚实客户端 (C4 - C9)..."

for i in {4..9}
do
   # 计算 GPU ID: (i-4) // 2 + 2
   # 4,5 -> GPU 2; 6,7 -> GPU 3; 8,9 -> GPU 4
   GPU_ID=$(( (i - 4) / 2 + 2 ))
   echo "   [C$i] 诚实节点 (GPU $GPU_ID)"
   CUDA_VISIBLE_DEVICES=$GPU_ID CLIENT_ID=$i ATTACK_TYPE=none TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
   python Client/client.py > client_$i.log 2>&1 &
done

echo "-------------------------------------------"
echo "✅ 所有进程已启动。"
echo "   - 跟踪服务器日志:  tail -f server.log"
echo "   - 跟踪审计日志:    tail -f tmaa_server_audit.log"
echo "   - 检查客户端日志:  cat client_*.log"
echo ""
echo "-------------------------------------------"
echo "📺 查看实时仪表板:"
echo "   1. 打开一个新的终端窗口"
echo "   2. 进入此目录"
echo "   3. 运行: python dashboard.py"
echo "-------------------------------------------"
echo ""
echo "按 Ctrl+C 停止所有进程。"

# 等待所有后台进程
wait
