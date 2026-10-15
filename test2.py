# Time：2026/10/12 18:27
import numpy as np, json
import matplotlib.pyplot as plt

data = np.load("history_data/quickdraw_100class/quickdraw_100class.npz")
class_names = json.load(open("history_data/quickdraw_100class/class_names.json", encoding="utf-8"))
X_train, y_train = data["X_train"], data["y_train"]

fig, axes = plt.subplots(4, 8, figsize=(16, 8))
for ax, idx in zip(axes.flat, np.random.choice(len(X_train), 32, replace=False)):
    ax.imshow(X_train[idx], cmap="gray")
    ax.set_title(class_names[y_train[idx]], fontsize=8)
    ax.axis("off")
plt.tight_layout()
plt.show()