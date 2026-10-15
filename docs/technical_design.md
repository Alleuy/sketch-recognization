# QuickDraw 草图识别闯关系统・技术方案

> 
> 版本：v1.0
> 日期：2026-10-15
> 关联文档：《产品设计文档》

## 1. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         浏览器 (Client)                       │
│  React + Vite + Canvas 画板                                  │
│  - 采集笔画坐标 (0~255)                                       │
│  - 抽稀、序列化 JSON                                          │
│  - 调用 /api/* 接口                                           │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                         Nginx                                │
│  /          → 静态 dist (React 构建产物)                      │
│  /api       → 反向代理 → http://127.0.0.1:8000               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (uvicorn)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  模型推理     │  │  关卡/进度    │  │  词语接龙     │       │
│  │  PyTorch     │  │  SQLAlchemy  │  │  业务逻辑     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           ▼                                 │
│                    SQLite / PostgreSQL                       │
└─────────────────────────────────────────────────────────────┘
```

## 2. 技术栈

表格

| 层级 | 技术选型 | 说明 |
| --- | --- | --- |
| 前端框架 | React 18 + Vite | 快速开发，热更新 |
| 前端语言 | TypeScript | 类型安全，减少运行时错误 |
| 画板 | HTML5 Canvas 原生 API | 灵活控制笔画 |
| 状态管理 | Zustand 或 React Context | 轻量，适合中小型应用 |
| HTTP 客户端 | Axios | 拦截器、错误处理方便 |
| 后端框架 | FastAPI | 异步、自动生成 Swagger 文档 |
| 后端语言 | Python 3.10+ | 与 PyTorch 生态一致 |
| 模型 | PyTorch 2.x | 已训练好的 best_model_64.pt |
| 图像处理 | OpenCV (cv2) + NumPy | 渲染笔画为 64×64 灰度图 |
| ORM | SQLAlchemy 2.x | 支持 SQLite / PostgreSQL |
| 数据库 | SQLite（开发） / PostgreSQL（生产） | 初期零配置，后期可迁移 |
| 部署 | Nginx + uvicorn | 反向代理，静态托管 |
| 进程管理 | systemd 或 supervisor | 生产环境守护进程 |

## 3. 前端技术方案

### 3.1 项目结构

```
frontend/
├── public/
├── src/
│   ├── api/                # Axios 封装
│   │   └── client.ts
│   ├── components/
│   │   ├── CanvasBoard.tsx # 画板组件
│   │   ├── LevelCard.tsx   # 关卡卡片
│   │   └── ResultModal.tsx # 结果弹窗
│   ├── pages/
│   │   ├── Home.tsx        # 首页
│   │   ├── LevelPlay.tsx   # 闯关页面
│   │   └── WordChain.tsx   # 词语接龙
│   ├── store/
│   │   └── useGameStore.ts # Zustand 状态
│   ├── types/
│   │   └── index.ts        # TypeScript 类型定义
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### 3.2 画板组件（CanvasBoard）

核心功能：
监听 `mousedown / mousemove / mouseup` 和 `touchstart / touchmove / touchend`。

将屏幕坐标转换为 0~255 的归一化坐标：

```
const rect = canvas.getBoundingClientRect();
const x = ((e.clientX - rect.left) / rect.width) * 255;
const y = ((e.clientY - rect.top) / rect.height) * 255;
```

按笔画存储点序列：`strokes: number[][][]`，每个笔画是 `[[x, y], ...]`。
实时抽稀：当新点与上一个点的欧氏距离 < 2 时丢弃。
提供 “清空”、“撤销”、“提交” 按钮。

### 3.3 状态管理（Zustand）

```
interface GameState {
  currentLevel: number;
  levels: Level[];
  progress: Record<number, boolean>;
  strokes: number[][][];
  addStroke: (stroke: number[][]) => void;
  clearStrokes: () => void;
  submitLevel: (levelId: number) => Promise<void>;
}
```

### 3.4 API 调用

```
// api/client.ts
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export const predict = (strokes: number[][][]) =>
  api.post('/predict', { strokes });

export const submitLevel = (levelId: number, strokes: number[][][]) =>
  api.post(`/levels/${levelId}/submit`, { strokes });
```

## 4. 后端技术方案

### 4.1 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（路径、阈值等）
│   ├── database.py          # SQLAlchemy 引擎、Session
│   ├── models.py            # ORM 模型
│   ├── schemas.py           # Pydantic 请求/响应模型
│   ├── ml/
│   │   ├── model.py         # QuickDrawCNN 定义
│   │   ├── preprocess.py    # render_drawing、抽稀
│   │   └── inference.py     # 模型加载、推理、锁
│   ├── routers/
│   │   ├── predict.py       # /api/predict
│   │   ├── levels.py        # /api/levels/*
│   │   ├── progress.py      # /api/progress
│   │   └── word_chain.py    # /api/word-chain/*
│   └── utils/
│       └── init_db.py       # 初始化关卡数据
├── best_model_64.pt         # 模型权重
├── class_names.json         # 类别名（可选，模型内已存）
├── requirements.txt
└── run.py                   # 启动脚本
```

### 4.2 模型加载与预热

```
# app/ml/inference.py
import torch
import threading
from app.ml.model import QuickDrawCNN

model_lock = threading.Lock()
model = None
class_names = None
device = None

def load_model(model_path: str):
    global model, class_names, device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    class_names = ckpt["class_names"]
    model = QuickDrawCNN(len(class_names)).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    # 预热
    dummy = torch.zeros(1, 1, 64, 64).to(device)
    with torch.no_grad():
        model(dummy)
    print("✅ 模型加载并预热完成")

def predict(tensor):
    with model_lock:
        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)
    return probs
```

### 4.3 预处理（必须与训练一致）

```
# app/ml/preprocess.py
import numpy as np
import cv2

TARGET_SIZE = 64
LINE_THICKNESS = 2
SRC_SIZE = 256

def simplify(stroke, min_dist=2.0):
    if not stroke:
        return stroke
    simplified = [stroke[0]]
    for p in stroke[1:]:
        if np.hypot(p[0]-simplified[-1][0], p[1]-simplified[-1][1]) >= min_dist:
            simplified.append(p)
    return simplified

def render_drawing(strokes, size=TARGET_SIZE):
    img = np.zeros((size, size), dtype=np.uint8)
    scale = size / SRC_SIZE
    for stroke in strokes:
        stroke = simplify(stroke)
        if len(stroke) < 2:
            continue
        pts = np.array(stroke, dtype=np.float32) * scale
        pts = np.round(pts).astype(np.int32)
        pts[:, 0] = np.clip(pts[:, 0], 0, size-1)
        pts[:, 1] = np.clip(pts[:, 1], 0, size-1)
        if len(pts) == 1:
            cv2.circle(img, tuple(pts[0]), LINE_THICKNESS, 255, -1, lineType=cv2.LINE_AA)
        else:
            cv2.polylines(img, [pts], False, 255, LINE_THICKNESS, lineType=cv2.LINE_AA)
    return img

def to_tensor(img, device):
    tensor = torch.from_numpy(img).float().div_(255.0).unsqueeze(0).unsqueeze(0)
    return tensor.to(device)
```

### 4.4 数据库模型（SQLAlchemy）

```
# app/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Level(Base):
    __tablename__ = "levels"
    id = Column(Integer, primary_key=True)
    class_name = Column(String(64), nullable=False)
    display_name = Column(String(64))
    difficulty = Column(Integer, default=3)
    pass_threshold = Column(Float, default=0.5)

class Progress(Base):
    __tablename__ = "progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), default="default")
    level_id = Column(Integer, ForeignKey("levels.id"))
    passed = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    best_confidence = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WordChainRecord(Base):
    __tablename__ = "word_chain_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), default="default")
    start_word = Column(String(64))
    required_letter = Column(String(1))
    guessed_word = Column(String(64))
    passed = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 4.5 API 路由设计

#### 4.5.1 通用预测

```
POST /api/predict
Content-Type: application/json

{
  "strokes": [
    [[10, 20], [15, 25], [20, 30]],
    [[50, 60], [55, 65]]
  ]
}
```

响应：

```
{
  "top5": [
    {"class": "apple", "confidence": 0.92},
    {"class": "banana", "confidence": 0.03},
    ...
  ]
}
```

#### 4.5.2 关卡列表

```
GET /api/levels
```

响应：

```
[
  {"id": 1, "class_name": "apple", "display_name": "苹果", "difficulty": 1},
  ...
]
```

#### 4.5.3 提交关卡

```
POST /api/levels/{id}/submit
{
  "strokes": [...]
}
```

响应：

```
{
  "passed": true,
  "target_class": "apple",
  "predicted": "apple",
  "confidence": 0.87,
  "top3": [
    {"class": "apple", "confidence": 0.87},
    {"class": "pear", "confidence": 0.08},
    {"class": "orange", "confidence": 0.03}
  ]
}
```

#### 4.5.4 词语接龙

```
POST /api/word-chain/start
→ { "start_word": "elephant", "required_letter": "t" }

POST /api/word-chain/guess
{ "strokes": [...], "required_letter": "t" }
→ { "passed": true, "guessed_word": "tiger", "confidence": 0.76 }

POST /api/word-chain/next
{ "last_word": "tiger" }
→ { "start_word": "tiger", "required_letter": "r" }
```

### 4.6 并发控制

FastAPI 默认异步，但 PyTorch 推理需加锁：

```
# 全局锁，已在 inference.py 中定义
model_lock = threading.Lock()
```

启动 uvicorn 时使用单 worker：

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## 5. 部署方案

### 5.1 前端构建

```
cd frontend
npm install
npm run build      # 生成 dist/
```

### 5.2 后端启动

```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 5.3 Nginx 配置

```
server {
    listen 80;
    server_name your_domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 可选：限制请求体大小
    client_max_body_size 2M;
}
```

### 5.4 环境变量

表格

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| MODEL_PATH | 模型文件路径 | best_model_64.pt |
| DATABASE_URL | 数据库连接串 | sqlite:///./quickdraw.db |
| PASS_THRESHOLD | 通关置信度阈值 | 0.5 |

## 6. 开发与测试

### 6.1 本地开发

前端：`npm run dev`（默认 5173 端口）
后端：`uvicorn app.main:app --reload --port 8000`

前端 vite.config.ts 中配置代理：

```
server: {
  proxy: {
    '/api': 'http://127.0.0.1:8000'
  }
}
```

### 6.2 测试要点

- 预处理一致性：用训练时的 render_drawing 渲染一张图，与训练集样本对比。
- 接口测试：使用 FastAPI 自带的 /docs 或 Postman。
- 并发测试：用 ab 或 wrk 模拟 10 个并发请求，确认无 CUDA 错误。
- 前端画板：测试鼠标和触摸事件，确认坐标归一化正确。
- 关卡数据：初始化脚本生成 100 关，并手动调整难度排序。

## 7. 风险与对策

表格

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 预处理不一致 | 识别率极低 | 严格复用训练时的渲染函数，写单元测试 |
| 并发导致 CUDA 错误 | 服务崩溃 | 加 threading.Lock，单 worker |
| 笔画点过多 | 请求过大、线条过粗 | 前端抽稀，后端再次抽稀 |
| 关卡难度不合理 | 用户体验差 | 按混淆矩阵的对角线准确率排序 |
| 中文名缺失 | 显示英文，体验差 | 准备 class_names_zh.json |
| 模型文件丢失 | 服务无法启动 | 版本管理，备份 |

## 8. 里程碑

表格

| 阶段 | 内容 | 预计工时 |
| --- | --- | --- |
| M1 | 最小闭环：FastAPI /predict + React 画板 | 2 天 |
| M2 | 闯关模式：关卡数据、进度存储、判定逻辑 | 3 天 |
| M3 | 词语接龙：首字母索引、判定接口、前端界面 | 2 天 |
| M4 | 辅助功能：练习模式、排行榜、中文名 | 2 天 |
| M5 | 部署优化：Nginx、HTTPS、ONNX 加速 | 2 天 |

## 9. 附录：依赖清单

前端 package.json

```
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "@vitejs/plugin-react": "^4.2.0"
  }
}
```

后端 requirements.txt

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
torch==2.1.0
torchvision==0.16.0
numpy==1.26.0
opencv-python==4.9.0
sqlalchemy==2.0.25
pydantic==2.5.0
python-multipart==0.0.6
```