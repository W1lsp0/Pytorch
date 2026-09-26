#!/usr/bin/env bash
set -Eeuo pipefail

# Sequential runner. Each run is isolated into its own result directory because
# run_simulation.sh intentionally clears source/log before starting.
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/envs/pytorch/bin/python}"
RESULT_ROOT="${RESULT_ROOT:-$ROOT_DIR/experiments/results}"
CLIENTS="${CLIENTS:-20}"
ROUNDS="${ROUNDS:-30}"
LOCAL_EPOCHS="${LOCAL_EPOCHS:-3}"
MAX_RUNS="${MAX_RUNS:-24}"
SEED_LIST="${SEED_LIST:-20240925 20240926}"
METHOD_LIST="${METHOD_LIST:-fedavg fltrust single_stream ttfl}"
SCENARIO_LIST="${SCENARIO_LIST:-none backdoor delayed_backdoor}"
PORT_BASE="${PORT_BASE:-18100}"
ATTACK_STOP_ROUND="${ATTACK_STOP_ROUND:-0}"
BACKDOOR_POISON_RATE="${BACKDOOR_POISON_RATE:-0.2}"
HEAVY_PROBE_ROTATE_MOD="${HEAVY_PROBE_ROTATE_MOD:-5}"
KNOWN_TRIGGER_PROBE="${KNOWN_TRIGGER_PROBE:-0}"

mkdir -p "$RESULT_ROOT"
run_index=0

for seed in $SEED_LIST; do
  for scenario in $SCENARIO_LIST; do
    case "$scenario" in
      none) profile=none; start=1 ;;
      backdoor) profile=backdoor; start=1 ;;
      delayed_backdoor) profile=backdoor; start=11 ;;
      *) echo "unknown scenario: $scenario" >&2; exit 2 ;;
    esac
    for method in $METHOD_LIST; do
      run_index=$((run_index + 1))
      if [ "$run_index" -gt "$MAX_RUNS" ]; then exit 0; fi
      run_id="${run_index}_${method}_${scenario}_seed${seed}"
      run_dir="$RESULT_ROOT/$run_id"
      mkdir -p "$run_dir"
      echo "[matrix] $run_id"
      (
        cd "$ROOT_DIR"
        env PYTHON_BIN="$PYTHON_BIN" TOTAL_CLIENTS="$CLIENTS" NUM_ROUNDS="$ROUNDS" \
          LOCAL_EPOCHS="$LOCAL_EPOCHS" ATTACK_PROFILE="$profile" ATTACK_START_ROUND="$start" ATTACK_STOP_ROUND="$ATTACK_STOP_ROUND" \
          BACKDOOR_POISON_RATE="$BACKDOOR_POISON_RATE" \
          AGGREGATION_MODE="$method" EXPERIMENT_SEED="$seed" USE_SIMULATION=0 \
          TTFL_DOWNLOAD_DATA=0 USE_PRETRAINED_MODEL=0 ENABLE_KNOWN_TRIGGER_PROBE="$KNOWN_TRIGGER_PROBE" \
          HEAVY_PROBE_ROTATE_MOD="$HEAVY_PROBE_ROTATE_MOD" ENABLE_PCA_PANEL=0 USE_CLIENT_REPORT_FOR_DECISIONS=0 \
          SERVER_ADDRESS="127.0.0.1:$((PORT_BASE + run_index))" \
          bash run_simulation.sh > "$run_dir/launcher.log" 2>&1
        cp log/server.log "$run_dir/server.log"
        cp log/tmaa_server_audit.log "$run_dir/tmaa_server_audit.log" 2>/dev/null || true
        cp log/round_metrics.jsonl "$run_dir/round_metrics.jsonl" 2>/dev/null || true
        "$PYTHON_BIN" experiments/analyze_run.py "$run_dir" > "$run_dir/analysis_stdout.json"
        cp log/client_*.log "$run_dir/" 2>/dev/null || true
        cat > "$run_dir/manifest.env" <<EOF
RUN_ID=$run_id
METHOD=$method
SCENARIO=$scenario
SEED=$seed
CLIENTS=$CLIENTS
ROUNDS=$ROUNDS
LOCAL_EPOCHS=$LOCAL_EPOCHS
ATTACK_START_ROUND=$start
ATTACK_STOP_ROUND=$ATTACK_STOP_ROUND
BACKDOOR_POISON_RATE=$BACKDOOR_POISON_RATE
KNOWN_TRIGGER_PROBE=$KNOWN_TRIGGER_PROBE
HEAVY_PROBE_ROTATE_MOD=$HEAVY_PROBE_ROTATE_MOD
EOF
      )
    done
  done
done
