import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt


# 搭建神经网络
class DNN(nn.Module):
    def __init__(self):
        ''' 搭建神经网络各层 '''
        super(DNN, self).__init__()
        self.net = nn.Sequential(  # 按顺序搭建各层
            nn.Linear(8, 32), nn.Sigmoid(),  # 第 1 层：全连接层
            nn.Linear(32, 8), nn.Sigmoid(),  # 第 2 层：全连接层
            nn.Linear(8, 4), nn.Sigmoid(),  # 第 3 层：全连接层
            nn.Linear(4, 1), nn.Sigmoid()  # 第 4 层：全连接层
        )

    def forward(self, x):
        ''' 前向传播 '''
        y = self.net(x)  # x 即输入数据
        return y  # y 即输出数据


model = DNN().to('cuda:0')  # 创建子类的实例，并搬到 GPU 上
# 损失函数的选择
loss_fn = nn.BCELoss(reduction='mean')
# 优化算法的选择
learning_rate = 0.005  # 设置学习率
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
# 训练网络
epochs = 5000
losses = []  # 记录损失函数变化的列表

# 准备数据集
# index_col=0: 使用第一列作为 DataFrame 的索引
df = pd.read_csv('DNN_Data.csv', index_col=0)
arr = df.values
arr = arr.astype('float32')
ts = torch.tensor(arr)
ts = ts.to('cuda')

# 划分训练集与测试集
train_size = int(len(ts) * 0.7)  # 训练集的样本数量
test_size = len(ts) - train_size  # 测试集的样本数量
# 打乱总体样本的顺序
ts = ts[torch.randperm(ts.size(0)), :]
train_Data = ts[: train_size, :]  # 训练集样本
test_Data = ts[train_size:, :]  # 测试集样本

# 给训练集划分输入与输出
X = train_Data[:, : -1]  # 前 8 列为输入特征
# 此处的.reshape((-1,1))将一阶张量升级为二阶张量 一维数组变二维
Y = train_Data[:, -1].reshape((-1, 1))  # 后 1 列为输出特征
for epoch in range(epochs):
    # 一次前向传播（批量）,模型执行前向计算，生成预测结果 Pred
    Pred = model(X)
    # 计算预测值 Pred 和真实标签 Y 之间的差异 计算损失函数
    loss = loss_fn(Pred, Y)
    # 记录损失函数的变化
    losses.append(loss.item())
    # 清理上一轮滞留的梯度，防止梯度累积，确保每次迭代都是基于当前 batch 的梯度
    optimizer.zero_grad()
    # 一次反向传播，自动计算所有参数的梯度，通过链式法则计算损失函数对每个参数的导数
    loss.backward()
    # 根据计算出的梯度更新模型参数，优化内部参数
    optimizer.step()

Fig = plt.figure()
plt.plot(range(epochs), losses)
plt.ylabel('loss')
plt.xlabel('epoch')
plt.show()

# 测试网络
# 给测试集划分输入与输出
X = test_Data[:, : -1]  # 前 8 列为输入特征
Y = test_Data[:, -1].reshape((-1, 1))  # 后 1 列为输出特征

# 退出 with 块后，梯度计算恢复正常
with torch.no_grad():  # 该局部关闭梯度计算功能
    Pred = model(X)  # 一次前向传播（批量）
    Pred[Pred >= 0.5] = 1
    Pred[Pred < 0.5] = 0
    correct = torch.sum((Pred == Y).all(1))  # 预测正确的样本
    total = Y.size(0)  # 全部的样本数量
    print(f'测试集精准度: {100 * correct / total} %')
