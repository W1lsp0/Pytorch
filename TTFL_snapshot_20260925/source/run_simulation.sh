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
SERVER_ADDRESS="${SERVER_ADDRESS:-0.0.0.0:8080}"
TOTAL_CLIENTS="${TOTAL_CLIENTS:-20}"
USE_SIMULATION="${USE_SIMULATION:-1}"  # 启用基于数据库的 L4 模拟监控
PYTHON_BIN="${PYTHON_BIN:-python}"
NUM_ROUNDS="${NUM_ROUNDS:-30}"
LOCAL_EPOCHS="${LOCAL_EPOCHS:-3}"
AGGREGATION_MODE="${AGGREGATION_MODE:-ttfl}"
ATTACK_START_ROUND="${ATTACK_START_ROUND:-1}"
ATTACK_STOP_ROUND="${ATTACK_STOP_ROUND:-0}"
ATTACK_PROFILE="${ATTACK_PROFILE:-mixed}"
BACKDOOR_POISON_RATE="${BACKDOOR_POISON_RATE:-0.2}"
EXPERIMENT_SEED="${EXPERIMENT_SEED:-20240925}"
SHARED_CLIENT_POOL_SIZE="${SHARED_CLIENT_POOL_SIZE:-0}"
SERVER_PROXY_SIZE="${SERVER_PROXY_SIZE:-500}"
ENABLE_KNOWN_TRIGGER_PROBE="${ENABLE_KNOWN_TRIGGER_PROBE:-0}"
USE_CLIENT_REPORT_FOR_DECISIONS="${USE_CLIENT_REPORT_FOR_DECISIONS:-0}"
RESET_TTFL_DB="${RESET_TTFL_DB:-0}"
DRY_RUN="${DRY_RUN:-0}"
export SERVER_ADDRESS TOTAL_CLIENTS NUM_ROUNDS LOCAL_EPOCHS AGGREGATION_MODE ATTACK_START_ROUND ATTACK_STOP_ROUND EXPERIMENT_SEED ATTACK_PROFILE BACKDOOR_POISON_RATE
export SHARED_CLIENT_POOL_SIZE SERVER_PROXY_SIZE ENABLE_KNOWN_TRIGGER_PROBE
export USE_CLIENT_REPORT_FOR_DECISIONS
export TTFL_DB_HOST="${TTFL_DB_HOST:-127.0.0.1}"
export TTFL_DB_PORT="${TTFL_DB_PORT:-3306}"
export TTFL_DB_USER="${TTFL_DB_USER:-root}"
export TTFL_SERVER_DB="${TTFL_SERVER_DB:-tmaa_server}"

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
echo "   - 客户端: ${TOTAL_CLIENTS}"
echo "   - 模式: 真实执行 + 模拟 L4 监控"
echo "   - 数据库管理器: 已启用 (状态跟踪)"
echo "   - 日志目录: ./log/"

case "$ATTACK_PROFILE" in
  none)
    C0_ATTACK=none; C0_RATE=0; C1_ATTACK=none; C1_RATE=0
    C2_ATTACK=none; C2_RATE=0; C3_ATTACK=none; C3_RATE=0
    ;;
  backdoor)
    C0_ATTACK=none; C0_RATE=0; C1_ATTACK=backdoor; C1_RATE="$BACKDOOR_POISON_RATE"
    C2_ATTACK=none; C2_RATE=0; C3_ATTACK=none; C3_RATE=0
    ;;
  mixed)
    C0_ATTACK=label_flip; C0_RATE=0.5; C1_ATTACK=backdoor; C1_RATE=0.2
    C2_ATTACK=clean_label; C2_RATE=0.5; C3_ATTACK=semantic; C3_RATE=0.5
    ;;
  *)
    echo "未知 ATTACK_PROFILE=$ATTACK_PROFILE，可选 none/backdoor/mixed" >&2
    exit 2
    ;;
esac

# 清理 MySQL 历史记录库
echo "-------------------------------------------"
echo "🚮 数据库清理开关 RESET_TTFL_DB=${RESET_TTFL_DB}"
if [ "$RESET_TTFL_DB" = "1" ] && ! "$PYTHON_BIN" - <<'PY'
import sys
import os

try:
    import mysql.connector
except Exception as exc:
    print(f"无法导入 mysql.connector: {exc}")
    sys.exit(1)

try:
    cnx = mysql.connector.connect(
        host=os.environ.get("TTFL_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("TTFL_DB_PORT", "3306")),
        user=os.environ.get("TTFL_DB_USER", "root"),
        password=os.environ.get("TTFL_DB_PASSWORD", ""),
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
if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_COUNT="$(nvidia-smi --query-gpu=index --format=csv,noheader 2>/dev/null | wc -l | tr -d ' ')"
else
    GPU_COUNT=0
fi
if [ "${GPU_COUNT:-0}" -lt 1 ]; then
    GPU_COUNT=0
    SERVER_DEVICE=""
    echo "ℹ️ 未检测到 NVIDIA GPU，客户端和服务端使用 CPU"
else
    SERVER_DEVICE=0
    echo "ℹ️ 检测到 ${GPU_COUNT} 张 GPU，客户端按轮询方式分配"
fi

if [ "$DRY_RUN" = "1" ]; then
    echo "DRY_RUN: mode=$AGGREGATION_MODE profile=$ATTACK_PROFILE clients=$TOTAL_CLIENTS rounds=$NUM_ROUNDS"
    for i in $(seq 0 $((TOTAL_CLIENTS - 1))); do
        if [ "$GPU_COUNT" -gt 0 ]; then gpu=$((i % GPU_COUNT)); else gpu=CPU; fi
        echo "DRY_RUN: client=$i gpu=$gpu"
    done
    exit 0
fi

echo "-------------------------------------------"
echo "🔵 正在启动服务器 (GPU ${SERVER_DEVICE:-CPU})..."
ENABLE_KNOWN_TRIGGER_PROBE="$ENABLE_KNOWN_TRIGGER_PROBE" HEAVY_PROBE_ROTATE_MOD="${HEAVY_PROBE_ROTATE_MOD:-5}" CUDA_VISIBLE_DEVICES="$SERVER_DEVICE" \
"$PYTHON_BIN" server/server.py --server_address=$SERVER_ADDRESS > log/server.log 2>&1 &
SERVER_PID=$!
echo "   服务器 PID: $SERVER_PID"
echo "   正在等待服务器初始化..."
sleep 5

# ================= 启动所有客户端 (自动 GPU 轮询) =================

echo "-------------------------------------------"
if [ "$ATTACK_PROFILE" = "none" ]; then
  echo "🔵 正在启动客户端 (无攻击配置) -> GPU 0..."
else
  echo "🔴 正在启动攻击配置客户端 (C0-C3) -> GPU 0..."
fi

# Client 0: 标签翻转
echo "   [C0] ATTACK_TYPE=${C0_ATTACK} -> GPU 0"
CUDA_VISIBLE_DEVICES="$SERVER_DEVICE" CLIENT_ID=0 ATTACK_TYPE=$C0_ATTACK POISON_RATE=$C0_RATE TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_0.log 2>&1 &

# Client 1: 后门攻击
echo "   [C1] ATTACK_TYPE=${C1_ATTACK} -> GPU 0"
CUDA_VISIBLE_DEVICES="$SERVER_DEVICE" CLIENT_ID=1 ATTACK_TYPE=$C1_ATTACK POISON_RATE=$C1_RATE TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_1.log 2>&1 &

# Client 2: 干净标签
echo "   [C2] ATTACK_TYPE=${C2_ATTACK} -> GPU 0"
CUDA_VISIBLE_DEVICES="$SERVER_DEVICE" CLIENT_ID=2 ATTACK_TYPE=$C2_ATTACK POISON_RATE=$C2_RATE TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_2.log 2>&1 &

# Client 3: 语义攻击
echo "   [C3] ATTACK_TYPE=${C3_ATTACK} -> GPU 0"
CUDA_VISIBLE_DEVICES="$SERVER_DEVICE" CLIENT_ID=3 ATTACK_TYPE=$C3_ATTACK POISON_RATE=$C3_RATE TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > log/client_3.log 2>&1 &

sleep 2

# 启动诚实客户端 C4 - C19
# Group A (IID): 4-9
# Group B (Mod): 10-14
# Group C (Ext): 15-19

for ((i=4; i<TOTAL_CLIENTS; i++))
do
   # 计算所属组别名称 (仅用于日志显示)
   GROUP_NAME="Unknown"
   if [ $i -le 9 ]; then GROUP_NAME="Group A (IID)";
   elif [ $i -le 14 ]; then GROUP_NAME="Group B (Mod)";
   else GROUP_NAME="Group C (Ext)"; fi

   if [ "$GPU_COUNT" -gt 0 ]; then
       GPU_ID=$(( i % GPU_COUNT ))
   else
       GPU_ID=""
   fi
   
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
