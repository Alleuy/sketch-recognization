# 一起画画吧！—— 基于 CNN 的草图识别闯关系统

一个完整的全栈项目：用 Google QuickDraw 数据训练 CNN 手绘草图识别模型（100 类），
并以此为核心做成一个闯关小游戏——每关一个类别，玩家在画布上作画，模型实时判定是否通关。

```
浏览器（Next.js 画板）──笔画坐标──▶ FastAPI 后端 ──渲染 64×64──▶ PyTorch CNN 推理
                                       │
                                       └── SQLite（关卡 / 用户进度）
```

## 1. 功能特性

**玩法**

- **100 个关卡**：每关对应一个 QuickDraw 类别（如星星、苹果、校车），按模型识别难度从易到难排序
- **递进解锁**：已通关关卡可任意重玩，通关链最前沿的关卡可进入，其后的关卡锁定
- **平衡模式**（默认）：top1 命中目标类别且准确度 ≥ 0.5 即通关；连续 5 次未通关时，绘画区下方自动展示该类别的**参考提示图**
- **练习模式**：自由作画，返回 top5 识别结果
- 撤销上一步（按钮 / Ctrl+Z）、清空画布、粒子背景动画

**参考提示图的质量保证**（"给用户的图一定能被模型识别"）

1. 数据源背书：仅从 QuickDraw `recognized=True` 的样本中选取
2. 模型背书：只取测试集中被模型**以最高置信度正确分类**的样本生成（`backend/scripts/generate_hint_images.py`）
3. 人工抽查：`backend/scripts/hint_gallery.html` 浏览全部 100 张，不满意可 `--rank N` 换图

## 2. 项目结构

```
sketch/
├── Pre_Process/                  # 数据准备
│   ├── install_dataset_64.py     #   下载 QuickDraw ndjson → 渲染 64×64 → 合并划分
│   ├── install_dataset_28.py     #   28×28 旧版（历史）
│   └── random_100_categories.txt #   随机抽取的 100 个类别
├── data/quickdraw_100class_64/   # 数据集产物（npz + class_names.json）
├── model/best_model_64.pt        # 当前部署模型（64×64 输入）
├── history_data/                 # 28×28 旧版训练脚本与曲线（历史存档）
├── backend/                      # FastAPI 服务
│   ├── app/
│   │   ├── main.py               #   应用入口：CORS、/static 挂载、启动时建库+加载模型
│   │   ├── config.py             #   路径 / 阈值 / 输入上限（环境变量可覆盖）
│   │   ├── routers/              #   predict / levels / progress 三组路由
│   │   ├── ml/                   #   model.py(网络) inference.py(推理) preprocess.py(渲染)
│   │   ├── utils/init_db.py      #   建表 + 100 关播种（按难度升序）
│   │   └── data/                 #   class_names_zh.json / level_difficulty.json
│   ├── scripts/                  #   难度计算、参考图生成、提示图画廊
│   ├── tests/                    #   pytest：API / 推理 / 预处理
│   └── requirements.txt
└── frontend/                     # Next.js 15 + React 19（App Router，JavaScript）
    ├── app/                      #   layout / page / globals.css / icon.png
    ├── components/               #   13 个组件（含 Icons.js SVG 图标库）
    ├── hooks/                    #   useDrawing(画笔) useGame(关卡/提交) useParticles(背景)
    └── lib/api.js                #   API 封装 + 匿名用户 ID
```

## 3. 快速开始

### 3.1 后端（端口 8000）

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU 版即可，模型仅 1.2M
fastapi dev app\main.py        # 开发模式（单进程）
```

生产环境用 `fastapi run app\main.py --workers 1`（推理依赖进程内单例模型，**必须单 worker**）。

启动时自动完成：建表 → 播种 100 关（需要 `data/quickdraw_100class_64/class_names.json`）→ 加载模型并预热。

### 3.2 前端（端口 3000）

```cmd
cd frontend
npm install
npm run dev          # 开发模式
# 或生产模式：
npm run build && npm start
```

浏览器打开 http://localhost:3000 。后端已放开 CORS，前端通过本地服务访问即可。

### 3.3 生成关卡难度与参考图（可选，已预生成）

```cmd
cd backend
python -m scripts.compute_level_difficulty    # 逐类 test recall → 难度 1~5
python -m scripts.generate_hint_images        # 生成 100 张参考提示图到 backend/static/hints/
```

## 4. API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（含模型加载状态） |
| GET | `/api/levels` | 关卡列表（按难度升序，1~100） |
| GET | `/api/levels/{id}` | 单个关卡详情 |
| POST | `/api/levels/{id}/submit` | 提交笔画并判定通关，更新进度 |
| POST | `/api/predict` | 通用预测，返回 top5 类别与置信度 |
| GET | `/api/progress` | 查询当前用户闯关进度 |

- 笔画格式：`{"strokes": [[[x,y],...], ...]}`，坐标范围 0~255
- 用户身份：请求头 `X-User-ID`（前端用 localStorage 持久化的匿名 UUID）
- 提交响应包含：`passed`、`top3`、`attempts`、`best_confidence`、`next_level_id`

## 5. 数据集

- 来源：Google QuickDraw 官方简化版 ndjson
  `https://storage.googleapis.com/quickdraw_dataset/full/simplified/`
- 100 个类别 × 每类 5000 张有效样本（`recognized=True`），共 500,000 张
- 渲染：原始矢量坐标 0~255 → 直接缩放到 **64×64**，线宽 `thickness=2` + 抗锯齿（`LINE_AA`），单点 stroke 用 `cv2.circle`
- 划分：train 80% / val 10% / test 10%，`train_test_split(stratify=y)` 分层抽样，每类均衡（4000/500/500）

> 后端推理时的笔画渲染逻辑（`backend/app/ml/preprocess.py`）与训练数据生成
> （`Pre_Process/install_dataset_64.py`）逐行一致，保证训练/推理分布相同。

## 6. 模型

### 6.1 当前部署版本（64×64 输入）

```
Input (1×64×64)
├─ Block 1: Conv(1→64) + BN + ReLU + Conv(64→64) + BN + ReLU + MaxPool(→32) + Dropout2d(0.10)
├─ Block 2: Conv(64→128) + BN + ReLU + Conv(128→128) + BN + ReLU + MaxPool(→16) + Dropout2d(0.15)
├─ Block 3: Conv(128→256) + BN + ReLU + Conv(256→256) + BN + ReLU + Dropout2d(0.20)
├─ GAP (AdaptiveAvgPool2d(1)) + Dropout(0.40)
└─ Linear(256 → 100)
```

- VGG 风格小型 CNN，参数量约 **1.2 M**，CPU 推理即可
- Val Accuracy（最佳）**0.8785**（`data/history_64.json`）
- 测试集逐类 recall：均值 0.8752，范围 0.38 ~ 0.99（`backend/app/data/level_difficulty.json`）
- serving 细节：模型全局单例 + 线程锁推理，启动时用 dummy 输入预热，避免首次请求慢

### 6.2 历史版本（28×28 输入，存档于 history_data/）

| 指标 | v1 | v2 |
|---|---|---|
| 参数量 | 0.30 M | 1.20 M |
| Test Accuracy | 0.8402 | 0.8856 |

28×28 下部分类别信息不足（如 eyeglasses / circle / ellipse 几乎无差别），
因此将分辨率提升到 64×64 并重新生成数据集，即当前部署版本。旧版训练曲线与混淆矩阵见 `history_data/`。

## 7. 游戏化设计

**关卡难度**

- `backend/scripts/compute_level_difficulty.py`：测试集每类抽 200 张统计 recall，
  按下表映射难度 1~5 并写入 `level_difficulty.json`
- 首次启动播种 100 关时按难度**升序**排列（简单在前），当前分布：`1:15 / 2:36 / 3:21 / 4:20 / 5:8`

| test recall | ≥0.95 | ≥0.90 | ≥0.85 | ≥0.75 | <0.75 |
|---|---|---|---|---|---|
| 难度 | 1 | 2 | 3 | 4 | 5 |

**通关判定**（平衡模式）

```
passed = (top1 类别 == 关卡目标类别) and (top1 置信度 ≥ pass_threshold，默认 0.5)
```

每关阈值可独立覆盖（`levels.pass_threshold`，默认取环境变量 `PASS_THRESHOLD`）。
进度表记录每用户的 `attempts / best_confidence / passed`，前端进度卡实时展示。

## 8. 附录

### 8.1 关键产物

| 文件 | 说明 |
|---|---|
| `model/best_model_64.pt` | **当前部署模型**（64×64 输入，1.2 M 参数） |
| `data/history_64.json` | 64×64 版本训练历史（loss/acc/lr） |
| `data/quickdraw_100class_64/` | 数据集 npz 与类别表 |
| `backend/app/data/level_difficulty.json` | 逐类 recall 与难度映射 |
| `backend/app/data/class_names_zh.json` | 类别英文 → 中文显示名 |
| `backend/static/hints/` | 100 张关卡参考提示图 |
| `history_data/` | 28×28 旧版全部产物（存档） |

### 8.2 硬件环境

- GPU：NVIDIA GeForce RTX 4060 Laptop GPU (8 GB)（训练用，推理 CPU 即可）
- PyTorch：2.5.1+cu121（训练）/ CPU 版（部署）
- OS：Windows 11

### 8.3 时间线

- 2026-10-12 ~ 13：28×28 数据集与 v1/v2 训练
- 2026-10-14：64×64 数据集重制与模型训练
- 2026-10-15：FastAPI 后端 + 闯关系统
- 2026-10-17：前端重构为 Next.js 15 + React 19 组件化版本
- 文档更新：2026-10-18
