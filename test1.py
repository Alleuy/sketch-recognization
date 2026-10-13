# Time：2026/10/12 18:26
import numpy as np, json

data = np.load("quickdraw_100class/quickdraw_100class.npz")
class_names = json.load(open("quickdraw_100class/class_names.json", encoding="utf-8"))

X_train, y_train = data["X_train"], data["y_train"]
X_val,   y_val   = data["X_val"],   data["y_val"]
X_test,  y_test  = data["X_test"],  data["y_test"]

K = len(class_names)
print(f"类别数: {K}")
print(f"train: {X_train.shape}  val: {X_val.shape}  test: {X_test.shape}")
print(f"dtype: {X_train.dtype}  min/max: {X_train.min()}/{X_train.max()}")
print(f"标签范围: {y_train.min()} ~ {y_train.max()}")

# 每类样本数是否均衡
for name, y_ in [("train", y_train), ("val", y_val), ("test", y_test)]:
    c = np.bincount(y_, minlength=K)
    print(f"{name}: min={c.min()} max={c.max()} mean={c.mean():.0f}")