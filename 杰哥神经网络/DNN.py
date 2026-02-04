import torch
import torch.nn as nn
import matplotlib.pyplot as plt
# 展示高清图
from matplotlib_inline import backend_inline


class DNN(nn.Module):
    def __init__(self):
        ''' 搭建神经网络各层 '''
        super(DNN, self).__init__()
        self.net = nn.Sequential(  # 按顺序搭建各层
            nn.Linear(3, 5), nn.ReLU(),  # 第 1 层：全连接层
            nn.Linear(5, 5), nn.ReLU(),  # 第 2 层：全连接层
            nn.Linear(5, 5), nn.ReLU(),  # 第 3 层：全连接层
            nn.Linear(5, 3)  # 第 4 层：全连接层
        )

    def forward(self, x):
        ''' 前向传播 '''
        y = self.net(x)  # x 即输入数据
        return y  # y 即输出数据


backend_inline.set_matplotlib_formats('svg')

# 生成数据集
X1 = torch.rand(10000, 1)  # 输入特征 1
X2 = torch.rand(10000, 1)  # 输入特征 2
X3 = torch.rand(10000, 1)  # 输入特征 3
Y1 = ((X1 + X2 + X3) < 1).float()  # 输出特征 1
Y2 = ((1 < (X1 + X2 + X3)) & ((X1 + X2 + X3) < 2)).float()  # 输出特征 2
Y3 = ((X1 + X2 + X3) > 2).float()  # 输出特征 3
Data = torch.cat([X1, X2, X3, Y1, Y2, Y3], axis=1)  # 整合数据集
Data = Data.to('cuda:0')  # 把数据集搬到 GPU 上

# 划分训练集与测试集
train_size = int(len(Data) * 0.7)  # 训练集的样本数量
test_size = len(Data) - train_size  # 测试集的样本数量
Data = Data[torch.randperm(Data.size(0)), :]  # 打乱样本的顺序
train_Data = Data[: train_size, :]  # 训练集样本
test_Data = Data[train_size:, :]  # 测试集样本
print(train_Data.shape, test_Data.shape)

model = DNN().to('cuda:0')

# 查看内部参数（非必要）
# for name, param in model.named_parameters():
#     print(f"参数:{name}\n 形状:{param.shape}\n 数值:{param}\n")

# 损失函数的选择
loss_fn = nn.MSELoss()

# 优化算法的选择
learning_rate = 0.01  # 设置学习率
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)

# 训练网络
epochs = 1000
losses = []  # 记录损失函数变化的列表
# 给训练集划分输入与输出
X = train_Data[:, :3]  # 前 3 列为输入特征
Y = train_Data[:, -3:]  # 后 3 列为输出特征
for epoch in range(epochs):
    Pred = model(X)  # 一次前向传播（批量）
    loss = loss_fn(Pred, Y)  # 计算损失函数
    losses.append(loss.item())  # 记录损失函数的变化
    optimizer.zero_grad()  # 清理上一轮滞留的梯度
    loss.backward()  # 一次反向传播
    optimizer.step()  # 优化内部参数

Fig = plt.figure()
plt.plot(range(epochs), losses)
plt.ylabel('loss'), plt.xlabel('epoch')
plt.show()

# 测试网络
# 给测试集划分输入与输出
X = test_Data[:, :3]  # 前 3 列为输入特征
Y = test_Data[:, -3:]  # 后 3 列为输出特征
with torch.no_grad():  # 该局部关闭梯度计算功能
    Pred = model(X)  # 一次前向传播（批量）
    Pred[:, torch.argmax(Pred, axis=1)] = 1
    Pred[Pred != 1] = 0
    correct = torch.sum((Pred == Y).all(1))  # 预测正确的样本
    total = Y.size(0)  # 全部的样本数量
    print(f'测试集精准度: {100 * correct / total} %')

# 保存网络
torch.save(model, 'model.pth')

# 把模型赋给新网络
new_model = torch.load('model.pth')

# 测试网络
# 给测试集划分输入与输出
X = test_Data[:, :3]  # 前 3 列为输入特征
Y = test_Data[:, -3:]  # 后 3 列为输出特征
with torch.no_grad():  # 该局部关闭梯度计算功能
    Pred = new_model(X)  # 用新模型进行一次前向传播
    Pred[:, torch.argmax(Pred, axis=1)] = 1
    Pred[Pred != 1] = 0
    correct = torch.sum((Pred == Y).all(1))  # 预测正确的样本
    total = Y.size(0)  # 全部的样本数量
    print(f'测试集精准度: {100 * correct / total} %')
