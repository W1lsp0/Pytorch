import numpy as np

# Simulate W_old (Pretrained weights have large variance, e.g. std=0.5)
W_old = np.random.randn(1000).astype(np.float32) * 0.5

# Gradients (SGD updates are tiny, usually 0.001 * 0.1)
grad_clean = np.random.randn(1000).astype(np.float32) * 0.001
grad_atk = np.random.randn(1000).astype(np.float32) * 0.001 + 0.05

# In PyTorch, W_new = W_old - grad. Let's do this in float32 as PyTorch would.
W_new_clean = (W_old - grad_clean).astype(np.float32)
W_new_atk = (W_old - grad_atk).astype(np.float32)

# Now, Server receives W_new, and computes Delta in float64/float32
delta_clean = W_new_clean - W_old
delta_atk = W_new_atk - W_old

def cos_sim(v1, v2):
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0: return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))

print(f"Clean Grad vs Its Delta: {cos_sim(-grad_clean, delta_clean)}")
print(f"Attack Grad vs Its Delta: {cos_sim(-grad_atk, delta_atk)}")
print(f"Norm of Clean Grad: {np.linalg.norm(-grad_clean):.6f}")
print(f"Norm of Clean Delta: {np.linalg.norm(delta_clean):.6f}")
