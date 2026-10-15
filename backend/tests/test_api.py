# Time: 2026/10/15
# API 集成测试：TestClient + 临时 SQLite；判定逻辑用 mock 验证，predict 做真实冒烟。
import uuid

import pytest

from app.ml import inference

USER = f"test-{uuid.uuid4().hex[:8]}"

# 一组近似"星星/形状"的合成笔画
STROKES = [
    [[128, 30], [160, 90], [128, 150], [96, 90], [128, 30]],
    [[100, 100], [156, 100], [100, 140], [156, 140]],
]


class TestHealthAndLevels:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_levels_list(self, client):
        r = client.get("/api/levels")
        assert r.status_code == 200
        levels = r.json()["levels"]
        assert len(levels) == 100
        assert [l["id"] for l in levels] == list(range(1, 101))
        # 按难度升序（简单在前）
        difficulties = [l["difficulty"] for l in levels]
        assert difficulties == sorted(difficulties)
        # 必备字段
        for l in levels[:3]:
            assert l["class_name"] and l["display_name"]
            assert 0 < l["pass_threshold"] < 1

    def test_get_level(self, client):
        r = client.get("/api/levels/1")
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_get_level_404(self, client):
        assert client.get("/api/levels/999").status_code == 404


class TestPredict:
    def test_empty_strokes_rejected(self, client):
        r = client.post("/api/predict", json={"strokes": []})
        assert r.status_code == 422

    def test_real_predict_smoke(self, client):
        if not inference.is_loaded():
            pytest.skip("模型未加载，跳过真实推理冒烟")
        r = client.post("/api/predict", json={"strokes": STROKES})
        assert r.status_code == 200
        top5 = r.json()["top5"]
        assert len(top5) == 5
        confs = [x["confidence"] for x in top5]
        assert confs == sorted(confs, reverse=True)


class TestSubmitAndProgress:
    def test_submit_pass_and_progress(self, client, monkeypatch):
        # mock 推理：top1 命中第 1 关且置信度 0.9
        target = client.get("/api/levels/1").json()["class_name"]
        fake = [
            (target, "目标", 0.9),
            ("other-a", "甲", 0.05),
            ("other-b", "乙", 0.03),
            ("other-c", "丙", 0.01),
            ("other-d", "丁", 0.005),
        ]
        monkeypatch.setattr(inference, "predict_topk", lambda s, k=5: fake[:k])

        r = client.post("/api/levels/1/submit",
                        json={"strokes": STROKES},
                        headers={"X-User-ID": USER})
        assert r.status_code == 200
        body = r.json()
        assert body["passed"] is True
        assert body["target_class"] == target
        assert body["attempts"] == 1
        assert body["best_confidence"] == 0.9
        assert body["next_level_id"] == 2
        assert len(body["top3"]) == 3

        # 进度已记录
        p = client.get("/api/progress", headers={"X-User-ID": USER}).json()
        assert p["passed_count"] == 1
        assert p["total"] == 100
        row = next(x for x in p["levels"] if x["level_id"] == 1)
        assert row["passed"] is True and row["attempts"] == 1

    def test_submit_fail_then_retry(self, client, monkeypatch):
        target = client.get("/api/levels/2").json()["class_name"]
        wrong = [("wrong-class", "错", 0.6)] + [
            (f" filler-{i}", f"填{i}", 0.01) for i in range(4)
        ]
        monkeypatch.setattr(inference, "predict_topk", lambda s, k=5: wrong[:k])

        # 第一次：top1 未命中 -> 失败
        r = client.post("/api/levels/2/submit",
                        json={"strokes": STROKES},
                        headers={"X-User-ID": USER})
        body = r.json()
        assert body["passed"] is False
        assert body["next_level_id"] is None
        assert body["best_confidence"] == 0.0  # 目标类不在 top5

        # 第二次：命中但置信度低于阈值 -> 失败
        low = [(target, "目标", 0.3)] + [
            (f" filler-{i}", f"填{i}", 0.02) for i in range(4)
        ]
        monkeypatch.setattr(inference, "predict_topk", lambda s, k=5: low[:k])
        r = client.post("/api/levels/2/submit",
                        json={"strokes": STROKES},
                        headers={"X-User-ID": USER})
        body = r.json()
        assert body["passed"] is False
        assert body["attempts"] == 2
        assert body["best_confidence"] == 0.3

        # 进度：未通关但尝试数正确
        p = client.get("/api/progress", headers={"X-User-ID": USER}).json()
        row = next(x for x in p["levels"] if x["level_id"] == 2)
        assert row["passed"] is False and row["attempts"] == 2

    def test_submit_404(self, client):
        r = client.post("/api/levels/999/submit",
                        json={"strokes": STROKES},
                        headers={"X-User-ID": USER})
        assert r.status_code == 404

    def test_progress_empty_user(self, client):
        p = client.get("/api/progress", headers={"X-User-ID": "nobody"}).json()
        assert p["passed_count"] == 0
        assert p["levels"] == []
