import torch
import numpy as np
import copy
from torchvision.models import resnet18, ResNet18_Weights

w_old = resnet18(weights=ResNet18_Weights.DEFAULT).state_dict()
w_clean = copy.deepcopy(w_old)
w_atk = copy.deepcopy(w_old)

# Simulate 3 epochs SGD with lr=0.001
for k in w_old.keys():
    if "weight" in k or "bias" in k:
        w_clean[k] = w_clean[k] + torch.randn_like(w_clean[k]) * 0.001
        w_atk[k] = w_atk[k] + torch.randn_like(w_atk[k]) * 0.001 + 0.05

flat_w_old = np.concatenate([v.cpu().numpy().flatten() for k,v in w_old.items()])
flat_w_clean = np.concatenate([v.cpu().numpy().flatten() for k,v in w_clean.items()])
flat_w_atk = np.concatenate([v.cpu().numpy().flatten() for k,v in w_atk.items()])

delta_clean = flat_w_clean - flat_w_old
delta_atk = flat_w_atk - flat_w_old
g_root = delta_clean * 0.9 + delta_atk * 0.1

def cos_sim(v1, v2):
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

print(f"Clean vs Root Delta: {cos_sim(delta_clean, g_root)}")
print(f"Attack vs Root Delta: {cos_sim(delta_atk, g_root)}")
