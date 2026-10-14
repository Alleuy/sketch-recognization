# Time：2026/10/13 23:39
import torch, numpy as np, json
from train import QuickDrawCNN   # 复用类定义

device = torch.device("cuda")
ckpt = torch.load("best_model_v2.pt", map_location=device, weights_only=False)
model = QuickDrawCNN(len(ckpt["class_names"])).to(device)
model.load_state_dict(ckpt["model_state"])
model.eval()

data = np.load("quickdraw_100class/quickdraw_100class.npz")
X_test, y_test = data["X_test"], data["y_test"]

# 随机抽 5 张看看
for i in np.random.choice(len(X_test), 5, replace=False):
    x = torch.from_numpy(X_test[i]).float().div_(255.0)[None, None].to(device)
    with torch.no_grad():
        prob = torch.softmax(model(x), 1)[0]
    top3 = prob.topk(3)
    print(f"真实: {ckpt['class_names'][y_test[i]]}")
    for p, idx in zip(top3.values, top3.indices):
        print(f"  {ckpt['class_names'][idx]:>20s}  {p:.3f}")
    print()