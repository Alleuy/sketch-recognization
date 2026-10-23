# Time: 2026/10/22
"""绘画导师 P0+P1：几何诊断 + 反事实探针（规则策略 Agent，无 LLM）。

Agent 四要素：
- 目标：让用户知道这一笔画"差在哪"，并给出可验证的修改方向
- 动作空间：放大 / 居中 / 放大并居中 / 缩小
- 策略：先看几何画像选动作，每次探针后按置信度变化决定是否继续该类动作
- 终止：命中目标类、置信度足够、连续无提升或达到最大步数
"""
import json
import math
import threading

import numpy as np

from app.config import APP_DATA_DIR
from app.ml import inference
from app.ml.preprocess import render_drawing

PROFILE_FILE = APP_DATA_DIR / "class_profiles.json"

MAX_PROBES = 3          # 最多主动实验次数
IMPROVE_EPS = 0.03      # 置信度提升低于该值视为该动作无效

_profile_lock = threading.Lock()
_profiles = None


def _load_profiles():
    """惰性加载类别几何画像（离线脚本 build_class_profiles.py 产出）。"""
    global _profiles
    if _profiles is not None:
        return _profiles
    with _profile_lock:
        if _profiles is None:
            try:
                with open(PROFILE_FILE, encoding="utf-8") as f:
                    _profiles = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                _profiles = {}
    return _profiles


# ============ 几何工具（离线/在线共用同一套定义） ============

def image_stats(img):
    """统计一张 64×64 草图的几何特征。

    返回 coverage（外接框面积占比）、ink_ratio（墨量占比）、
    offset（外接框中心到画布中心的归一化距离）、aspect（宽高比）。
    """
    size = img.shape[0]
    mask = img > 0
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return {"coverage": 0.0, "ink_ratio": 0.0, "offset": 0.0, "aspect": 1.0}

    w = (int(xs.max()) - int(xs.min()) + 1) / size
    h = (int(ys.max()) - int(ys.min()) + 1) / size
    cx = (int(xs.min()) + int(xs.max())) / 2 / size
    cy = (int(ys.min()) + int(ys.max())) / 2 / size

    return {
        "coverage": round(w * h, 4),
        "ink_ratio": round(float(mask.mean()), 4),
        "offset": round(math.hypot(cx - 0.5, cy - 0.5), 4),
        "aspect": round(w / h, 4) if h > 0 else 1.0,
    }


def _bbox(strokes):
    xs = [p[0] for s in strokes for p in s]
    ys = [p[1] for s in strokes for p in s]
    if not xs:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def _scale(strokes, factor):
    box = _bbox(strokes)
    if box is None:
        return strokes
    minx, maxx, miny, maxy = box
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    return [[[cx + (p[0] - cx) * factor, cy + (p[1] - cy) * factor] for p in s] for s in strokes]


def _move_to_center(strokes):
    box = _bbox(strokes)
    if box is None:
        return strokes
    minx, maxx, miny, maxy = box
    dx, dy = 127.5 - (minx + maxx) / 2, 127.5 - (miny + maxy) / 2
    return [[[p[0] + dx, p[1] + dy] for p in s] for s in strokes]


def _fit_inside(strokes):
    """缩放/平移后若越界，整体收回 0~255，避免边缘被裁掉。"""
    box = _bbox(strokes)
    if box is None:
        return strokes
    minx, maxx, miny, maxy = box
    dx = dy = 0.0
    if minx < 0:
        dx = -minx
    elif maxx > 255:
        dx = 255 - maxx
    if miny < 0:
        dy = -miny
    elif maxy > 255:
        dy = 255 - maxy
    if dx == 0 and dy == 0:
        return strokes
    return [[[p[0] + dx, p[1] + dy] for p in s] for s in strokes]


def _apply_action(strokes, action):
    out = strokes
    if action.get("factor"):
        out = _scale(out, action["factor"])
    if action["kind"] in ("center", "scale_center"):
        out = _move_to_center(out)
    return _fit_inside(out)


# ============ 动作规划（基于几何画像） ============

def _act(kind, factor, label):
    return {"kind": kind, "factor": factor, "label": label,
            "key": f"{kind}-{factor}"}


def _plan_actions(stats, profile):
    """根据当前图形与标准画像的差距，给出候选动作（有序）。"""
    coverage = stats["coverage"]
    offset = stats["offset"]
    med_cov = profile.get("coverage_p50")
    med_off = profile.get("offset_p50", 0.06)

    small = (med_cov is not None and coverage < med_cov * 0.8) or coverage < 0.35
    large = (med_cov is not None and coverage > med_cov * 1.35) or coverage > 0.92
    off = offset > max(0.08, med_off * 1.8)

    actions = []
    if small:
        actions.append(_act("scale_up", 1.5, "把图形放大"))
        actions.append(_act("scale_up", 1.25, "把图形稍微放大"))
    if off:
        actions.append(_act("center", None, "把图形移到画布中央"))
    if small and off:
        actions.append(_act("scale_center", 1.4, "放大并居中"))
    if large:
        actions.append(_act("scale_down", 0.75, "把图形缩小一些"))
    if not actions:
        actions.append(_act("scale_up", 1.35, "把图形放大"))
        actions.append(_act("center", None, "把图形移到画布中央"))
    return actions


def _next_action(actions, executed, failed_kinds):
    """策略：跳过已执行过的动作；某类动作被证明无效后不再重试同类。"""
    for action in actions:
        if action["key"] in executed:
            continue
        if action["kind"] in failed_kinds:
            continue
        return action
    return None


def _prob_of(classes, probs, class_name):
    if class_name in classes:
        return float(probs[classes.index(class_name)])
    return 0.0


# ============ 诊断主流程 ============

def diagnose(strokes, target_class, target_display):
    """返回结构化诊断结果，供前端卡片直接渲染。"""
    classes, probs = inference.predict_probs(strokes)
    base_conf = _prob_of(classes, probs, target_class)
    base_top1 = classes[int(probs.argmax())]

    stats = image_stats(render_drawing(strokes))
    profile = _load_profiles().get(target_class) or {}
    actions = _plan_actions(stats, profile)

    executed = set()
    failed_kinds = set()
    steps = []
    best = {"conf": base_conf, "action": None, "conf_after": base_conf,
            "top1": base_top1, "became_top1": False}
    prev_conf = base_conf
    stopped = "no_action"

    while len(steps) < MAX_PROBES:
        action = _next_action(actions, executed, failed_kinds)
        if action is None:
            stopped = "no_action"
            break

        executed.add(action["key"])
        classes2, probs2 = inference.predict_probs(_apply_action(strokes, action))
        conf2 = _prob_of(classes2, probs2, target_class)
        top1_2 = classes2[int(probs2.argmax())]

        steps.append({
            "action": action["kind"],
            "label": action["label"],
            "factor": action["factor"],
            "confidence": round(conf2, 4),
            "top1": top1_2,
        })
        if conf2 > best["conf"]:
            best = {"conf": conf2, "action": action, "conf_after": conf2,
                    "top1": top1_2, "became_top1": top1_2 == target_class}
        if top1_2 == target_class:
            stopped = "target_top1"
            break
        if conf2 - prev_conf < IMPROVE_EPS:
            failed_kinds.add(action["kind"])
        prev_conf = conf2
    else:
        stopped = "max_steps"

    return _build_result(
        target_class, target_display, stats, profile,
        base_conf, base_top1, best, steps, stopped,
    )


def _pct(value):
    return f"{round(value * 100)}%"


def _build_result(target_class, target_display, stats, profile,
                  base_conf, base_top1, best, steps, stopped):
    evidence = []
    if profile.get("coverage_p50") is not None:
        evidence.append(
            f"你的图形覆盖画布 {_pct(stats['coverage'])}，"
            f"同类标准样本中位数 {_pct(profile['coverage_p50'])}"
        )
    else:
        evidence.append(f"你的图形覆盖画布 {_pct(stats['coverage'])}")
    if stats["offset"] > 0.08:
        evidence.append(f"图形中心偏离画布中心 {_pct(stats['offset'])}")

    best_action = best["action"]
    improved = best["conf"] - base_conf >= IMPROVE_EPS

    if best["became_top1"]:
        diagnosis = f"位置和大小调整后，模型已经能识别成「{target_display}」"
        suggestions = [f"按「{best_action['label']}」的方式重画一遍即可"]
    elif improved:
        diagnosis = f"主要问题在构图：{best_action['label']}"
        suggestions = [f"{best_action['label']}，再提交一次"]
        if profile.get("coverage_p50") is not None:
            suggestions.append(f"目标是让图形覆盖画布约 {_pct(profile['coverage_p50'])}")
    elif base_conf >= 0.25:
        diagnosis = f"形状已经接近「{target_display}」，但置信度还不够"
        suggestions = ["保持现在的画法，把图形画大一点、线条连贯一些"]
    else:
        diagnosis = f"和「{target_display}」的形状差异较大，不只是大小或位置的问题"
        suggestions = ["对照参考图重画整体轮廓，先抓大形状再补细节"]

    probe = None
    if best_action is not None:
        probe = {
            "action": best_action["kind"],
            "label": best_action["label"],
            "factor": best_action["factor"],
            "before": round(base_conf, 4),
            "after": round(best["conf"], 4),
            "changed": best["conf"] - base_conf >= IMPROVE_EPS,
        }

    return {
        "diagnosis": diagnosis,
        "evidence": evidence,
        "probe": probe,
        "suggestions": suggestions,
        "stats": stats,
        "profile": profile or None,
        "target": {"class_name": target_class, "display_name": target_display},
        "agent": {
            "steps": len(steps),
            "stopped_reason": stopped,
            "tried": steps,
        },
    }
