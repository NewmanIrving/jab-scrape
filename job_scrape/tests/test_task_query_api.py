"""Story 1.3 — 查询任务状态与基础进度 API 测试"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_operator, get_db
from app.db.base import Base
from app.main import app
from app.models import TaskEvent


@pytest.fixture()
def client(tmp_path: pytest.TempPathFactory) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test_story_1_3.db"
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


def _append_task_event(
    task_id: str,
    event_type: str,
    created_at: datetime,
    payload: dict,
) -> None:
    session_factory = app.state.testing_session_local
    db = session_factory()
    try:
        db.add(
            TaskEvent(
                task_id=task_id,
                event_type=event_type,
                operator="ops_tester",
                payload=payload,
                created_at=created_at,
            )
        )
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /api/tasks — 列表查询
# ---------------------------------------------------------------------------

class TestListTasks:
    def test_empty_returns_empty_list_with_meta(self, client: TestClient) -> None:
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None
        assert body["data"] == []
        assert body["meta"] == {"total": 0, "limit": 20, "offset": 0}

    def test_returns_created_task(self, client: TestClient) -> None:
        created = _create_task(client)
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        item = body["data"][0]
        assert item["task_id"] == created["task_id"]
        assert item["status"] == "pending"
        assert "customer_scope" in item
        assert "updated_at" in item

    def test_list_item_fields(self, client: TestClient) -> None:
        """列表项包含规定的最小字段集合"""
        _create_task(client, ["B公司"])
        resp = client.get("/api/tasks")
        item = resp.json()["data"][0]
        expected_fields = (
            "task_id", "status", "customer_scope",
            "triggered_by", "created_at", "updated_at",
        )
        for field in expected_fields:
            assert field in item, f"missing field: {field}"

    def test_filter_by_customer(self, client: TestClient) -> None:
        _create_task(client, ["A公司"])
        _create_task(client, ["B公司"])
        resp = client.get("/api/tasks", params={"customer": "A公司"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all("A公司" in item["customer_scope"] for item in data)

    def test_filter_by_customer_is_exact_match(self, client: TestClient) -> None:
        _create_task(client, ["A公司"])
        _create_task(client, ["AA公司"])
        resp = client.get("/api/tasks", params={"customer": "A公司"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["customer_scope"] == ["A公司"]

    def test_pagination_limit_offset(self, client: TestClient) -> None:
        for _ in range(3):
            _create_task(client)
        resp = client.get("/api/tasks", params={"limit": 2, "offset": 0})
        body = resp.json()
        assert body["meta"]["total"] == 3
        assert body["meta"]["limit"] == 2
        assert body["meta"]["offset"] == 0
        assert len(body["data"]) == 2

    def test_pagination_offset(self, client: TestClient) -> None:
        for _ in range(3):
            _create_task(client)
        resp = client.get("/api/tasks", params={"limit": 2, "offset": 2})
        assert len(resp.json()["data"]) == 1

    def test_invalid_time_range_returns_422(self, client: TestClient) -> None:
        resp = client.get(
            "/api/tasks",
            params={
                "start_time": "2026-03-13T12:00:00Z",
                "end_time": "2026-03-13T10:00:00Z",
            },
        )
        assert resp.status_code == 422
        err = resp.json()["error"]
        assert err["code"] == "VAL_INVALID_TIME_RANGE"

    def test_invalid_time_format_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/tasks", params={"start_time": "not-a-date"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["data"] is None
        assert body["meta"] is None
        assert body["error"]["code"] == "VAL_REQUEST_INVALID"

    def test_non_utc_time_returns_422(self, client: TestClient) -> None:
        _create_task(client, ["A公司"])
        resp = client.get(
            "/api/tasks",
            params={"start_time": "2026-03-13T10:00:00+08:00"},
        )
        assert resp.status_code == 422
        err = resp.json()["error"]
        assert err["code"] == "VAL_INVALID_TIMEZONE"

    def test_meta_structure(self, client: TestClient) -> None:
        resp = client.get("/api/tasks")
        meta = resp.json()["meta"]
        assert set(meta.keys()) == {"total", "limit", "offset"}

    def test_default_limit_is_20(self, client: TestClient) -> None:
        resp = client.get("/api/tasks")
        assert resp.json()["meta"]["limit"] == 20


# ---------------------------------------------------------------------------
# GET /api/tasks/{task_id} — 详情查询
# ---------------------------------------------------------------------------

class TestGetTask:
    def test_returns_task_with_progress(self, client: TestClient) -> None:
        created = _create_task(client)
        resp = client.get(f"/api/tasks/{created['task_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None
        assert body["meta"] is None
        data = body["data"]
        assert data["task_id"] == created["task_id"]
        assert data["status"] == "pending"
        assert "progress" in data

    def test_progress_fields(self, client: TestClient) -> None:
        created = _create_task(client)
        resp = client.get(f"/api/tasks/{created['task_id']}")
        progress = resp.json()["data"]["progress"]
        assert "current_status" in progress
        assert "updated_at" in progress
        assert "event_count" in progress

    def test_event_count_equals_one_after_create(self, client: TestClient) -> None:
        """创建任务后应记录 1 个 task.created 事件"""
        created = _create_task(client)
        resp = client.get(f"/api/tasks/{created['task_id']}")
        assert resp.json()["data"]["progress"]["event_count"] == 1

    def test_detail_meta_is_null(self, client: TestClient) -> None:
        created = _create_task(client)
        resp = client.get(f"/api/tasks/{created['task_id']}")
        assert resp.json()["meta"] is None

    def test_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/tasks/nonexistent-task-id")
        assert resp.status_code == 404
        err = resp.json()["error"]
        assert err["code"] == "VAL_TASK_NOT_FOUND"
        assert resp.json()["data"] is None
        assert resp.json()["meta"] is None

    def test_detail_fields(self, client: TestClient) -> None:
        """详情项包含规定的全部字段"""
        created = _create_task(client)
        resp = client.get(f"/api/tasks/{created['task_id']}")
        data = resp.json()["data"]
        expected_fields = (
            "task_id", "status", "customer_scope", "triggered_by",
            "created_at", "updated_at", "progress",
        )
        for field in expected_fields:
            assert field in data, f"missing field: {field}"


class TestGetTaskEvents:
    def test_returns_events_with_contract(self, client: TestClient) -> None:
        created = _create_task(client)

        resp = client.get(f"/api/tasks/{created['task_id']}/events")
        assert resp.status_code == 200

        body = resp.json()
        assert body["error"] is None
        assert set(body.keys()) == {"data", "meta", "error"}
        assert set(body["meta"].keys()) == {"total", "limit", "offset"}
        assert body["meta"]["limit"] == 50
        assert body["meta"]["offset"] == 0
        assert body["meta"]["total"] >= 1

        event = body["data"][0]
        expected_fields = {
            "task_id",
            "session_id",
            "event_type",
            "operator",
            "payload",
            "error_code",
            "error_message",
            "created_at",
        }
        assert set(event.keys()) == expected_fields
        assert event["task_id"] == created["task_id"]

    def test_event_order_is_created_at_ascending(self, client: TestClient) -> None:
        created = _create_task(client)
        task_id = created["task_id"]
        base = datetime.now(UTC)

        _append_task_event(
            task_id=task_id,
            event_type="task.failed",
            created_at=base + timedelta(seconds=20),
            payload={"error_code": "INT_X", "error_message": "boom"},
        )
        _append_task_event(
            task_id=task_id,
            event_type="task.running",
            created_at=base + timedelta(seconds=10),
            payload={"session_id": "sess_123"},
        )

        resp = client.get(f"/api/tasks/{task_id}/events")
        assert resp.status_code == 200
        event_types = [item["event_type"] for item in resp.json()["data"]]
        assert event_types[:3] == ["task.created", "task.running", "task.failed"]

    def test_pagination_limit_offset(self, client: TestClient) -> None:
        created = _create_task(client)
        task_id = created["task_id"]
        base = datetime.now(UTC)

        _append_task_event(task_id, "task.running", base + timedelta(seconds=1), {})
        _append_task_event(task_id, "task.failed", base + timedelta(seconds=2), {})

        resp = client.get(
            f"/api/tasks/{task_id}/events",
            params={"limit": 2, "offset": 1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"] == {"total": 3, "limit": 2, "offset": 1}
        assert len(body["data"]) == 2

    def test_not_found_returns_val_task_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/tasks/not-exists/events")
        assert resp.status_code == 404
        body = resp.json()
        assert body["data"] is None
        assert body["meta"] is None
        assert body["error"]["code"] == "VAL_TASK_NOT_FOUND"

    def test_invalid_pagination_returns_422(self, client: TestClient) -> None:
        created = _create_task(client)
        task_id = created["task_id"]

        resp = client.get(f"/api/tasks/{task_id}/events", params={"limit": 0})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VAL_REQUEST_INVALID"

    def test_error_fields_and_session_id_derived_from_payload(
        self,
        client: TestClient,
    ) -> None:
        created = _create_task(client)
        task_id = created["task_id"]
        now = datetime.now(UTC)

        _append_task_event(
            task_id=task_id,
            event_type="task.failed",
            created_at=now + timedelta(seconds=1),
            payload={
                "session_id": "sess_1",
                "error_code": "INT_TASK_EXEC_FAILED",
                "error_message": "执行失败",
            },
        )

        resp = client.get(f"/api/tasks/{task_id}/events")
        assert resp.status_code == 200
        failed = [
            item
            for item in resp.json()["data"]
            if item["event_type"] == "task.failed"
        ][0]
        assert failed["session_id"] == "sess_1"
        assert failed["error_code"] == "INT_TASK_EXEC_FAILED"
        assert failed["error_message"] == "执行失败"
