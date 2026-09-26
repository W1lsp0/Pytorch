"""Protocol v2: deterministic, disjoint proxy and hybrid client partitions."""
import json
from pathlib import Path
import numpy as np


def proxy_indices(labels, size):
    labels = np.asarray(labels)
    if not 0 < size < len(labels):
        raise ValueError("proxy size must be between 1 and training size - 1")
    classes = np.unique(labels)
    selected = []
    for i, label in enumerate(classes):
        count = size // len(classes) + (i < size % len(classes))
        indices = np.flatnonzero(labels == label)
        if len(indices) < count:
            raise ValueError("not enough samples for balanced proxy")
        selected.extend(indices[:count].tolist())
    return sorted(selected)


def partition_clients(labels, clients, seed, proxy_size=500, shared_size=0):
    labels = np.asarray(labels)
    if clients < 4 or clients > 20:
        raise ValueError("hybrid protocol currently supports 4..20 clients")
    proxy = proxy_indices(labels, proxy_size)
    rng = np.random.default_rng(seed)
    available = rng.permutation(np.setdiff1d(np.arange(len(labels)), proxy))
    if not 0 <= shared_size < len(available) - 10 * clients:
        raise ValueError("invalid shared pool size")
    shared, remaining = available[:shared_size], available[shared_size:]
    a = clients // 2
    b = (clients - a) // 2
    c = clients - a - b
    pools = np.split(remaining, [len(remaining) * a // clients, len(remaining) * (a+b) // clients])
    groups = ['iid'] * a + ['moderate'] * b + ['extreme'] * c
    parts = [x.tolist() for x in np.array_split(pools[0], a)]
    for pool, count, alpha in [(pools[1], b, 1.0), (pools[2], c, 0.1)]:
        for attempt in range(1000):
            batch = [[] for _ in range(count)]
            for label in np.unique(labels):
                indices = rng.permutation(pool[labels[pool] == label])
                props = rng.dirichlet(np.repeat(alpha, count))
                props *= np.asarray([len(x) < len(pool)/count for x in batch])
                if props.sum() == 0:
                    props = np.ones(count)
                cuts = (np.cumsum(props/props.sum()) * len(indices)).astype(int)[:-1]
                for target, chunk in zip(batch, np.split(indices, cuts)):
                    target.extend(chunk.tolist())
            if min(map(len, batch)) >= 10:
                parts.extend(batch)
                break
        else:
            raise ValueError("Dirichlet partition failed after 1000 attempts")
    return proxy, [shared.tolist() + x for x in parts], groups


def save_partition(name, indices, **metadata):
    folder = Path('log/partitions')
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (name + '.json')).write_text(json.dumps(dict(indices=indices, **metadata)))
