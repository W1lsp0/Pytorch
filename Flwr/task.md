# Project Tasks: TMAA Federated Learning Simulation

## Phase 1: Foundation & Basic FL [x]
- [x] Implement basic Client/Server architecture.
- [x] Implement standard FedAvg strategy with custom reporting.

## Phase 2: Security & Defenses [x]
- [x] **TMAA Sidecar (L1/L2/L4)**: System integrity, resource monitoring.
- [x] **Zero-Knowledge Inspector (L3)**: Data entropy, uniqueness, clustering.
- [x] **Advanced Security Enhancements**:
    - [x] Layer-wise Gradient Consistency (`Client/client.py`)
    - [x] Physical Throughput Hard-Limit (`sidecar.py`)
    - [x] Differential Privacy Noise (`inspector.py`)
    - [x] Policy Enforcement Engine (`server/server.py`)
    - [x] **Data Statistics** (Label Hist, Feature Summary) (`inspector.py`)
    - [x] **Training Portrait** (Loss/Grad Norm) (`client.py`)

## Phase 3: Heterogeneity & Scalability [x]
- [x] **Hybrid Data Partitioning**:
    - [x] Group A (IID): 10 Clients (Uniform)
    - [x] Group B (Moderate): 5 Clients (Dirichlet $\alpha=1.0$)
    - [x] Group C (Extreme): 5 Clients (Dirichlet $\alpha=0.1$)
- [x] **Simulation Optimization**:
    - [x] Scale to 20 Clients.
    - [x] Optimize GPU allocation (4 Clients/GPU).
    - [x] Update `dashboard.py` for 20-client monitoring.

## Phase 4: Logging & Observability [x]
- [x] **Server-side Logging**:
    - [x] Log Data Fingerprints (Dist/Feat) in `server.log`.
    - [x] **Isolated Client 0 Audit**: Generate `client_0_audit.jsonl` containing full round history.

## Phase 5: Refactoring: Event-Driven Monitoring [x]
- [x] **Simulator**: Generate telemetry "pools" by Phase (Idle/Loading/Forward/Backward).
- [x] **DB Manager**: Add `fetch_telemetry_by_phase` support.
- [x] **Client**: Emit Phase Signals (`batch_start`, `forward_end`, `backward_end`).
- [x] **Monitor (TMAA)**: Implement Event Listening & Phase-based Fetching.

## Phase 6: Full Telemetry Expansion [x]
- [x] **Monitor**: 扩展 `metrics_history` 收集 GPU/内存/温度/风扇/延迟全维度数据
- [x] **Sidecar**: Trust Report v2.0 包含全维度波动率 + 资源摘要
- [x] **Server**: PolicyMatcher 增加 GPU 行为异常检测 + 审计日志记录资源摘要

## Phase 7: Server Refactoring [x]
- [x] **Extract Strategy & Policy**: Move `TMAA_FedAvg` and `PolicyMatcher` to `server/strategy.py`.
- [x] **Extract Auditing**: Move logging logic to `server/audit.py`.
- [x] **Clean Server Entry**: Simplify `server/server.py` to main entry point.

## Phase 8: Client Refactoring [x]
- [x] **Extract Engine**: Move `train()` and `test()` logic to `Client/engine.py`.
- [x] **Extract Status Reporter**: Move `update_status_monitor` to `Client/status.py`.
- [x] **Clean Client Entry**: Simplify `Client/client.py`.

## Phase 9: Virtual-Reality Alignment [x]
- [x] **Data Complexity Logic**: Pass `data_complexity` (High/Low) to Simulator.
- [x] **Adaptive Simulation**:
    - [x] **Speed Factor**: Low complexity -> Faster processing (shorter phase duration).
    - [x] **Volatility Factor**: Low complexity -> Higher jitter (IO bound simulation).
- [x] **Document Simulation Data**: Analyze and document current simulation data scale.

## Phase 10: Advanced Poisoning Detection (L3/L4) [x]
- [x] **Client-Side (L3)**: Implement Cluster Separability metrics in `inspector.py`.
- [x] **Server-Side (L4)**: Implement Initial Loss Consistency Check in `strategy.py`.
- [x] **Server-Side (L4)**: Implement Layer-wise Norm Filtering in `strategy.py`.
- [x] **Server-Side (L4)**: Implement Cosine Similarity Check (Sign Flipping) in `strategy.py`.

## Phase 11: Deployment [x]
- [x] **Remote Setup**: Initialized git repo on `frps.w1lsp0.top`.
- [x] **Configuration**: Updated `run_simulation.sh` to use remote Python environment (`/data1/anaconda3/envs/W1lsp0/bin/python`).
- [x] **Code Sync**: Pushed latest code to remote master branch.

## Next Steps [ ]
- [ ] Monitor long-term performance stability on remote server.
