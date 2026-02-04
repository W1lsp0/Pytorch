from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os

from torch.utils.tensorboard import SummaryWriter
from torchvision import transforms
import cv2

# Transform如何使用
# 为什么需要transform.Totensor
img_path = "/home/data/lab08/W1lsp0/pytorchTrain/pytorch-tutorial/hymenoptera_data/train/ants/45472593_bfd624f8dc.jpg"
img = Image.open(img_path)

cv_img = cv2.imread(img_path)

writer = SummaryWriter("./logs")
tenso_trans = transforms.ToTensor()
tensor_img = tenso_trans(img)
writer.add_image("tenso_img", tensor_img)

writer.close()
