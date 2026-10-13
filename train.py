# train_gpu_aug.py
import os
import sys
import json
import time
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms import v2
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix


# ==================== 配置 ====================
DATA_DIR = "quickdraw_100class"
NPZ_PATH = os.path.join(DATA_DIR, "quickdraw_100class.npz")
CLASS_JSON = os.path.join(DATA_DIR, "class_names.json")

BATCH_SIZE = 512          # GPU 上保持 512；显存宽松可上 1024
EPOCHS = 50
LR = 2e-3                 # batch 512 配 2e-3
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1

NUM_WORKERS = 0           # 数据在内存里，0 最快、最省内存
PIN_MEMORY = True
SEED = 42

PATIENCE_LR = 3
PATIENCE_STOP = 8

OUT_MODEL = "best_model.pt"
OUT_HISTORY = "history.json"
OUT_CURVE = "training_curve.png"
OUT_CM = "confusion_matrix.png"

AMP = True                # RTX 20 系及以上开；老显卡改 False


# ==================== 随机种子 ====================
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ==================== Dataset（只做最小转换，不再做增强）====================
class QuickDrawDataset(Dataset):
    """
    X: (N,28,28) uint8 [0,255]
    y: (N,)      int64
    """
    def __init__(self, X, y):
        self.X = X
        self.y = y

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        # 只做 uint8 -> float [0,1] 的形状转换，微秒级
        img = torch.from_numpy(self.X[idx]).float().div_(255.0).unsqueeze(0)
        return img, int(self.y[idx])


# ==================== 模型 ====================
class QuickDrawCNN(nn.Module):
    """3 个 block，每块两个 3x3 conv + BN + ReLU；两次 MaxPool；GAP 分类头"""
    def __init__(self, num_classes=100):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1: 28 -> 14
            nn.Conv2d(1, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.MaxPool2d(2), nn.Dropout2d(0.10),

            # Block 2: 14 -> 7
            nn.Conv2d(32, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.MaxPool2d(2), nn.Dropout2d(0.15),

            # Block 3: 保持 7x7
            nn.Conv2d(64, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True),
            nn.Dropout2d(0.20),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.40),
            nn.Linear(128, num_classes),
        )
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        return self.head(self.features(x))


# ==================== GPU 增强 ====================
def build_gpu_augment():
    """
    用 torchvision.transforms.v2，可以直接吃 GPU 上的 batch 张量。
    输入: (B,1,28,28) float [0,1] on cuda
    输出: 同形状，同设备
    """
    return v2.Compose([
        v2.RandomAffine(
            degrees=10,                          # ±10°
            translate=(0.08, 0.08),              # ±8%
            scale=(0.92, 1.08),                  # ±8%
            interpolation=v2.InterpolationMode.NEAREST,
            fill=0,
        ),
    ])


# ==================== 单 epoch 训练 ====================
def train_one_epoch(model, loader, optimizer, criterion, scaler,
                    device, use_amp, augment_gpu):
    model.train()
    total_loss, total_correct, total = 0.0, 0, 0

    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)

        # ★ 增强搬到 GPU：整批一次性做，不占 CPU
        x = augment_gpu(x)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=use_amp):
            logits = model(x)
            loss = criterion(logits, y)

        if use_amp:
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

        total_loss += loss.item() * x.size(0)
        total_correct += (logits.argmax(1) == y).sum().item()
        total += x.size(0)

    return total_loss / total, total_correct / total


# ==================== 评估 ====================
@torch.no_grad()
def evaluate(model, loader, criterion, device, use_amp):
    model.eval()
    total_loss, total_correct, total = 0.0, 0, 0

    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        with torch.amp.autocast("cuda", enabled=use_amp):
            logits = model(x)
            loss = criterion(logits, y)
        total_loss += loss.item() * x.size(0)
        total_correct += (logits.argmax(1) == y).sum().item()
        total += x.size(0)

    return total_loss / total, total_correct / total


# ==================== 主流程 ====================
def main():
    # 打印环境信息，便于排查
    print("=" * 60)
    print("Python:", sys.executable)
    print("Torch :", torch.__version__)
    print("=" * 60)

    set_seed(SEED)

    # ----- 设备 -----
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA: {torch.version.cuda}")
        torch.backends.cudnn.benchmark = True
    else:
        print("⚠️  未检测到 GPU，使用 CPU 训练会非常慢")
    use_amp = AMP and device.type == "cuda"

    # ----- 数据 -----
    print("\n加载数据...")
    data = np.load(NPZ_PATH)
    class_names = json.load(open(CLASS_JSON, encoding="utf-8"))
    K = len(class_names)

    X_train, y_train = data["X_train"], data["y_train"]
    X_val,   y_val   = data["X_val"],   data["y_val"]
    X_test,  y_test  = data["X_test"],  data["y_test"]
    print(f"类别数: {K}")
    print(f"train: {X_train.shape}  val: {X_val.shape}  test: {X_test.shape}")

    # ----- Dataset（不做 CPU 增强）-----
    train_ds = QuickDrawDataset(X_train, y_train)
    val_ds   = QuickDrawDataset(X_val,   y_val)
    test_ds  = QuickDrawDataset(X_test,  y_test)

    common = dict(num_workers=NUM_WORKERS,
                  pin_memory=(device.type == "cuda"))
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              drop_last=True, **common)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE * 2, shuffle=False, **common)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE * 2, shuffle=False, **common)

    # ----- GPU 增强 -----
    augment_gpu = build_gpu_augment()

    # ----- 模型 -----
    model = QuickDrawCNN(K).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n模型参数量: {n_params/1e6:.2f} M")
    print(f"模型设备: {next(model.parameters()).device}")

    criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR,
                                  weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5,
        patience=PATIENCE_LR, min_lr=1e-5,
    )
    scaler = torch.amp.GradScaler(device.type, enabled=use_amp)

    # ----- 训练 -----
    history = {"train_loss": [], "train_acc": [],
               "val_loss": [], "val_acc": [], "lr": []}
    best_val_acc = 0.0
    epochs_no_improve = 0

    print("\n开始训练...")
    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()
        train_loss, train_acc = train_one_epoch(
            model, train_loader, optimizer, criterion, scaler,
            device, use_amp, augment_gpu)
        val_loss, val_acc = evaluate(
            model, val_loader, criterion, device, use_amp)
        scheduler.step(val_loss)
        cur_lr = optimizer.param_groups[0]["lr"]

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["lr"].append(cur_lr)

        print(f"Epoch {epoch:2d}/{EPOCHS} | "
              f"train {train_loss:.4f}/{train_acc:.4f} | "
              f"val {val_loss:.4f}/{val_acc:.4f} | "
              f"lr {cur_lr:.2e} | {time.time()-t0:.1f}s")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "model_state": model.state_dict(),
                "epoch": epoch,
                "val_acc": val_acc,
                "class_names": class_names,
            }, OUT_MODEL)
            print(f"   ✅ best saved (val_acc={val_acc:.4f})")
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= PATIENCE_STOP:
            print(f"\nEarlyStopping 触发（连续 {PATIENCE_STOP} epoch 未提升）")
            break

    # ----- 保存 history -----
    with open(OUT_HISTORY, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    # ----- 画训练曲线 -----
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(history["train_loss"], label="train")
    axes[0].plot(history["val_loss"], label="val")
    axes[0].set_title("Loss"); axes[0].set_xlabel("epoch")
    axes[0].legend(); axes[0].grid(alpha=0.3)

    axes[1].plot(history["train_acc"], label="train")
    axes[1].plot(history["val_acc"], label="val")
    axes[1].set_title("Accuracy"); axes[1].set_xlabel("epoch")
    axes[1].legend(); axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_CURVE, dpi=120)
    print(f"\n训练曲线已保存: {OUT_CURVE}")

    # ----- 加载最佳模型评估 test -----
    print("\n加载最佳模型评估 test...")
    ckpt = torch.load(OUT_MODEL, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    test_loss, test_acc = evaluate(model, test_loader, criterion, device, use_amp)
    print(f"\n>>> Final test accuracy: {test_acc:.4f}  loss: {test_loss:.4f}")

    # ----- 混淆矩阵 -----
    print("\n计算混淆矩阵...")
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for x, y in test_loader:
            x = x.to(device, non_blocking=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                logits = model(x)
            all_preds.append(logits.argmax(1).cpu().numpy())
            all_labels.append(y.numpy())
    y_pred = np.concatenate(all_preds)
    y_true = np.concatenate(all_labels)

    cm = confusion_matrix(y_true, y_pred, normalize="true")
    diag = cm.diagonal()

    print("\n最差的 20 个类别（对角线准确率 / recall）：")
    worst_idx = np.argsort(diag)[:20]
    for i in worst_idx:
        print(f"  {class_names[i]:>22s}  {diag[i]:.3f}")

    plt.figure(figsize=(14, 12))
    plt.imshow(cm, interpolation="nearest", cmap="Blues", vmin=0, vmax=1)
    plt.colorbar()
    plt.title(f"Confusion Matrix (100 classes, test acc={test_acc:.4f})")
    plt.xlabel("predicted"); plt.ylabel("true")
    plt.tight_layout()
    plt.savefig(OUT_CM, dpi=120)
    print(f"\n混淆矩阵已保存: {OUT_CM}")
    print("全部完成。")


if __name__ == "__main__":
    main()