# 前端 Next.js 15 + React 19 组件化改造计划

## Context

当前 [frontend/index.html](file:///d:\Projects\sketch\frontend\index.html) 是约 900 行的单文件应用（HTML+CSS+JS），功能完整但难以维护。目标：改造为 Next.js 15 + React 19 组件化项目，**UI 与行为 1:1 复刻，不允许走样或功能丢失**。

用户已确认的决策：
- **直接替换 frontend/**（旧单文件版删除，仅存 React 版）
- **Node 服务模式**：`npm run dev` 开发 / `npm run build && npm start` 生产（不用 static export）
- JavaScript（非 TS）；**原 CSS 逐行原样迁入 globals.css**，禁用 tailwind/styled-components 重写，保证像素级一致

后端不动：`http://127.0.0.1:8000`（CORS 已放开），接口 `GET /api/levels`、`GET /api/progress`、`POST /api/predict`、`POST /api/levels/{id}/submit`、`GET /static/hints/{class}.png`。

## 一、文件树（manual scaffold，frontend/ 非空故不用 create-next-app）

```
frontend/
├── package.json              # next@^15.5, react@^19, react-dom@^19; scripts: dev/build/start; engines node>=18.18
├── next.config.mjs           # export default {}
├── jsconfig.json             # paths @/* 
├── .gitignore                # node_modules/ .next/
├── app/
│   ├── layout.js             # 服务端组件；metadata title「一起画画吧！」；<html lang="zh-CN">；viewport
│   ├── globals.css           # 原 index.html L8-399 CSS 逐行原样迁入（含全部 id/class 选择器与 @keyframes）
│   └── page.js               # 'use client'；页面壳 + 编排 + 过渡序列
├── components/
│   ├── ParticleBackground.js # canvas#particleCanvas（useParticles）
│   ├── HomePage.js           # #homePage 整块（home-card、float-bubble×2、deco-dot×3、startBtn）
│   ├── GamePage.js           # #gamePage 组装（back-btn、h1、main-wrap）
│   ├── ModePanel.js          # 三模式按钮（词语接龙 disabled + title="MVP 暂未开放，敬请期待"）
│   ├── InfoPanel.js          # .info-panel 容器（组装 4 卡）
│   ├── ModeCard.js           # modeTitle + modeHint(lid/targetZh/targetEn) + 准确度说明行
│   ├── FeedbackCard.js       # msg + Top3List
│   ├── Top3List.js           # 原 renderTop3 → JSX（内联样式逐条保留）
│   ├── ProgressCard.js       # passCount/totalLevel
│   ├── LevelList.js          # 关卡标签三态链（passed ✅ / 前沿 ▶ / locked 🔒 无 onClick）
│   ├── DrawPanel.js          # canvas 380×380 + undoBtn/clearCanvasBtn/submitBtn + Ctrl+Z 提示行
│   └── HintBox.js            # hintName + <img onError> + hintFallback（内联样式原样）
├── hooks/
│   ├── useParticles.js       # Particle 类、palette、resize 监听、rAF、cleanup
│   ├── useDrawing.js         # pointer 五事件、redraw、undo/clear、Ctrl+Z（全 ref）
│   └── useGame.js            # 关卡/进度/模式/提交/hint 状态机
└── lib/
    └── api.js                # API_BASE、FALLBACK_LEVELS、getUserId、apiFetch、normalizeStrokes
```

**硬约束：所有 id/class 名与原文件完全一致**（CSS 选择器依赖）；`<img>` 用原生标签（无 eslint 时 build 不拦截）；不建 public/（提示图全在后端）；字体系统微软雅黑无需 next/font。

## 二、状态管理

page.js ('use client') + useGame 集中持有：

| state | 位置 | 说明 |
|---|---|---|
| gameActive, levelData, progress, currentLevelId, currentMode, msg{text,cls}, top3, hint{name,className}, hintImgError | useState | progress 提交后**不可变更新**（原版原地改对象必须改写） |
| failStreak | useRef | 纯计数不驱动渲染 |
| strokes/currentStroke/drawing | useRef（useDrawing 内部） | pointermove 高频，入 state 会全树重渲染且偏离原版行为；画布重绘走命令式 redraw() |
| 过渡定时器 | useRef | 600/700/1600ms setTimeout id |
| 派生值 | 渲染期计算 | frontierId（第一个未通关）、passCount、totalLevel=`levelData.length \|\| 10`（复刻初始硬编码 10）、lv 兜底 `{id:1, display_name:"星星", class_name:"star"}`（复刻初始 modeHint 文案） |

useDrawing 返回 `{canvasRef, redraw, clear, undo, hasStrokes}`；undo 只返回结果，msg/top3 副作用由 useGame.handleUndo 做。Ctrl+Z **不加 view 守卫**（原版首页按下也触发提示）。

## 三、事件迁移要点（全部 useEffect + cleanup，StrictMode 双执行防护）

1. **pointer 五事件**挂 canvasRef：`e.preventDefault()`、setPointerCapture 存在性守卫、2px 防抖、pointerleave 结笔、`currentStroke.length>0` 才入 strokes；ctx 初始化（lineWidth 4/#fff/round）挂载 effect 一次性设置
2. **Ctrl+Z / Cmd+Z** 挂 document keydown（ctrlKey||metaKey、z、非 shift/alt、preventDefault）
3. **window resize**（粒子）+ cancelAnimationFrame 清理
4. **img.onerror → `<img onError>`**：置 hintImgError=true，每次 maybeShowHint 重置 false
5. **页面切换过渡（最大坑）**：原版返回首页流程 `display="flex"` → `opacity=0` → `void offsetWidth` 强制 reflow → `opacity=1` 重触发渐入。React 批处理会把 display+opacity 合进同一次 commit 吞掉 transition——**首页容器用 homeRef 命令式直改 style**（唯一允许绕过 state 处），gameActive 走 state 纯类切换

## 四、行为保真对照（零遗漏自查表）

- 粒子背景（90 个气泡、5 色 palette、上浮循环）→ useParticles
- 页面切换 600ms/700ms 序列 + reflow 技巧 → useGame.startGame/goHome + homeRef
- 离线降级：loadLevels catch → FALLBACK_LEVELS + msg「无法连接识别服务（请启动后端：uvicorn app.main:app --port 8000），当前仅离线浏览」；loadProgress catch 静默
- 启动 `loadLevels().then(loadProgress)` 页面加载即执行（不等点开始）
- 提交流程：空画布校验「请先在画布上绘制草图」→ challenge：成功「识别「X」成功！」+1.6s 自动跳关+hideHint，失败「识别「X」失败，你画的可能是：...」+failStreak++；≥5 → HintBox 加载 `/static/hints/{class_name}.png`，onerror → hintFallback
- practice：POST /predict 取 top5 前 3，不加分不加进度
- 模式切换：challenge 恢复进度+关卡面板；practice 隐藏双面板+清画布+hideHint；词语接龙 disabled
- 返回首页再进入**状态保留**（原版不重置）
- 文案与内联样式逐条原样（含「模式：平衡模式（top1匹配，准确度≥0.5 通过，识别不成功就画大一点）」）

## 五、实施步骤

1. **环境检查**：`node -v` ≥18.18；npm registry 可达（慢则 `--registry=https://registry.npmmirror.com`）
2. **手写脚手架**：package.json/next.config.mjs/jsconfig.json/.gitignore/app/layout.js/最小 page.js → `npm install` → `npm run dev` 验证 localhost:3000 显示文字
3. **迁 CSS**：原 L8-399 → globals.css，DevTools 对比背景渐变/布局
4. **静态组件**：ParticleBackground/HomePage/GamePage + useParticles + 过渡逻辑 → 验证粒子、进出动画、装饰气泡 floaty
5. **画布引擎**：useDrawing + DrawPanel → 验证画线/单点圆/撤销/清空/Ctrl+Z/touch 不滚动
6. **接 API**：lib/api.js + useGame + ModePanel/InfoPanel 全卡 → 后端起着联调全流程 + 停后端测离线降级
7. **删旧文件**：删除 frontend/index.html
8. **全量验收**：第五节清单逐项过（重点：初始 totalLevel=10、初始星星/star 文案、locked 无 onClick、undo 清 top3、5 次失败出图、通关链推进、状态保留、resize 自适应）
9. **生产验证**：`npm run build && npm start` 复测关键项，确认无 SSR/水合报错

## 六、风险

- SSR 水合：page.js 必须 'use client'；localStorage/crypto/window/canvas 只在 effect/事件处理器内触碰；getUserId 首调在挂载 effect 的 fetch 中，安全
- CORS：localhost:3000 → 8000，后端已放开，API_BASE 保持绝对地址原值
- StrictMode 双执行：effect 严格 cleanup；loadLevels 请求两次幂等无害；不关 StrictMode
- 版本：react/react-dom 必须 ^19 配 next@15，不可混 18

## 验证方式

后端起 `fastapi dev app\main.py`（8000），前端 `npm run dev`（3000）：浏览器按第八步验收清单全项过一遍；`npm run build && npm start` 再复测。
