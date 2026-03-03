import numpy as np

# 1. 模拟 W_old (ResNet 某层权重)
W_old = np.random.randn(10, 10).astype(np.float32) * 0.5 

# 2. 模拟客户端训练 (W_new)
# Client 0: 标签翻转攻击者 (梯度方向被污染，稍微大一点的随机偏置)
W_new_0 = W_old + np.random.randn(10, 10).astype(np.float32) * 0.005 + 0.02
# Client 15: 正常客户端 (正常的 SGD 小碎步梯度)
W_new_15 = W_old + np.random.randn(10, 10).astype(np.float32) * 0.001
# Client 16: 正常客户端
W_new_16 = W_old + np.random.randn(10, 10).astype(np.float32) * 0.001

# ========== 错误的做法 (Flwr 原版提取绝对参数) ==========
def cos_sim(v1, v2):
    return float(np.dot(v1.flatten(), v2.flatten()) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

# 伪造全局梯度 (均值)
W_avg = (W_new_0 + W_new_15 + W_new_16) / 3

print(f"❌ 错误做法 (依赖 W) | Client 0 相似度: {cos_sim(W_new_0, W_avg):.4f}")
print(f"❌ 错误做法 (依赖 W) | Client 15 相似度: {cos_sim(W_new_15, W_avg):.4f}")

# ========== 正确的做法 (减去 W_old 提取 ΔW) ==========
delta_0 = W_new_0 - W_old
delta_15 = W_new_15 - W_old
delta_16 = W_new_16 - W_old

delta_avg = (delta_0 + delta_15 + delta_16) / 3

print(f"✅ 正确做法 (依赖 ΔW) | Client 0 相似度: {cos_sim(delta_0, delta_avg):.4f}")
print(f"✅ 正确做法 (依赖 ΔW) | Client 15 相似度: {cos_sim(delta_15, delta_avg):.4f}")
print(f"✅ 正确做法 (依赖 ΔW) | Client 16 相似度: {cos_sim(delta_16, delta_avg):.4f}")
