import flwr as fl
import torch
from torchvision.models import resnet18, ResNet18_Weights

net = resnet18(weights=ResNet18_Weights.DEFAULT)
# Simulate Client Extract
w_new = [val.cpu().numpy() for _, val in net.state_dict().items()]
flwr_params = fl.common.ndarrays_to_parameters(w_new)

# Simulate Server Extract
w_server = fl.common.parameters_to_ndarrays(flwr_params)

print(f"Shapes matched? {[v.shape for v in w_new] == [v.shape for v in w_server]}")
print(f"Norm w_new: {np.linalg.norm(np.concatenate([x.flatten() for x in w_new]))}")
print(f"Norm w_server: {np.linalg.norm(np.concatenate([x.flatten() for x in w_server]))}")
