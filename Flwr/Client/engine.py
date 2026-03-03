
import torch
import torch.nn as nn
import torch.optim as optim
import time
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger("Client.Engine")

def train(
    net: nn.Module, 
    trainloader: torch.utils.data.DataLoader, 
    epochs: int, 
    device: torch.device,
    tmaa_agent: Any = None
) -> Dict[str, List[float]]:
    """
    本地模型训练函数
    Returns: history (Dict containing 'loss' and 'grad_norm' lists per epoch)
    """
    criterion = nn.CrossEntropyLoss()
    # 降低学习率至 0.001：在联邦 Non-IID 且有强力 TMAA 裁剪下，过大的 lr 会导致步长太大被不断惩罚，从而无法收敛
    optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)
    net.train()
    
    logger.info(f"    🏋️  开始本地训练 (Epochs: {epochs})...")
    
    epoch_loss_history = []
    epoch_grad_norm_history = []
    
    for epoch in range(epochs):
        running_loss = 0.0
        running_grad_norm = 0.0
        batch_count = 0
        
        # [Phase Signal] Data Loading (Start of Epoch)
        if tmaa_agent: tmaa_agent.set_phase("Loading")

        for i, (images, labels) in enumerate(trainloader):
            # [Phase Signal] Forward Pass
            # 数据已经加载完成，现在开始计算
            if tmaa_agent: tmaa_agent.set_phase("Forward")

            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = net(images)
            loss = criterion(outputs, labels)
            
            # [Phase Signal] Backward Pass
            if tmaa_agent: tmaa_agent.set_phase("Backward")
            
            loss.backward()
            
            # [New Feature] 计算梯度范数 (Monitor Gradient Norm)
            # 反映训练的"力度"和收敛趋势
            total_norm = 0.0
            for p in net.parameters():
                if p.grad is not None:
                    param_norm = p.grad.data.norm(2)
                    total_norm += param_norm.item() ** 2
            total_norm = total_norm ** 0.5
            running_grad_norm += total_norm
            
            optimizer.step()
            running_loss += loss.item()
            batch_count += 1
            
            # [Phase Signal] Batch End -> Loading next batch
            if tmaa_agent: tmaa_agent.set_phase("Loading")
        
        # [Phase Signal] Epoch End -> Idle
        if tmaa_agent: tmaa_agent.set_phase("Idle")

        # 模拟计算耗时，便于观察 Dashboard 状态变化
        time.sleep(0.1)
        avg_loss = running_loss / batch_count if batch_count > 0 else 0.0
        avg_grad = running_grad_norm / batch_count if batch_count > 0 else 0.0
        
        epoch_loss_history.append(round(avg_loss, 4))
        epoch_grad_norm_history.append(round(avg_grad, 4))
        
        logger.info(f"       Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f} | GradNorm: {avg_grad:.4f}")

    return {
        "loss": epoch_loss_history,
        "grad_norm": epoch_grad_norm_history
    }


def test(
    net: nn.Module, 
    testloader: torch.utils.data.DataLoader,
    device: torch.device
) -> Tuple[float, float]:
    """
    本地模型评估函数
    Returns: (avg_loss, accuracy)
    """
    criterion = nn.CrossEntropyLoss()
    correct, total, loss = 0, 0, 0.0
    
    net.eval()
    with torch.no_grad():
        for images, labels in testloader:
            images, labels = images.to(device), labels.to(device)
            outputs = net(images)
            loss += criterion(outputs, labels).item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
    avg_loss = loss / len(testloader.dataset) if len(testloader.dataset) else 0.0
    accuracy = correct / total if total else 0.0
    return avg_loss, accuracy
