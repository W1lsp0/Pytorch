from PIL import Image
from torch.utils.tensorboard import SummaryWriter
from torchvision import transforms

writer = SummaryWriter("logs")

# ToTensor的使用
img = Image.open("../imgs/pytorch.jpg")
trans_totensor = transforms.ToTensor()
img_tensor = trans_totensor(img)
writer.add_image("ToTensor", img_tensor)

# 归一化Normalize的使用
# print(img_tensor[0][0][0])
trans_normalize = transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
img_normalize = trans_normalize(img_tensor)
# print(img_tensor[0][0][0])
writer.add_image("Normalize", img_normalize)

# Resize的使用
print(img.size)
trans_resize = transforms.Resize((256, 256))
# resize后还是img
img_resize = trans_resize(img)
img_resize = trans_totensor(img_resize)
writer.add_image("Resize", img_resize, 1)

# compose的使用
trans_resize_2 = transforms.Resize(512)
trans_compose = transforms.Compose([trans_resize_2, trans_totensor])
img_resize_2 = trans_compose(img)
writer.add_image("Resize", img_resize_2, 2)

# RandomCrop的使用随机裁剪
trans_RandomCrop = transforms.RandomCrop((512, 512))
trans_compose_2 = transforms.Compose([trans_RandomCrop, trans_totensor])
for i in range(10):
    img_crop = trans_compose_2(img)
    writer.add_image("Crop", img_crop, i)

writer.close()
