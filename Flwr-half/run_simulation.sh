#!/bin/bash
# ==============================================================================
# 脚本名: run_simulation.sh (Flwr-half)
# 功能: 50% 恶意节点联邦学习仿真启动脚本
# 描述:
#     一键启动 Flower 联邦学习环境（高对抗强度测试场景）：
#     - 服务器: 1 个
#     - 恶意客户端: 10 个（50%），涵盖 6 种攻击类型
#         C0:  Label Flip（数据投毒）
#         C1:  Backdoor（后门攻击）
#         C2:  Clean Label（干净标签后门）
#         C3:  Semantic（语义攻击）
#         C4:  Sign-Flip（符号反转，模型投毒）
#         C5:  Sign-Flip（符号反转，模型投毒）
#         C6:  Gradient-Scale（梯度缩放，模型投毒）
#         C7:  Gradient-Scale（梯度缩放，模型投毒）
#         C8:  Label Flip（数据投毒）
#         C9:  Backdoor（后门攻击）
#     - 正常客户端: 10 个（50%），全部 IID 均匀分布（DATA_GROUP=iid）
#     - 日志目录: ./log/
#
# 与 Flwr 原版的区别:
#     1. 恶意节点从 4/20 增至 10/20
#     2. 新增 sign_flip 和 gradient_scale 两种模型投毒攻击
#     3. 正常节点全部为 IID 均匀分布（非 Non-IID）
#     4. 日志统一写入 log/ 目录
# ==============================================================================

set -e

export GRPC_ENABLE_FORK_SUPPORT=0
export GRPC_POLL_STRATEGY=epoll1

# ================= 配置 =================
SERVER_ADDRESS="0.0.0.0:8080"
TOTAL_CLIENTS=20
USE_SIMULATION=1
PYTHON_BIN="/data1/anaconda3/envs/W1lsp0/bin/python"
LOG_DIR="log"

cd "$(dirname "$0")"

# 清理旧进程
echo "🧹 正在清理旧进程..."
pkill -f "server/server.py" || true
pkill -f "Client/client.py" || true
wait

# 创建日志目录
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*

echo "🚀 正在启动仿真 (Flwr-half: 50% 恶意节点)..."
echo "   - 服务器: 1"
echo "   - 恶意客户端: 10 (C0~C9, 6 种攻击类型)"
echo "   - 正常客户端: 10 (C10~C19, 全部 IID)"
echo "   - 数据库管理器: 已启用"
echo "   - 日志目录: ./$LOG_DIR/"

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

# ===========================================================
# 1. 启动服务器 (GPU 0)
# ===========================================================
echo "-------------------------------------------"
echo "🔵 正在启动服务器 (GPU 0)..."
ENABLE_KNOWN_TRIGGER_PROBE=1 HEAVY_PROBE_ROTATE_MOD=1 CUDA_VISIBLE_DEVICES=0 \
"$PYTHON_BIN" server/server.py --server_address=$SERVER_ADDRESS > "$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!
echo "   服务器 PID: $SERVER_PID"
echo "   正在等待服务器初始化..."
sleep 5

# ===========================================================
# 2. 启动恶意客户端 C0~C9
# ===========================================================
# GPU 分配（均匀: 每张卡 4 个客户端）:
#   GPU 0: C0~C1, C10~C11
#   GPU 1: C2~C3, C12~C13
#   GPU 2: C4~C5, C14~C15
#   GPU 3: C6~C7, C16~C17
#   GPU 4: C8~C9, C18~C19

echo "-------------------------------------------"
echo "🔴 正在启动恶意客户端 C0~C9..."

# --- 数据投毒（GPU 0）---
echo "   [C0] 恶意 (Label Flip) -> GPU 0"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=0 CLIENT_ID=0 ATTACK_TYPE=label_flip POISON_RATE=0.5 TARGET_LABEL=0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_0.log" 2>&1 &

echo "   [C1] 恶意 (Backdoor) -> GPU 0"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=0 CLIENT_ID=1 ATTACK_TYPE=backdoor POISON_RATE=0.2 TARGET_LABEL=0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_1.log" 2>&1 &

echo "   [C2] 恶意 (Clean Label) -> GPU 1"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=1 CLIENT_ID=2 ATTACK_TYPE=clean_label POISON_RATE=0.5 TARGET_LABEL=0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_2.log" 2>&1 &

echo "   [C3] 恶意 (Semantic) -> GPU 1"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=1 CLIENT_ID=3 ATTACK_TYPE=semantic POISON_RATE=0.5 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_3.log" 2>&1 &

sleep 1

# --- 模型投毒: Sign-Flip（GPU 2）---
echo "   [C4] 恶意 (Sign-Flip, scale=10) -> GPU 2"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=2 CLIENT_ID=4 ATTACK_TYPE=sign_flip SCALE_FACTOR=10.0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_4.log" 2>&1 &

echo "   [C5] 恶意 (Sign-Flip, scale=10) -> GPU 2"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=2 CLIENT_ID=5 ATTACK_TYPE=sign_flip SCALE_FACTOR=10.0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_5.log" 2>&1 &

sleep 1

# --- 模型投毒: Gradient-Scale（GPU 3）---
echo "   [C6] 恶意 (Gradient-Scale, scale=10) -> GPU 3"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=3 CLIENT_ID=6 ATTACK_TYPE=gradient_scale SCALE_FACTOR=10.0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_6.log" 2>&1 &

echo "   [C7] 恶意 (Gradient-Scale, scale=10) -> GPU 3"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=3 CLIENT_ID=7 ATTACK_TYPE=gradient_scale SCALE_FACTOR=10.0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_7.log" 2>&1 &

# --- 数据投毒补充（GPU 4）---
echo "   [C8] 恶意 (Label Flip) -> GPU 4"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=4 CLIENT_ID=8 ATTACK_TYPE=label_flip POISON_RATE=0.5 TARGET_LABEL=0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_8.log" 2>&1 &

echo "   [C9] 恶意 (Backdoor) -> GPU 4"
DATA_GROUP=iid CUDA_VISIBLE_DEVICES=4 CLIENT_ID=9 ATTACK_TYPE=backdoor POISON_RATE=0.2 TARGET_LABEL=0 \
TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
"$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_9.log" 2>&1 &

sleep 2

# ===========================================================
# 3. 启动正常客户端 C10~C19（全部 IID，DATA_GROUP=iid）
# ===========================================================
# GPU 分配（均匀延续）：
#   GPU 0: C10~C11
#   GPU 1: C12~C13
#   GPU 2: C14~C15
#   GPU 3: C16~C17
#   GPU 4: C18~C19

echo "-------------------------------------------"
echo "🟢 正在启动正常客户端 C10~C19 (全部 IID)..."

for i in {10..19}
do
    # GPU 分配: 10~11->0, 12~13->1, 14~15->2, 16~17->3, 18~19->4
    if   [ $i -le 11 ]; then GPU_ID=0
    elif [ $i -le 13 ]; then GPU_ID=1
    elif [ $i -le 15 ]; then GPU_ID=2
    elif [ $i -le 17 ]; then GPU_ID=3
    else GPU_ID=4; fi

    echo "   [C$i] 正常 (IID) -> GPU $GPU_ID"
    DATA_GROUP=iid CUDA_VISIBLE_DEVICES=$GPU_ID CLIENT_ID=$i ATTACK_TYPE=none \
    TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
    "$PYTHON_BIN" Client/client.py > "$LOG_DIR/client_$i.log" 2>&1 &

    if [ $(( (i - 9) % 4 )) -eq 0 ]; then
        sleep 1
    fi
done

echo "-------------------------------------------"
echo "✅ 所有进程已启动。"
echo "   - 跟踪服务器日志:  tail -f $LOG_DIR/server.log"
echo "   - 跟踪审计日志:    tail -f $LOG_DIR/tmaa_server_audit.log"
echo "   - 检查客户端日志:  cat $LOG_DIR/client_*.log"
echo ""
echo "按 Ctrl+C 停止所有进程。"

wait
