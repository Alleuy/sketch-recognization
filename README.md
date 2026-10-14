# 基于CNN的草图识别系统

## 1.数据集来源
### 1.1 来源

- 下载自 Google QuickDraw 官方简化版 ndjson：
  `https://storage.googleapis.com/quickdraw_dataset/full/simplified/`
- 选取 100 个类别（列表见 `random_100_categories.txt`）
- 每类采集 5000 张有效样本（`recognized=True`）

### 1.2 渲染方式

- 原始矢量坐标范围 0~255
- 直接缩放到 28×28 画布
- 线宽 `thickness=1` + 抗锯齿（`LINE_AA`）
- 单点 stroke 用 `cv2.circle` 绘制

### 1.3 划分

| 集合 | 样本数 | 占比 |
|---|---|---|
| train | 400,000 | 80% |
| val | 50,000 | 10% |
| test | 50,000 | 10% |
| **总计** | **500,000** | 100% |

- 使用 `train_test_split(stratify=y)` 保证每类比例一致
- 每类样本数完全均衡：train 4000 / val 500 / test 500

### 1.4 数据预览
待补充。

---

## 2. 模型架构

### 2.1 版本 v1（baseline）

```
Input (1×28×28)
├─ Block 1: Conv(1→32) + BN + ReLU + Conv(32→32) + BN + ReLU + MaxPool + Dropout(0.10)
├─ Block 2: Conv(32→64) + BN + ReLU + Conv(64→64) + BN + ReLU + MaxPool + Dropout(0.15)
├─ Block 3: Conv(64→128) + BN + ReLU + Conv(128→128) + BN + ReLU + Dropout(0.20)
├─ GAP (AdaptiveAvgPool2d(1))
├─ Dropout(0.40)
└─ Linear(128 → 100)
```

- **参数量**：0.30 M
- **特征图尺寸变化**：28 → 14 → 7 → 7
- **权重初始化**：Kaiming Normal

### 2.2 版本 v2（加宽版，推荐）

```
Input (1×28×28)
├─ Block 1: Conv(1→64) + BN + ReLU + Conv(64→64) + BN + ReLU + MaxPool + Dropout(0.10)
├─ Block 2: Conv(64→128) + BN + ReLU + Conv(128→128) + BN + ReLU + MaxPool + Dropout(0.15)
├─ Block 3: Conv(128→256) + BN + ReLU + Conv(256→256) + BN + ReLU + Dropout(0.20)
├─ GAP (AdaptiveAvgPool2d(1))
├─ Dropout(0.40)
└─ Linear(256 → 100)
```

- **参数量**：1.20 M
- **相对 v1 变化**：所有通道数翻倍（32/64/128 → 64/128/256）

---

## 3. 训练配置

### 3.1 通用超参

| 参数 | 值 | 说明 |
|---|---|---|
| Optimizer | AdamW | weight_decay=1e-4 |
| Batch Size | 512 | |
| Label Smoothing | 0.1 | 防止过度自信 |
| Mixed Precision | 开启 | `torch.amp.autocast` + `GradScaler` |
| Grad Clip | 5.0 | 梯度裁剪 |
| DataLoader Workers | 0 | 数据在内存中，0 最快 |

### 3.2 数据增强（GPU 上执行）

```python
v2.RandomAffine(
    degrees=10,               # ±10°
    translate=(0.08, 0.08),   # 平移 ±8%
    scale=(0.92, 1.08),       # 缩放 ±8%
    interpolation=NEAREST,
    fill=0,
)
```

- v1 中该增强在 CPU 上逐张执行，导致 GPU 利用率仅 30%
- v2 中该增强搬到 GPU 上整批执行，GPU 利用率提升到 60~80%

### 3.3 v1 训练策略

| 参数 | 值 |
|---|---|
| EPOCHS | 50 |
| Initial LR | 2e-3 |
| LR Scheduler | ReduceLROnPlateau (factor=0.5, patience=3) |
| EarlyStopping | patience=8（监控 val_acc） |
| 单 epoch 耗时 | ~19 秒（GPU 增强） |
| 总训练时间 | ~16 分钟 |

### 3.4 v2 训练策略

| 参数 | 值 |
|---|---|
| EPOCHS | 80 |
| Initial LR | 2e-3 |
| LR Scheduler | **CosineAnnealingLR** (T_max=80, eta_min=1e-5) |
| EarlyStopping | patience=15（监控 val_acc） |
| 单 epoch 耗时 | ~33.6 秒 |
| 总训练时间 | ~45 分钟 |

---

## 4. 训练结果

### 4.1 最终指标对比

| 指标 | v1 | v2 | 提升 |
|---|---|---|---|
| 参数量 | 0.30 M | 1.20 M | ×4 |
| **Test Accuracy** | **0.8402** | **0.8856** | **+4.54%** |
| Val Accuracy（最佳） | ~0.83 | ~0.887 | +5.7% |
| Train Accuracy（终末） | ~0.75 | ~0.86 | +11% |
| Test Loss | — | — | — |
| 训练时间 | ~16 分钟 | ~45 分钟 | ×2.8 |

### 4.2 v2 训练过程关键节点

| Epoch | Train Acc | Val Acc | LR |
|---|---|---|---|
| 1 | 0.4728 | 0.7288 | 2.00e-3 |
| 5 | 0.7603 | 0.8342 | 1.98e-3 |
| 10 | 0.7964 | 0.8557 | 1.92e-3 |
| 20 | ~0.82 | ~0.87 | ~1.7e-3 |
| 32 | 0.8383 | 0.8785 | 1.31e-3 |
| 40 | 0.8434 | 0.8810 | 1.00e-3 |
| 50 | 0.8496 | 0.8839 | 6.24e-4 |
| 60 | 0.8565 | 0.8854 | 3.01e-4 |
| 70 | 0.8579 | 0.8871 | 8.57e-5 |
| **77（最终）** | **0.8593** | **0.8859** | 1.69e-5 |

### 4.3 训练曲线分析

**Loss 曲线**：

- train loss 从 2.62 降到 1.34（降幅 49%）
- val loss 从 1.79 降到 1.22（降幅 32%）
- 两条线无交叉、无分叉，**无过拟合迹象**

**Accuracy 曲线**：

- 前 15 个 epoch 快速上升，之后平滑趋平
- train acc 始终低于 val acc 2.5 个点左右，是 **数据增强 + label smoothing** 的正常表现
- 曲线形态健康，收敛稳定

**Learning Rate 曲线（Cosine）**：

- lr 从 2e-3 平滑降至 1e-5，呈现标准余弦弧线
- 精修阶段（epoch 60~80）仍在缓慢提升 val acc

### 4.4 混淆矩阵

- 对角线干净，大部分类别 recall > 0.90
- 剩余错误集中在以下几类（典型 QuickDraw 难点）：
  - `animal migration`：类内画法差异极大
  - `mosquito`：画法发散
  - `tooth` / `steak`：形状相近
  - `circle` / `ellipse`：28×28 下几乎无差别
  - `eyeglasses` / `moustache`：笔画结构相近

---

## 5. 推理示例

从 test 集随机抽样 5 张，用 v2 模型推理：

| 真实类别 | Top-1 预测 | 置信度 | Top-2 |
|---|---|---|---|
| paintbrush | paintbrush | 0.964 | carrot (0.025) |
| toothbrush | toothbrush | 0.993 | garden hose (0.002) |
| eyeglasses | eyeglasses | **0.271** | moustache (0.170) |
| snail | snail | 0.956 | garden hose (0.016) |
| shovel | shovel | 0.795 | flamingo (0.067) |

**观察**：

- 5/5 全部预测正确
- 简单类别（paintbrush、toothbrush、snail）置信度 > 0.95
- 困难类别（eyeglasses、shovel）置信度偏低，反映 28×28 分辨率下这些类别信息不足

---

## 6. 复现方式

```bash
# 1. 准备数据集（28×28）
python data_prepare.py

# 2. 训练 v2 模型
python train_v2.py

# 3. 查看训练曲线和混淆矩阵
# 输出: best_model_v2.pt, training_curve_v2.png, confusion_matrix_v2.png
```

### 6.1 环境依赖

```
torch==2.5.1+cu121
torchvision==0.20.1+cu121
numpy
matplotlib
scikit-learn
```

### 6.2 推理用法

```python
import torch
from train_v2 import QuickDrawCNN

device = torch.device("cuda")
ckpt = torch.load("best_model_v2.pt", map_location=device, weights_only=False)
model = QuickDrawCNN(len(ckpt["class_names"])).to(device)
model.load_state_dict(ckpt["model_state"])
model.eval()

# img: (28,28) uint8 数组
def predict(img):
    x = torch.from_numpy(img).float().div_(255.0)[None, None].to(device)
    with torch.no_grad():
        prob = torch.softmax(model(x), dim=1)[0]
    top5 = prob.topk(5)
    return [(ckpt["class_names"][i], float(p)) for p, i in zip(top5.values, top5.indices)]
```

---

## 7. 附录

### 7.1 文件清单

| 文件 | 说明                                    |
|---|---------------------------------------|
| `best_model_v1.pt` | v1 模型（0.30 M 参数，84.02% acc），需在仓库记录中找到 |
| `best_model_v2.pt` | v2 模型（1.20 M 参数，88.56% acc）— **推荐使用** |
| `history_v2.json` | v2 训练历史（loss/acc/lr）                  |
| `training_curve_v2.png` | v2 训练曲线                               |
| `confusion_matrix_v2.png` | v2 混淆矩阵                               |
| `class_names.json` | 类别名 → 索引映射                            |

### 7.2 硬件环境

- GPU：NVIDIA GeForce RTX 4060 Laptop GPU (8 GB)
- CUDA：12.1
- PyTorch：2.5.1+cu121
- OS：Windows 11

### 7.3 时间戳

- 训练日期：2026-10-12 ~ 2026-10-13
- 报告生成：2026-10-13