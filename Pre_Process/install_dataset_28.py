# Time：2026/10/12 18:11
import json
import os
import time
import numpy as np
import cv2
import requests
from urllib.parse import quote
from sklearn.model_selection import train_test_split

# ==================== 配置 ====================
PROXY_HTTP = "http://127.0.0.1:7897"
PROXY_HTTPS = "http://127.0.0.1:7897"
PROXIES = {"http": PROXY_HTTP, "https": PROXY_HTTPS}

SAMPLES_PER_CLASS = 5000
TARGET_SIZE = 28
SRC_SIZE = 256
LINE_THICKNESS = 1

TRAIN_RATIO, VAL_RATIO, TEST_RATIO = 0.8, 0.1, 0.1
RANDOM_SEED = 42

OUTPUT_DIR = "../quickdraw_100class"
PER_CLASS_DIR = os.path.join(OUTPUT_DIR, "per_class")
DONE_FILE = os.path.join(OUTPUT_DIR, "_done.json")
os.makedirs(PER_CLASS_DIR, exist_ok=True)

BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/"
CLASS_LIST_FILE = "random_100_categories.txt"

MAX_RETRY = 3
REQUEST_TIMEOUT = 60


# ==================== 工具 ====================
def load_class_names(path):
    with open(path, "r", encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip()]
    seen, uniq = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def load_done():
    """读取已完成类别集合。文件可能被截断，做容错。"""
    if not os.path.exists(DONE_FILE):
        return {}
    try:
        with open(DONE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print("⚠ _done.json 损坏，忽略并按空进度继续")
        return {}


def save_done(done):
    """原子写入，避免中断导致 _done.json 被写坏。"""
    tmp = DONE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DONE_FILE)


def class_filename(idx, class_name):
    safe = class_name.replace(" ", "_")
    return f"{idx:03d}_{safe}.npz"


# ==================== 渲染 ====================
def render_drawing(drawing, size=TARGET_SIZE):
    img = np.zeros((size, size), dtype=np.uint8)
    scale = size / SRC_SIZE

    for stroke in drawing:
        if not isinstance(stroke, (list, tuple)) or len(stroke) != 2:
            continue
        xs, ys = stroke
        if len(xs) == 0:
            continue

        pts = np.stack([xs, ys], axis=1).astype(np.float32)
        pts = np.round(pts * scale).astype(np.int32)
        pts[:, 0] = np.clip(pts[:, 0], 0, size - 1)
        pts[:, 1] = np.clip(pts[:, 1], 0, size - 1)

        if len(pts) == 1:
            cv2.circle(img, tuple(pts[0]), LINE_THICKNESS, 255, -1, lineType=cv2.LINE_AA)
        else:
            cv2.polylines(img, [pts], False, 255, LINE_THICKNESS, lineType=cv2.LINE_AA)

    return img


# ==================== 下载单个类别 ====================
def download_one_class(class_name, max_samples=SAMPLES_PER_CLASS):
    encoded = quote(class_name)
    url = f"{BASE_URL}{encoded}.ndjson"
    images = []

    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT, proxies=PROXIES) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not rec.get("recognized", False):
                    continue
                drawing = rec.get("drawing")
                if not drawing:
                    continue
                images.append(render_drawing(drawing))
                if len(images) >= max_samples:
                    break
    except Exception as e:
        print(f"  下载异常: {e}")
        return None

    if not images:
        print("  没有采到有效样本")
        return None

    return np.stack(images, axis=0)


def download_one_class_with_retry(class_name):
    for attempt in range(1, MAX_RETRY + 1):
        arr = download_one_class(class_name)
        if arr is not None:
            return arr
        if attempt < MAX_RETRY:
            print(f"  重试 {attempt}/{MAX_RETRY} ...")
            time.sleep(3)
    return None


# ==================== 阶段 1：按类下载 ====================
def stage_download(class_names):
    done = load_done()
    print(f"已完成: {len(done)} / {len(class_names)}")

    for idx, cls in enumerate(class_names):
        key = str(idx)
        if key in done:
            print(f"[{idx+1}/{len(class_names)}] {cls} 已存在，跳过")
            continue

        print(f"\n[{idx+1}/{len(class_names)}] 处理类别: {cls}")
        arr = download_one_class_with_retry(cls)
        if arr is None:
            print(f"  跳过 {cls}")
            continue

        fname = class_filename(idx, cls)
        fpath = os.path.join(PER_CLASS_DIR, fname)

        # 先写 tmp，再原子 rename，避免中断留下半个损坏文件
        tmp_path = fpath + ".tmp.npz"
        np.savez_compressed(tmp_path, X=arr)
        os.replace(tmp_path, fpath)

        done[key] = {"class_name": cls, "file": fname, "n": int(arr.shape[0])}
        save_done(done)
        print(f"  已保存 {fname}  ({arr.shape[0]} 张)")


# ==================== 阶段 2：合并 + 划分 + 保存最终 npz ====================
def stage_merge_and_split(class_names):
    done = load_done()
    # 按索引顺序读，保证类别顺序 = class_names 顺序
    keys = sorted(done.keys(), key=lambda x: int(x))

    X_list, y_list, kept_classes = [], [], []
    for k in keys:
        info = done[k]
        fpath = os.path.join(PER_CLASS_DIR, info["file"])
        if not os.path.exists(fpath):
            print(f"⚠ 缺少文件 {fpath}，跳过")
            continue
        with np.load(fpath) as f:
            arr = f["X"]
        X_list.append(arr)
        y_list.append(np.full(len(arr), len(kept_classes), dtype=np.int64))
        kept_classes.append(info["class_name"])

    if not X_list:
        print("没有任何类别可合并")
        return

    X = np.concatenate(X_list, axis=0)
    y = np.concatenate(y_list, axis=0)
    print(f"\n合并完成: X={X.shape}, y={y.shape}, 类别数={len(kept_classes)}")

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=(VAL_RATIO + TEST_RATIO),
        stratify=y, random_state=RANDOM_SEED,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=TEST_RATIO / (VAL_RATIO + TEST_RATIO),
        stratify=y_temp, random_state=RANDOM_SEED,
    )
    print(f"train: {X_train.shape}  val: {X_val.shape}  test: {X_test.shape}")

    npz_path = os.path.join(OUTPUT_DIR, "quickdraw_100class.npz")
    tmp_path = npz_path + ".tmp.npz"
    np.savez_compressed(
        tmp_path,
        X_train=X_train, y_train=y_train,
        X_val=X_val,     y_val=y_val,
        X_test=X_test,   y_test=y_test,
    )
    os.replace(tmp_path, npz_path)
    print(f"已保存: {npz_path}")

    with open(os.path.join(OUTPUT_DIR, "class_names.json"), "w", encoding="utf-8") as f:
        json.dump(kept_classes, f, ensure_ascii=False, indent=2)


# ==================== 入口 ====================
if __name__ == "__main__":
    class_names = load_class_names(CLASS_LIST_FILE)
    print(f"待处理类别数: {len(class_names)}")

    t0 = time.time()
    stage_download(class_names)
    stage_merge_and_split(class_names)
    print(f"\n全部完成，耗时 {time.time()-t0:.1f}s")