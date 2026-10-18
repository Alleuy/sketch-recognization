# MVP 后端设计与实施计划（含前端 demo 对接）

## Context

项目已有：训练好的 64×64 CNN 模型（`model/best_model_64.pt`，100 类，test acc \~0.89）、训练脚本（`data/train_64.py`）、数据预处理脚本（`Pre_Process/install_dataset_64.py`）、以及一个纯前端静态 demo（`frontend/index.html`，三模式均为 mock 预测）。

本次目标：交付**最小闭环 MVP** —— FastAPI 后端加载真实模型提供识别服务 + 闯关模式全套（关卡/提交判定/进度存储，匿名 UUID 用户），并把前端 demo 改造为调用真实 API。**砍掉词语接龙**（MVP 范围外，前端按钮置灰）。

已确认决策：

* MVP 范围 = 路线图 M1+M2（/predict + 闯关全套）

* 前端 demo 一并改造对接真实后端

* 用户体系 = 匿名 UUID（localStorage 生成，后端 SQLite 按此存进度）

## 关键约束（必须遵守）

1. **预处理一致性**：后端渲染必须与训练数据渲染（`Pre_Process/install_dataset_64.py` 的 `render_drawing`）完全一致：坐标 0\~255（SRC\_SIZE=256）→ 缩放到 64×64、黑底白线、`LINE_THICKNESS=2`、`cv2.LINE_AA`、`polylines`、单点用 `cv2.circle`。
2. **模型定义一致性**：`QuickDrawCNN` 必须与 `data/train_64.py` L65-116 逐层一致（checkpoint 含 `model_state` + `class_names`）。
3. **坐标转换**：前端画布 380×380，提交前需乘 `255/380` 归一化到 0\~255。
4. **并发**：推理加 `threading.Lock`，uvicorn 单 worker；路由用同步 `def`（FastAPI 自动放线程池）。
5. **AGENT.md 约定**：每步改动创建 git commit；交付前所有测试通过。

## 新增文件结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口：lifespan 中加载模型+预热+建表播种
│   ├── config.py            # MODEL_PATH / DB_URL / 阈值（环境变量可覆盖）
│   ├── database.py          # SQLAlchemy engine + SessionLocal
│   ├── models.py            # Level / Progress ORM（MVP 不含 users、word_chain_records）
│   ├── schemas.py           # Pydantic 请求/响应模型
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── model.py         # QuickDrawCNN（从 data/train_64.py 复制）
│   │   ├── preprocess.py    # render_drawing（适配 [[x,y],...] 格式）+ simplify 抽稀 + to_tensor
│   │   └── inference.py     # 全局模型句柄、load_model（含预热）、predict（带锁）
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── predict.py       # POST /api/predict
│   │   ├── levels.py        # GET /api/levels、GET /api/levels/{id}、POST /api/levels/{id}/submit
│   │   └── progress.py      # GET /api/progress（按 X-User-ID header）
│   └── data/
│       ├── class_names_zh.json    # 100 类中文显示名（实现时编写）
│       └── level_difficulty.json  # 每类难度分（由脚本生成）
├── scripts/
│   └── compute_level_difficulty.py  # 从 npz test 集每类抽样 ~200 张算 recall → 难度 1~5
├── requirements.txt
└── tests/
    ├── conftest.py          # 临时 DB fixture、TestClient fixture
    ├── test_preprocess.py
    ├── test_inference.py
    └── test_api.py
```

修改文件：`frontend/index.html`（替换 mock 为真实 API 调用）。

## 实现要点

### 1. ML 模块（后端核心）

* `app/ml/model.py`：原样复制 `data/train_64.py` 的 `QuickDrawCNN`（64/128/256 通道 VGG 风格，GAP + Linear(256→100)）。

* `app/ml/preprocess.py`：以 `install_dataset_64.py` L75-97 为基准适配输入格式——训练时 QuickDraw ndjson 是 `[[xs...],[ys...]]`，前端发送 `[[x,y],...]` 点列表。渲染参数一字不改（TARGET\_SIZE=64, SRC\_SIZE=256, LINE\_THICKNESS=2, LINE\_AA）。附 `simplify()` 后端二次抽稀（min\_dist=2）和 `to_tensor()`（`/255.0`，与训练 `QuickDrawDataset.__getitem__` L60 一致）。

* `app/ml/inference.py`：`load_model()` 读取 `model/best_model_64.pt`（默认相对路径 `../model/best_model_64.pt`，`MODEL_PATH` 可覆盖），`map_location` 自动 cuda/cpu，加载后 `eval()` + dummy `(1,1,64,64)` 预热；`predict_topk(strokes, k)` 内部 `model_lock` + `torch.no_grad()` + softmax，返回 `[(class_name, confidence), ...]`。

### 2. 数据库与播种

* `models.py`：`Level`（id/class\_name/display\_name/difficulty/pass\_threshold）与 `Progress`（user\_id 字符串主键复合、level\_id 外键、passed/attempts/best\_confidence/updated\_at），与 `docs/technical_design.md` 4.4 一致（砍掉 WordChainRecord）。

* 启动时（lifespan）自动 `Base.metadata.create_all` + 若 levels 为空则播种：

  * 类别顺序来自 checkpoint 的 `class_names`（100 个）

  * `display_name` 读 `app/data/class_names_zh.json`

  * `difficulty` 读 `app/data/level_difficulty.json`（不存在则默认 3）

  * 关卡按 difficulty 升序排列（简单在前，符合产品文档 2.1）

  * `pass_threshold` 默认 0.5（平衡模式，`PASS_THRESHOLD` 环境变量可覆盖）

* `scripts/compute_level_difficulty.py`：一次性脚本，从 `data/quickdraw_100class_64/quickdraw_100class_64.npz` 的 test 集每类抽 \~200 张，加载真实模型批量推理算每类 recall，分桶映射难度 1（recall≥0.95）\~5（recall<0.75），输出 `level_difficulty.json`。

### 3. API 设计（MVP 子集）

| 方法   | 路径                      | 请求                               | 响应                                                                                     |
| ---- | ----------------------- | -------------------------------- | -------------------------------------------------------------------------------------- |
| POST | /api/predict            | `{strokes: number[][][]}`        | `{top5: [{class_name, display_name, confidence}]}`                                     |
| GET  | /api/levels             | -                                | `[{id, class_name, display_name, difficulty, pass_threshold}]`                         |
| GET  | /api/levels/{id}        | -                                | 单关信息                                                                                   |
| POST | /api/levels/{id}/submit | `{strokes}` + header `X-User-ID` | `{passed, target_class, display_name, top3, attempts, best_confidence, next_level_id}` |
| GET  | /api/progress           | header `X-User-ID`               | `{passed_count, total, levels: [{level_id, passed, attempts, best_confidence}]}`       |

* 判定逻辑（平衡模式）：`top1.class_name == target && top1.confidence >= level.pass_threshold`。

* submit 内更新 Progress：attempts+1、passed 置位、best\_confidence 取 max。

* `X-User-ID` 缺失时使用 `"default"`（宽容处理，前端总会带）。

* CORS：`allow_origins=["*"]`（前端为静态文件直接打开，MVP 放开）。

* 输入校验：strokes 非空、坐标裁剪到 0\~255、点数上限（防超大请求）。

### 4. 前端改造（frontend/index.html）

* 新增 `API_BASE = 'http://127.0.0.1:8000/api'` 与 `getUserId()`（localStorage `qd_user_id`，无则生成 UUID v4）。

* 启动时 `fetch GET /api/levels` 替换硬编码 `levelData`（失败则回退 mock 数据并提示离线模式）。

* 提交时把 `strokes` 坐标乘 `255/380` 归一化后 POST；请求带 `X-User-ID` header。

* 闯关模式：调 `/levels/{id}/submit`，按响应更新进度/跳转下一关（用 `next_level_id`）。

* 练习模式：调 `/predict` 显示 top3（原 mockPredict 全部删除）。

* 词语接龙：按钮置灰禁用，提示"MVP 暂未开放"。

* 关卡列表渲染：按后端返回的 100 关分页/滚动展示（复用现有 level-tag 样式）。

* 错误处理：fetch 失败时在 `#msg` 显示"无法连接识别服务"。

### 5. requirements.txt

```
fastapi>=0.109
uvicorn[standard]>=0.27
sqlalchemy>=2.0
pydantic>=2.5
numpy>=1.26
opencv-python>=4.9
httpx          # TestClient 依赖
pytest
torch>=2.1     # 本机已有 2.5.1+cu121，直接复用训练环境
```

## 测试计划（AGENT.md 要求）

1. **test\_preprocess.py**：点列表格式渲染 vs `install_dataset_64.py` 原版 `[[xs],[ys]]` 渲染，同一 drawing 逐像素一致；单点 stroke 画圆；越界坐标 clip；`simplify` 抽稀正确。
2. **test\_inference.py**（模型文件存在时执行，否则 skip）：加载 `data/quickdraw_100class_64.npz` test 集抽样，直接 `to_tensor` 推理，top1 准确率 ≥ 0.8（模型 test acc 0.89 的下界保护）；topk 输出按置信度降序。
3. **test\_api.py**（TestClient + 临时 SQLite）：

   * `/api/levels` 返回 100 条且按难度升序

   * `/api/predict` 空笔画 → 422/400

   * `/api/levels/{id}/submit` 用 test 集真实样本的坐标构造 strokes（从 npz 图像反推不可行——改为用模型高置信度类别：取 test 集某类图像直接作为 tensor 不可绕过预处理 → 改用「固定一组已知可识别的合成笔画」做冒烟，重点断言判定逻辑：mock 掉 `predict_topk` 验证 passed/attempts/best\_confidence 更新与 `next_level_id`）

   * `/api/progress` 反映提交后的状态
4. **端到端验证**：启动后端 + `python -m http.server` 托管前端，浏览器打开，注入合成 strokes 点提交，确认返回真实预测（非 mock 随机值）。

## 实施步骤（每步一个 git commit）

1. backend 骨架：config/database/models/schemas + requirements.txt
2. ML 模块：model.py + preprocess.py + inference.py
3. 难度脚本 + 中文映射 + 播种逻辑 + main.py + 三个 router
4. pytest 测试三件套，全部通过
5. 前端 demo 改造对接真实 API
6. 端到端验证（后端 + 前端联调），修复问题，最终 commit

## 验证方式

```powershell
# 后端测试
cd backend && python -m pytest tests/ -v

# 启动后端
cd backend && uvicorn app.main:app --port 8000 --workers 1
# 冒烟：curl http://127.0.0.1:8000/api/levels

# 前端联调
cd frontend && python -m http.server 8080
# 浏览器打开 http://localhost:8080，绘制并提交，观察真实识别结果
```

