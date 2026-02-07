#!/bin/bash
set -e

# ================= Configuration =================
SERVER_ADDRESS="0.0.0.0:8080"
TOTAL_CLIENTS=10
USE_SIMULATION=1  # Enable DB-based L4 monitoring

# Ensure we are in the right directory
cd /root/code/Pytorch/Flwr

# Clean up previous logs
rm -f server.log tmaa_server_audit.log client_*.log

echo "🚀 Starting Simulation..."
echo "   - Server: 1"
echo "   - Clients: 10 (4 Bad, 6 Good)"
echo "   - Mode: Real Execution + Simulated L4 Monitor"

# 1. Start Server
echo "-------------------------------------------"
echo "🔵 Launching Server..."
conda run -n pytorch python server/server.py > server.log 2>&1 &
SERVER_PID=$!
echo "   Server PID: $SERVER_PID"
echo "   Waiting for server to initialize..."
sleep 5

# 2. Start Malicious Clients (4 Nodes)
echo "-------------------------------------------"
echo "🔴 Launching Malicious Clients..."

# Client 0: Label Flip
echo "   [C0] Malicious: Label Flip"
CLIENT_ID=0 ATTACK_TYPE=label_flip POISON_RATE=0.5 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
conda run -n pytorch python Client/client.py > client_0.log 2>&1 &

# Client 1: Backdoor
echo "   [C1] Malicious: Backdoor"
CLIENT_ID=1 ATTACK_TYPE=backdoor POISON_RATE=0.2 TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
conda run -n pytorch python Client/client.py > client_1.log 2>&1 &

# Client 2: Clean Label
echo "   [C2] Malicious: Clean Label"
CLIENT_ID=2 ATTACK_TYPE=clean_label POISON_RATE=0.5 TARGET_LABEL=0 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
conda run -n pytorch python Client/client.py > client_2.log 2>&1 &

# Client 3: Semantic
echo "   [C3] Malicious: Semantic"
CLIENT_ID=3 ATTACK_TYPE=semantic POISON_RATE=0.5 TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
conda run -n pytorch python Client/client.py > client_3.log 2>&1 &

sleep 2

# 3. Start Honest Clients (6 Nodes)
echo "-------------------------------------------"
echo "🟢 Launching Honest Clients (C4 - C9)..."

for i in {4..9}
do
   echo "   [C$i] Honest Node"
   CLIENT_ID=$i ATTACK_TYPE=none TOTAL_CLIENTS=$TOTAL_CLIENTS USE_SIMULATION=$USE_SIMULATION \
   conda run -n pytorch python Client/client.py > client_$i.log 2>&1 &
done

echo "-------------------------------------------"
echo "✅ All processes launched."
echo "   - Tail server log:  tail -f server.log"
echo "   - Tail audit log:   tail -f tmaa_server_audit.log"
echo "   - Check client logs: cat client_*.log"
echo ""
echo "Press Ctrl+C to stop all processes."

# Wait for all background processes
wait
