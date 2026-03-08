#!/bin/bash
# ==============================================================================
# 脚本名: run_simulation.sh
# 功能: 联邦学习仿真启动脚本
# 描述:
#     一键启动 Flower 联邦学习环境，包括:
#     1. 聚合服务器 (Server)
#     2. 恶意客户端 (Malicious Clients: Label Flip, Backdoor, Clean Label, Semantic)
#     3. 诚实客户端 (Honest Clients)
#     同时集成了 TMAA (Trusted Model Audit Agent) 的 L4 级模拟监控。
#
# 作者: Flwr 联邦学习项目组
# 日期: 2024
# ==============================================================================

set -e

# 屏蔽 gRPC 中频繁出现的 fork() 线程警告
export GRPC_ENABLE_FORK_SUPPORT=0
export GRPC_POLL_STRATEGY=epoll1

# ================= 配置 =================
SERVER_ADDRESS="0.0.0.0:8080"
TOTAL_CLIENTS=20
USE_SIMULATION=1  # 启用基于数据库的 L4 模拟监控
PYTHON_BIN="/data1/anaconda3/envs/W1lsp0/bin/python"

# 确保在正确目录
cd "$(dirname "$0")"

# 清理旧环境
echo "🧹 正在清理旧进程和日志..."
# Match script path instead of interpreter to be safe
pkill -f "server/server.py" || true
pkill -f "Client/client.py" || true
wait # 等待进程完全退出

# 创建日志目录 (如果不存在)
mkdir -p log

# 清理旧日志 (清空 log 目录)
rm -f log/*
# 同时清理可能残留的根目录日志 (兼容旧习惯)
rm -f server.log tmaa_server_audit.log client_*.log dashboard_debug.log

echo "🚀 正在启动仿真..."
echo "   - 服务器: 1"
echo "   - 客户端: 20 (Group A: 10, Group B: 5, Group C: 5)"
echo "   - 模式: 真实执行 + 模拟 L4 监控"
echo "   - 数据库管理器: 已启用 (状态跟踪)"
echo "   - 日志目录: ./log/"

# 清理 MySQL 历史记录库
echo "-------------------------------------------"
echo "🚮 正在清空 tmaa_server 历史数据库..."
if ! "$PYTHON_BIN" - <<'PY'
import sys

try:
    import mysql.connector
except Exception as exc:
    print(f"无法导入 mysql.connector: {exc}")
    sys.exit(1)

try:
    cnx = mysql.connector.connect(
        host="202.113.76.179",
        port=3306,
        user="root",
        password="root123456",
    )
    cursor = cnx.cursor()
    cursor.execute("DROP DATABASE IF EXISTS tmaa_server;")
    cnx.commit()
    cursor.close()
    cnx.close()
    print("数据库清理成功")
except Exception as exc:
    print(f"数据库清理失败: {exc}")
    sys.exit(1)
PY
then
    echo "数据库清理失败，将尝试继续执行"
fi

# 1. 启动服务器 (GPU 0)
echo "-------------------------------------------"
echo "🔵 正在启动服务器 (GPU 0)..."
# 服务器占用显存极少，与 C0-C3 共享 GPU 0
CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" server/server.py --server_address=$SERVER_ADDRESS > log/server.log 2>&1 &
SERVER_PID=$!
echo "   服务器 PID: $SERVER_PID"
echo "   正在等待服务器初始化..."
sleep 5

# ================= 启动所有客户端 (负载均衡: 4 Clients/GPU) =================
# GPU 0: Clients 0-3   (Malicious)
# GPU 1: Clients 4-7   (Group A)
# GPU 2: Clients 8-11  (Group A/B)
# GPU 3: Clients 12-15 (Group B/C)
# GPU 4: Clients 16-19 (Group C)

echo "-------------------------------------------"
echo "🔴 正在启动恶意客户端 (C0-C3) -> GPU 0..."

# Client 0: 标签翻转
echo "   [C0] 恶意 (Label Flip) -> GPU 0"
CUDA_VISIBLE_DEVICES=0 CLIENT_ID=0 ATTACK_TYPE=label_flip POISON_RATE=0.5 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_0.log 2>&1 &

# Client 1: 后门攻击
echo "   [C1] 恶意 (Backdoor) -> GPU 0"
CUDA_VISIBLE_DEVICES=0 CLIENT_ID=1 ATTACK_TYPE=backdoor POISON_RATE=0.2 TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_1.log 2>&1 &

# Client 2: 干净标签
echo "   [C2] 恶意 (Clean Label) -> GPU 0"
CUDA_VISIBLE_DEVICES=0 CLIENT_ID=2 ATTACK_TYPE=clean_label POISON_RATE=0.5 TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_2.log 2>&1 &

# Client 3: 语义攻击
echo "   [C3] 恶意 (Semantic) -> GPU 0"
CUDA_VISIBLE_DEVICES=0 CLIENT_ID=3 ATTACK_TYPE=semantic POISON_RATE=0.5 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_3.log 2>&1 &

sleep 2

# 启动诚实客户端 C4 - C19
# Group A (IID): 4-9
# Group B (Mod): 10-14
# Group C (Ext): 15-19

for i in {4..19}
do
   # 计算所属组别名称 (仅用于日志显示)
   GROUP_NAME="Unknown"
   if [ $i -le 9 ]; then GROUP_NAME="Group A (IID)";
   elif [ $i -le 14 ]; then GROUP_NAME="Group B (Mod)";
   else GROUP_NAME="Group C (Ext)"; fi

   # 计算 GPU ID: floor(i / 4)
   # 4-7->1, 8-11->2, 12-15->3, 16-19->4
   GPU_ID=$(( i / 4 ))
   
   echo "   [C$i] Assigner: $GROUP_NAME -> GPU $GPU_ID"
   CUDA_VISIBLE_DEVICES=$GPU_ID CLIENT_ID=$i ATTACK_TYPE=none TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
   "$PYTHON_BIN" Client/client.py > log/client_$i.log 2>&1 &
   
   # 每启动 4 个暂停一下，避免冲击
   if [ $(( (i+1) % 4 )) -eq 0 ]; then
       sleep 1
   fi
done

echo "-------------------------------------------"
echo "✅ 所有进程已启动。"
echo "   - 跟踪服务器日志:  tail -f log/server.log"
echo "   - 跟踪审计日志:    tail -f log/tmaa_server_audit.log"
echo "   - 检查客户端日志:  cat log/client_*.log"
echo ""
echo "-------------------------------------------"
echo "📺 查看实时仪表板:"
echo "   1. 打开一个新的终端窗口"
echo "   2. 进入此目录"
echo "   3. 运行: $PYTHON_BIN dashboard.py"
echo "-------------------------------------------"
echo ""
echo "按 Ctrl+C 停止所有进程。"

# 等待所有后台进程
wait
