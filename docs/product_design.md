# QuickDraw 草图识别闯关系统・产品设计文档

> 
> 基于 100 类 QuickDraw 数据训练的 CNN 模型，提供网页端手绘草图识别、闯关挑战和词语接龙玩法。

## 1. 项目概述

表格

| 项目 | 内容 |
| --- | --- |
| 名称 | QuickDraw 草图识别闯关系统 |
| 定位 | 网页端手绘草图识别 + 闯关 + 词语接龙 |
| 前端 | React + Vite |
| 后端 | FastAPI (uvicorn) |
| 部署 | Nginx 反向代理 |
| 存储 | SQLite（初期）/ PostgreSQL（后期） |
| 模型 | 自训练 CNN，输入 64×64 灰度图，输出 100 类 |

## 2. 核心功能

### 2.1 闯关模式（主功能）

- 共 **100 关**，每关对应一个类别（如 `apple`、`cat`）。
- 用户在当前关卡画布上绘制草图，点击提交。
- 后端用模型识别，判定规则（可配置）：
  - **严格模式**：top1 == 目标类别 且 置信度 ≥ 0.7
  - **平衡模式（推荐）**：top1 == 目标类别 且 置信度 ≥ 0.5
  - **宽松模式**：目标类别出现在 top3 内
- 通过 → 解锁下一关，记录进度；失败 → 提示 “再试一次”，展示模型预测的 top3。
- 关卡按难度排序：简单类别（`hand`、`star`）在前，难类别（`garden hose`、`raccoon`）在后。

### 2.2 词语接龙（预留接口）

- 系统随机给出起始词（如 `elephant`），要求用户画一个以指定字母开头的词（如 `t` 开头的 `tiger`）。
- 判定规则：**top5 候选中存在以指定字母开头的类别，且置信度 ≥ 0.15** 即通过。
- 通过后，可用识别结果作为下一轮起点，形成接龙。
- 需要建立 “首字母 → 类别” 索引，确保每个字母都有足够词汇。

### 2.3 辅助功能（建议）

- **练习模式**：不计分，自由绘制，显示 top5 预测和概率。
- **排行榜**：通关数、用时、连击数。
- **错误反馈**：失败时显示模型预测的 top3。
- **中文名映射**：为 100 个类别提供中文显示名。

## 3. 系统架构

```
浏览器 (React + Vite)
   │  HTTP /api/*
   ▼ Nginx
   ├─ /          → 静态 dist 前端
   └─ /api       → 反向代理 → FastAPI (uvicorn)
                              ├─ 模型推理 (PyTorch)
                              ├─ 关卡/进度管理
                              └─ 词语接龙逻辑
                                   │
                                   ▼
                              SQLite / PostgreSQL
```

- 前端：Canvas 画板，采集笔画坐标（归一化到 0~255），提交 JSON。
- 后端：FastAPI 单进程，加载 best_model_64.pt，提供 REST API。
- 数据库：存关卡定义、用户进度、排行榜（初期可用 SQLite）。

## 4. 数据模型（简要）

### 4.1 levels

表格

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER | 主键，1~100 |
| class_name | VARCHAR | 英文类别名，如 apple |
| display_name | VARCHAR | 中文显示名，如 苹果 |
| difficulty | INTEGER | 1~5，用于关卡排序 |
| pass_threshold | FLOAT | 默认 0.5 |

### 4.2 progress

表格

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| user_id | INTEGER | 用户 ID（可选） |
| level_id | INTEGER | 关卡 ID |
| passed | BOOLEAN | 是否通过 |
| attempts | INTEGER | 尝试次数 |
| best_confidence | FLOAT | 最高置信度 |
| updated_at | DATETIME | 更新时间 |

### 4.3 users（可选）

表格

| 字段 | 类型 |
| --- | --- |
| id | INTEGER |
| username | VARCHAR |
| password_hash | VARCHAR |

### 4.4 word_chain_records

表格

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER |  |
| user_id | INTEGER |  |
| start_word | VARCHAR |  |
| required_letter | CHAR(1) |  |
| guessed_word | VARCHAR |  |
| passed | BOOLEAN |  |
| created_at | DATETIME |  |

## 5. API 设计概要

表格

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | /api/predict | 通用预测，返回 top5 类别和置信度 |
| GET | /api/levels | 获取关卡列表 |
| GET | /api/levels/{id} | 获取单关信息 |
| POST | /api/levels/{id}/submit | 提交当前关卡的笔画，判定是否通过 |
| GET | /api/progress | 获取用户进度 |
| POST | /api/word-chain/start | 开始词语接龙，返回起始词和要求字母 |
| POST | /api/word-chain/guess | 提交接龙笔画，判定是否通过 |
| POST | /api/word-chain/next | 进入下一轮接龙 |

## 6. 部署方案

### 6.1 前端

```
npm run build     # 生成 dist
```

### 6.2 后端

```
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 6.3 Nginx 关键配置

```
location / {
    root /path/to/dist;
    try_files $uri /index.html;
}

location /api {
    proxy_pass http://127.0.0.1:8000;
}
```

### 6.4 其他

模型预热：启动时用 dummy 输入跑一次，避免首次请求慢。

并发控制：推理加 threading.Lock，或只启动一个 worker。

## 7. 开发路线图

- 最小闭环
FastAPI 加载模型 + /predict
React 画板 + 提交显示结果
- 闯关模式
关卡数据、进度存储（localStorage 或 SQLite）
判定逻辑
- 词语接龙
首字母索引、判定接口、前端接龙界面
- 辅助功能
练习模式、排行榜、中文名
- 优化上线
Nginx 配置、HTTPS、模型 ONNX 加速、移动端触摸支持

## 8. 风险与注意事项

预处理必须一致：前端坐标归一化到 0~255，后端用训练时的 render_drawing () 渲染 64×64 黑底白线。

笔画抽稀：前端两点距离 < 2 像素时丢弃，避免请求过大和线条过粗。

模型并发：加锁或单 worker。

类别不均衡：某些类别准确率低，关卡难度要合理排序。

中文映射：手动维护 class_names_zh.json。

## 9. 附录：模型并发问题说明

FastAPI 本身支持异步，可以同时处理多个请求。但 PyTorch 模型是全局共享对象，多个请求同时调用 model (x) 时可能出问题：

- GPU 显存竞争：两个请求同时拷贝数据到 GPU，可能导致显存碎片或 OOM。
- CUDA 上下文冲突：PyTorch 的 CUDA 操作不是线程安全的，多线程可能报 CUDA error。
- 模型内部状态：虽然 model.eval () 下 BatchNorm 不更新 running stats，但多线程下仍可能混乱。

解决方案：

```
import threading

model_lock = threading.Lock()

@app.post("/predict")
async def predict(data: StrokeData):
    with model_lock:
        logits = model(tensor)
    ...
```

或启动时只用一个 worker：`uvicorn main:app --workers 1`