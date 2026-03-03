import numpy as np

# Simulate W_old
W_old = np.random.randn(1000).astype(np.float32)

# Normal Client updates W towards positive gradient 
W_new_clean = W_old + np.random.randn(1000).astype(np.float32) * 0.01

# Attack Client updates W wildly (e.g. label flip or backdoor)
W_new_atk = W_old + np.random.randn(1000).astype(np.float32) * 0.05 - 0.02

# Server computes Deltas
delta_clean = W_new_clean - W_old
delta_atk = W_new_atk - W_old

# Global average as root (mix of clean and atk)
global_delta = (delta_clean * 0.9 + delta_atk * 0.1)

# Simulating Contribution Validator
def cos_sim(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

print(f"Clean vs Root: {cos_sim(delta_clean, global_delta)}")
print(f"Attack vs Root: {cos_sim(delta_atk, global_delta)}")
