"""Centralized experiment configuration for reproducible TTFL runs."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Optional

import numpy as np


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ExperimentConfig:
    total_clients: int = _env_int("TOTAL_CLIENTS", 20)
    num_rounds: int = _env_int("NUM_ROUNDS", 30)
    local_epochs: int = _env_int("LOCAL_EPOCHS", 3)
    seed: int = _env_int("EXPERIMENT_SEED", 20240925)
    shared_client_pool_size: int = _env_int("SHARED_CLIENT_POOL_SIZE", 0)
    server_proxy_size: int = _env_int("SERVER_PROXY_SIZE", 500)
    use_known_trigger_probe: bool = _env_bool("ENABLE_KNOWN_TRIGGER_PROBE", False)
    use_client_report_for_decisions: bool = _env_bool(
        "USE_CLIENT_REPORT_FOR_DECISIONS", False
    )


CONFIG = ExperimentConfig()


def seed_everything(seed: Optional[int] = None) -> int:
    """Seed Python, NumPy and Torch when available; return the applied seed."""
    applied = CONFIG.seed if seed is None else int(seed)
    random.seed(applied)
    np.random.seed(applied)
    try:
        import torch

        torch.manual_seed(applied)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(applied)
        try:
            torch.use_deterministic_algorithms(
                _env_bool("DETERMINISTIC_ALGORITHMS", False)
            )
        except (AttributeError, RuntimeError):
            pass
    except ImportError:
        pass
    return applied
