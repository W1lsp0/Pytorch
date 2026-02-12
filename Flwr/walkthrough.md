# Remote Deployment Walkthrough: Event-Driven Monitoring

This guide outlines how to deploy the new **Event-Driven Monitoring** architecture to your remote server.

## 1. Prerequisites (Remote Server)

Ensure the following processes are stopped on your remote server before proceeding:
-   `run_simulation.sh` (Main simulation script)
-   `dashboard.py` (Flower Dashboard)
-   `server.py` (Flower Server)

## 2. Sync Codebase

Copy the modified files from your local environment to the remote server.
Key files changed:
-   `Client/client.py` (Refactored entry point)
-   `Client/engine.py` (New: Unified Training & Evaluation logic)
-   `Client/status.py` (New: Status reporting)
-   `Client/tmaa/monitor.py` (Added GPU/Temp/Fan/Latency metrics)
-   `Client/tmaa/sidecar.py` (Trust Report v2.0)
-   `server/server.py` (Refactored entry point)
-   `server/strategy.py` (New: Federated strategy & Policy Engine)
-   `server/audit.py` (New: Audit logging)

## 3. Reset Database & Generate New Data (Virtual-Reality Alignment)

Sync the updated `Client/poison/simulator.py` and `Client/poison/generate_traces.py` to the remote server.
Then, run the generation script to create complexity-aware data pools:

**Generate Data**
```bash
# Generate data with Virtual-Reality Alignment (High/Medium/Low Complexity)
python Client/poison/generate_traces.py --devices 20 --duration 600 --clean
```

> **Verify:** The output log will now show `COMP:HIGH`, `COMP:MED`, or `COMP:LOW` for each device.
- Group A (0-9): `COMP:HIGH` (Smooth, Compute Bound)
- Group B (10-14): `COMP:MED`
- Group C (15-19): `COMP:LOW` (Jittery, IO Bound)

## 4. Run Simulation

Start the simulation as usual.

```bash
bash run_simulation.sh
```

## 5. Verification Checklist

Monitor the logs (`log/client_*.log`) and dashboard to verify:
1.  **Phase Alignment**: When a client is training (Forward/Backward), CPU/GPU usage should reflect high load.
2.  **Virtual-Reality Alignment**: 
    - **Group C (ID 15-19)** should show more volatile GPU usage (jagged waves) in Trust Reports.
    - **Group A (ID 0-9)** should show smoother GPU usage.
3.  **Full Telemetry**: Check `log/tmaa_server_audit.log`. You should see `Resources: CPU=... GPU=... Temp=...` logs.
4.  **Refactoring Check**: Ensure no `ImportError` in client or server logs.
5.  **Dashboard Status**: Clients should transition through `Waiting -> Training -> Trained/Evaluated`.

## Phase 10: Advanced Poisoning Detection (L3/L4)

**Objective**: Detect sophisticated attacks (Backdoor, Stealthy Poisoning) using multi-dimensional analysis.

### 1. Client-Side: Cluster Separability (L3)
- **Implemented in**: `Client/tmaa/inspector.py`
- **Metric**: `cluster_quality` (Intra-class Variance vs Inter-class Distance).

### 2. Server-Side: Policy Enforcement (L4)
- **Implemented in**: `server/strategy.py`
- **Checks**:
  - **Initial Loss Consistency**: Flags clients with `|loss - median| > 3 * MAD`.
  - **Layer-wise Norm Filtering**: Monitors `Classifier / Extractor` update ratio.
  - **Cosine Similarity (Sign Flip)**: Comparing client update direction with the average. Flags if `Cos(ΔW_i, ΔW_avg) < -0.5`.

## Phase 11: Deployment & Handoff

**Objective**: Deploy the simulation environment to the high-performance remote server (`frps.w1lsp0.top`).

### Remote Configuration
- **Server**: `frps.w1lsp0.top` (Port 33376)
- **Path**: `/data1/lab409/W1lsp0/Pytorch/Flwr`
- **Python**: Uses default `python` in active environment.

### How to Run on Remote Server
1. **SSH into Server**:
   ```bash
   ssh -p 33376 inpsur@frps.w1lsp0.top
   ```
2. **Navigate to Directory**:
   ```bash
   cd /data1/lab409/W1lsp0/Pytorch/Flwr
   ```
3. **Start Simulation**:
   ```bash
   # Ensure your conda environment is active (e.g. W1lsp0)
   bash run_simulation.sh
   # Script now uses 'python', so it respects your active environment
   ```
