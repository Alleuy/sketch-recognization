# Time：2026/10/12 19:31
import torch
print("torch 版本:", torch.__version__)
print("编译时 CUDA:", torch.version.cuda)
print("CUDA 可用:", torch.cuda.is_available())
print("设备数量:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("显卡:", torch.cuda.get_device_name(0))