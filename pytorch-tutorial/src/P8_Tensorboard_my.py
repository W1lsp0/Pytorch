from torch.utils.tensorboard import SummaryWriter
import numpy as np
from PIL import Image
import cv2

writer = SummaryWriter("logs")
image_path = "../hymenoptera_data/train/ants/6240329_72c01e663e.jpg"

# 图片转换为numpy，或者tensor型
img_PIL = Image.open(image_path)
img_array = np.array(img_PIL)
print("img_array: ", type(img_array))
print("img_array.shape: ", img_array.shape)
writer.add_image("train", img_array, 1, dataformats='HWC')

# y = 2x
for i in range(100):
    writer.add_scalar("y=x", i, i)

writer.close()
