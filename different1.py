# Time：2026/10/13 23:47
import numpy as np, json, matplotlib.pyplot as plt

data = np.load("quickdraw_100class/quickdraw_100class.npz")
X, y = data["X_train"], data["y_train"]
class_names = json.load(open("quickdraw_100class/class_names.json", encoding="utf-8"))

def show(cls, n=8):
    idx = np.where(y == class_names.index(cls))[0][:n]
    fig, axes = plt.subplots(1, n, figsize=(n*1.5, 2))
    for ax, i in zip(axes, idx):
        ax.imshow(X[i], cmap="gray"); ax.axis("off")
    fig.suptitle(cls); plt.show()

show("eyeglasses")
show("moustache")
show("shovel")
show("flamingo")