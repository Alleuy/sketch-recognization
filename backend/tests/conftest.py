# Time: 2026/10/15
# 测试公共夹具：临时数据库 + TestClient（触发 lifespan：建表播种 + 加载模型）。
import os
import shutil
import tempfile

# 必须在导入 app 之前设置，让 app.config / app.database 使用临时库
_TMPDIR = tempfile.mkdtemp(prefix="qd_backend_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMPDIR + '/test.db').replace(os.sep, '/')}"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # with 语句触发 lifespan
        yield c


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMPDIR, ignore_errors=True)
