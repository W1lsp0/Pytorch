from torch.utils.data import DataLoader, Dataset
from PIL import Image
import os


class MyDataset(Dataset):
    def __init__(self, root_dir, label_dir):
        self.root_dir = root_dir
        self.label_dir = label_dir
        self.path = os.path.join(self.root_dir, self.label_dir)
        self.img_path = os.listdir(self.path)

    # 根据索引（index）读取单个样本,
    def __getitem__(self, index):
        img_name = self.img_path[index]
        img_itme_path = os.path.join(self.root_dir, self.label_dir, img_name)
        img = Image.open(img_itme_path)
        label = self.label_dir
        return img, label

    # 返回整个数据集的大小。
    def __len__(self):
        return len(self.img_path)


ants_dataset = MyDataset(root_dir='../hymenoptera_data/train', label_dir='ants')
img, label = ants_dataset[0]  # 访问第一张图片
img.show()  # 显示图片
print(label)  # 输出标签 (这里是 'ants')
