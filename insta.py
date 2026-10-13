# Time：2026/10/12 17:25
import json
import requests
import numpy as np
import cv2
import os
import time
from sklearn.model_selection import train_test_split

# ===================== 【配置区域，请自行修改】 =====================
# 1. 代理配置（http / socks5 二选一）
# HTTP代理示例：Clash默认 http://127.0.0.1:7890
PROXY_HTTP = "http://127.0.0.1:7897"
PROXY_HTTPS = "http://127.0.0.1:7897"


proxies = {
    "http": PROXY_HTTP,
    "https": PROXY_HTTPS,
}

# 2. 数据集参数
SAMPLES_PER_CLASS = 10000          # 每一类采集样本总数
TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1
OUTPUT_DIR = "quickdraw_100class_subset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. QuickDraw简化ndjson根地址
BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/"

# 4. 【在这里填入你的100个类别名称】
# 注意：空格换成下划线，例如 aircraft carrier → aircraft_carrier
CLASS_NAMES = [
    "cat", "dog", "bird", "apple", "banana", "airplane", "car", "fish", "flower", "house",
    "tree", "sun", "moon", "star", "cloud", "rainbow", "mountain", "river", "ocean", "beach",
    "cactus", "palm_tree", "pine_tree", "bush", "grass", "wheat", "sunflower", "rose", "tulip", "daisy",
    "butterfly", "bee", "ant", "spider", "snail", "snake", "lizard", "frog", "turtle", "rabbit",
    "horse", "cow", "pig", "sheep", "chicken", "duck", "penguin", "elephant", "lion", "tiger",
    "bear", "zebra", "giraffe", "monkey", "kangaroo", "whale", "dolphin", "octopus", "crab", "shrimp",
    "boat", "ship", "sailboat", "submarine", "bicycle", "motorcycle", "train", "truck", "bus", "road",
    "bridge", "castle", "tent", "lighthouse", "church", "skyscraper", "stove", "refrigerator", "oven", "toaster",
    "chair", "table", "bed", "sofa", "lamp", "candle", "book", "pencil", "pen", "ruler",
    "scissors", "eraser", "backpack", "handbag", "shoe", "hat", "glasses", "watch", "ring", "necklace"
]

# 渲染参数（固定，不要随便改，保证数据分布一致）
CANVAS_SIZE = 256
TARGET_SIZE = 28
LINE_THICKNESS = 2
MAX_RETRY = 3
REQUEST_TIMEOUT = 40
# ===================================================================


def render_drawing_to_28x28(drawing):
    """
    将ndjson里的drawing矢量渲染成28×28灰度图，左上角对齐
    返回 shape=(28,28) uint8，线条255，背景0
    """
    img = np.zeros((CANVAS_SIZE, CANVAS_SIZE), dtype=np.uint8)
    for stroke in drawing:
        xs, ys = stroke
        pts = np.stack([xs, ys], axis=1).astype(np.int32)
        cv2.polylines(img, [pts], isClosed=False, color=255, thickness=LINE_THICKNESS)
    img_resized = cv2.resize(img, (TARGET_SIZE, TARGET_SIZE))
    return img_resized


def process_one_class(class_name):
    url = f"{BASE_URL}{class_name}.ndjson"
    collected_samples = []
    print(f"\n===== 正在处理类别: {class_name} | 目标样本数: {SAMPLES_PER_CLASS} =====")
    try:
        resp = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            record = json.loads(line)
            # 只保留识别成功的样本
            if not record["recognized"]:
                continue
            drawing_data = record["drawing"]
            img_28 = render_drawing_to_28x28(drawing_data)
            collected_samples.append(img_28.flatten())
            # 收集够数量就停止读取流
            if len(collected_samples) >= SAMPLES_PER_CLASS:
                break
        resp.close()
    except Exception as e:
        print(f"网络/解析异常 {class_name}: {str(e)}")
        return False

    if len(collected_samples) == 0:
        print(f"{class_name}: 没有采集到有效样本！")
        return False

    data_np = np.array(collected_samples, dtype=np.uint8)
    print(f"{class_name} 采集完成，有效样本: {data_np.shape[0]}")

    # 划分 train / val / test
    X_train, X_temp = train_test_split(
        data_np,
        test_size=VAL_RATIO + TEST_RATIO,
        shuffle=True,
        random_state=42
    )
    X_val, X_test = train_test_split(
        X_temp,
        test_size=TEST_RATIO / (VAL_RATIO + TEST_RATIO),
        shuffle=True,
        random_state=42
    )

    # 保存npy文件
    np.save(os.path.join(OUTPUT_DIR, f"{class_name}_train.npy"), X_train)
    np.save(os.path.join(OUTPUT_DIR, f"{class_name}_val.npy"), X_val)
    np.save(os.path.join(OUTPUT_DIR, f"{class_name}_test.npy"), X_test)
    print(f"{class_name} 保存成功 | train:{X_train.shape}, val:{X_val.shape}, test:{X_test.shape}")
    return True


def process_one_class_with_retry(class_name):
    for attempt in range(MAX_RETRY):
        ok = process_one_class(class_name)
        if ok:
            return True
        print(f">>> 重试 {attempt+1}/{MAX_RETRY}，等待3秒...")
        time.sleep(3)
    print(f"类别 {class_name} 全部重试失败，跳过！")
    return False


if __name__ == "__main__":
    print(f"待处理类别总数：{len(CLASS_NAMES)}")
    for idx, cls_name in enumerate(CLASS_NAMES):
        print(f"\n===== 进度：{idx+1}/{len(CLASS_NAMES)} =====")
        process_one_class_with_retry(cls_name)
    print("\n✅ 全部任务执行完毕！")
