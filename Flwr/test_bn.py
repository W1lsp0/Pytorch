import torch
import numpy as np
from torchvision.models import resnet18, ResNet18_Weights

net1 = resnet18(weights=ResNet18_Weights.DEFAULT)
net2 = resnet18(weights=ResNet18_Weights.DEFAULT)

net1.train()
net2.train()

x1 = torch.randn(32, 3, 224, 224)
x2 = torch.randn(32, 3, 224, 224) * 2.0 + 1.0

# Simulate one batch forward pass
net1(x1)
net2(x2)

w1 = [v.cpu().numpy() for k,v in net1.state_dict().items()]
w2 = [v.cpu().numpy() for k,v in net2.state_dict().items()]

# Without isolating BN
delta = [v2 - v1 for v1, v2 in zip(w1, w2)]
flat_delta = np.concatenate([x.flatten() for x in delta])
print(f"Norm with BN included: {np.linalg.norm(flat_delta)}")

w1_no_bn = [v.cpu().numpy() for k,v in net1.state_dict().items() if "running" not in k and "num_batches" not in k]
w2_no_bn = [v.cpu().numpy() for k,v in net2.state_dict().items() if "running" not in k and "num_batches" not in k]
delta_no_bn = [v2 - v1 for v1, v2 in zip(w1_no_bn, w2_no_bn)]
flat_delta_no_bn = np.concatenate([x.flatten() for x in delta_no_bn])
print(f"Norm WITHOUT BN tracked stats: {np.linalg.norm(flat_delta_no_bn)}")
