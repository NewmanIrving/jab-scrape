"""Story 1.5 — Manual 队列处理（重放/跳过）API 测试"""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_operator, get_db
from app.db.base import Base
from app.main import app
from app.models import Task

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path: pytest.TempPathFactory) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test_story_1_5.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_operator() -> str:
        return "ops_tester"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_operator] = override_get_current_operator
    app.state.testing_session_local = testing_session_local

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        if hasattr(app.state, "testing_session_local"):
            del app.state.testing_session_local
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _create_task(client: TestClient, customer_scope: list[str] | None = None) -> dict:
    resp = client.post(
        "/api/tasks",
        json={"customer_scope": customer_scope or ["A公司"]},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _set_task_status(task_id: str, new_status: str) -> None:
    """直接操作数据库，将任务状态设置为指定值（绕过服务层）"""
    session_factory = app.state.testing_session_local
    db = session_factory()
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        assert task is not None
        task.status = new_status
        task.updated_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


def _do_manual_action(
    client: TestClient,
    task_id: str,
    action: str,
    reason: str | None = None,
) -> dict:
    body: dict = {"action": action}
    if reason is not None:
        body["reason"] = reason
    return client.post(f"/api/tasks/{task_id}/actions/manual", json=body)


def _get_events(client: TestClient, task_id: str) -> list[dict]:
    resp = client.get(f"/api/tasks/{task_id}/events")
    assert resp.status_code == 200
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Task 1: replay 成功路径
# ---------------------------------------------------------------------------

class TestManualActionReplay:
    def test_replay_returns_200(self, client: TestClient) -> None:
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "replay")
        assert resp.status_code == 200

    def test_replay_response_contract(self, client: TestClient) -> None:
        """响应体遵循 {data, meta, error} 包装"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "replay")
        body = resp.json()

        assert body["error"] is None
        assert body["meta"] is None
        assert body["data"] is not None

    def test_replay_data_fields(self, client: TestClient) -> None:
        """data 字段包含指定字段"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "replay")
        data = resp.json()["data"]

        expected_fields = {
            "task_id",
            "previous_status",
            "current_status",
            "action",
            "operator",
            "updated_at",
        }
        assert set(data.keys()) == expected_fields

    def test_replay_transitions_status_to_pending(self, client: TestClient) -> None:
        """replay 使任务状态从 manual → pending"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "replay")
        data = resp.json()["data"]

        assert data["previous_status"] == "manual"
        assert data["current_status"] == "pending"
        assert data["action"] == "replay"

    def test_replay_task_status_persisted(self, client: TestClient) -> None:
        """replay 后 GET /api/tasks/{task_id} 返回 status=pending"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "replay")

        detail_resp = client.get(f"/api/tasks/{created['task_id']}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"]["status"] == "pending"

    def test_replay_with_reason(self, client: TestClient) -> None:
        """replay 携带 reason 字段时正常执行"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(
            client, created["task_id"], "replay", reason="重新拉起"
        )
        assert resp.status_code == 200

    def test_replay_operator_in_response(self, client: TestClient) -> None:
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "replay")
        assert resp.json()["data"]["operator"] == "ops_tester"

    def test_replay_task_id_matches(self, client: TestClient) -> None:
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "replay")
        assert resp.json()["data"]["task_id"] == created["task_id"]


# ---------------------------------------------------------------------------
# Task 2: skip 成功路径
# ---------------------------------------------------------------------------

class TestManualActionSkip:
    def test_skip_returns_200(self, client: TestClient) -> None:
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "skip")
        assert resp.status_code == 200

    def test_skip_transitions_status_to_failed(self, client: TestClient) -> None:
        """skip 使任务状态从 manual → failed"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "skip")
        data = resp.json()["data"]

        assert data["previous_status"] == "manual"
        assert data["current_status"] == "failed"
        assert data["action"] == "skip"

    def test_skip_task_status_persisted(self, client: TestClient) -> None:
        """skip 后 GET /api/tasks/{task_id} 返回 status=failed"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "skip")

        detail_resp = client.get(f"/api/tasks/{created['task_id']}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"]["status"] == "failed"

    def test_skip_with_reason(self, client: TestClient) -> None:
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(
            client, created["task_id"], "skip", reason="人工确认无需重试"
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task 3: 错误路径
# ---------------------------------------------------------------------------

class TestManualActionErrors:
    def test_invalid_action_returns_422(self, client: TestClient) -> None:
        """非法 action 返回 422 + VAL_MANUAL_ACTION_INVALID"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        resp = _do_manual_action(client, created["task_id"], "invalid_action")
        assert resp.status_code == 422
        body = resp.json()
        assert body["data"] is None
        assert body["meta"] is None
        assert body["error"]["code"] == "VAL_MANUAL_ACTION_INVALID"

    def test_task_not_found_returns_404(self, client: TestClient) -> None:
        """任务不存在返回 404 + VAL_TASK_NOT_FOUND"""
        resp = _do_manual_action(client, "nonexistent-task-id", "replay")
        assert resp.status_code == 404
        body = resp.json()
        assert body["data"] is None
        assert body["meta"] is None
        assert body["error"]["code"] == "VAL_TASK_NOT_FOUND"

    def test_non_manual_status_pending_returns_409(self, client: TestClient) -> None:
        """pending 状态任务执行 replay 返回 409

        错误码应为 VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION
        """
        created = _create_task(client)  # 默认 pending

        resp = _do_manual_action(client, created["task_id"], "replay")
        assert resp.status_code == 409
        body = resp.json()
        assert body["data"] is None
        assert body["meta"] is None
        assert body["error"]["code"] == "VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION"

    def test_non_manual_status_failed_returns_409(self, client: TestClient) -> None:
        """failed 状态任务执行 skip 返回 409"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "failed")

        resp = _do_manual_action(client, created["task_id"], "skip")
        assert resp.status_code == 409
        err_code = resp.json()["error"]["code"]
        assert err_code == "VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION"

    def test_non_manual_status_running_returns_409(self, client: TestClient) -> None:
        """running 状态任务执行动作返回 409"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "running")

        resp = _do_manual_action(client, created["task_id"], "replay")
        assert resp.status_code == 409
        err_code = resp.json()["error"]["code"]
        assert err_code == "VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION"

    def test_error_response_structure(self, client: TestClient) -> None:
        """所有错误响应都遵循统一包装结构"""
        resp = _do_manual_action(client, "nonexistent", "replay")
        body = resp.json()
        assert set(body.keys()) == {"data", "meta", "error"}
        assert set(body["error"].keys()) >= {"code", "message"}


# ---------------------------------------------------------------------------
# Task 4: 审计事件留痕（AC: 1, 4）
# ---------------------------------------------------------------------------

class TestManualActionAudit:
    def test_replay_creates_task_event(self, client: TestClient) -> None:
        """replay 动作后 task_events 新增 task.manual.replay 事件"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "replay")

        events = _get_events(client, created["task_id"])
        event_types = [e["event_type"] for e in events]
        assert "task.manual.replay" in event_types

    def test_skip_creates_task_event(self, client: TestClient) -> None:
        """skip 动作后 task_events 新增 task.manual.skip 事件"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "skip")

        events = _get_events(client, created["task_id"])
        event_types = [e["event_type"] for e in events]
        assert "task.manual.skip" in event_types

    def test_replay_event_payload_contains_required_fields(
        self, client: TestClient
    ) -> None:
        """replay 事件 payload 包含 task_id、action、from_status、to_status"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "replay", reason="测试重放")

        events = _get_events(client, created["task_id"])
        replay_event = next(
            e for e in events if e["event_type"] == "task.manual.replay"
        )
        payload = replay_event["payload"]

        assert payload["task_id"] == created["task_id"]
        assert payload["action"] == "replay"
        assert payload["from_status"] == "manual"
        assert payload["to_status"] == "pending"
        assert payload["reason"] == "测试重放"
        assert payload["timestamp"]
        datetime.fromisoformat(payload["timestamp"])

    def test_skip_event_payload_fields(self, client: TestClient) -> None:
        """skip 事件 payload 正确记录状态迁移信息"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "skip")

        events = _get_events(client, created["task_id"])
        skip_event = next(e for e in events if e["event_type"] == "task.manual.skip")
        payload = skip_event["payload"]

        assert payload["from_status"] == "manual"
        assert payload["to_status"] == "failed"

    def test_event_visible_via_events_endpoint(self, client: TestClient) -> None:
        """replay 后 GET /api/tasks/{task_id}/events 可查到 manual.replay 事件"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "replay")

        resp = client.get(f"/api/tasks/{created['task_id']}/events")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None

        event_types = [e["event_type"] for e in body["data"]]
        assert "task.manual.replay" in event_types

    def test_event_count_increments_after_action(self, client: TestClient) -> None:
        """manual 动作后 event_count 增加 1"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")

        # 动作前查事件数
        before = (
            client.get(f"/api/tasks/{created['task_id']}")
            .json()["data"]["progress"]["event_count"]
        )

        _do_manual_action(client, created["task_id"], "replay")

        after = (
            client.get(f"/api/tasks/{created['task_id']}")
            .json()["data"]["progress"]["event_count"]
        )
        assert after == before + 1

    def test_event_operator_matches_current_operator(self, client: TestClient) -> None:
        """审计事件的 operator 字段与发起请求的操作员一致"""
        created = _create_task(client)
        _set_task_status(created["task_id"], "manual")
        _do_manual_action(client, created["task_id"], "skip")

        events = _get_events(client, created["task_id"])
        skip_event = next(e for e in events if e["event_type"] == "task.manual.skip")
        assert skip_event["operator"] == "ops_tester"
