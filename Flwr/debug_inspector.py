
import logging
import torch
import torch.nn as nn
from Client.tmaa.inspector import DataInspector

# Mock Dataloader
def mock_dataloader():
    images = torch.randn(10, 3, 32, 32)
    labels = torch.randint(0, 10, (10,))
    yield images, labels

# Mock Model
class MockNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 10, 3)
        self.fc = nn.Linear(10*30*30, 10)
        self.avgpool = nn.AdaptiveAvgPool2d(1) # For feature extraction hook

    def forward(self, x):
        x = self.conv(x)
        # x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)

def check_fixed_inspector():
    print("Testing Inspector...")
    device = torch.device("cpu")
    inspector = DataInspector(device)
    net = MockNet()
    try:
        metrics = inspector.inspect(net, mock_dataloader())
        print("Inspection Result Keys:", metrics.keys())
        if "label_distribution" in metrics:
            print("Label Distribution:", metrics["label_distribution"])
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fixed_inspector()
