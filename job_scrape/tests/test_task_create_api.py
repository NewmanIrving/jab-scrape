from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_operator, get_db
from app.db.base import Base
from app.main import app


@pytest.fixture()
def client(tmp_path: pytest.TempPathFactory) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test_story_1_2.db"
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

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_create_task_success_returns_pending_and_task_id(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        json={"customer_scope": ["A公司", "B公司"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]["status"] == "pending"
    assert isinstance(payload["data"]["task_id"], str)
    assert payload["data"]["task_id"]


def test_create_task_invalid_scope_returns_validation_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/tasks",
        json={"customer_scope": ["", "   "]},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "VAL_CUSTOMER_SCOPE_EMPTY"


def test_create_task_persists_task_and_created_event(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        json={"customer_scope": ["OnlyOne"]},
    )
    assert response.status_code == 201
    task_id = response.json()["data"]["task_id"]

    db = next(app.dependency_overrides[get_db]())
    try:
        task_row = db.execute(
            text(
                """
                SELECT task_id, status, triggered_by, created_at
                FROM tasks
                WHERE task_id = :task_id
                """
            ),
            {"task_id": task_id},
        ).one()
        assert task_row.task_id == task_id
        assert task_row.status == "pending"
        assert task_row.triggered_by == "ops_tester"
        assert task_row.created_at is not None

        event_row = db.execute(
            text(
                """
                SELECT event_type, task_id, operator
                FROM task_events
                WHERE task_id = :task_id
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"task_id": task_id},
        ).one()
        assert event_row.event_type == "task.created"
        assert event_row.operator == "ops_tester"
    finally:
        db.close()


def test_create_task_uses_x_operator_header(client: TestClient) -> None:
    app.dependency_overrides.pop(get_current_operator, None)

    response = client.post(
        "/api/tasks",
        json={"customer_scope": ["HeaderCorp"]},
        headers={"X-Operator": "alice.ops"},
    )
    assert response.status_code == 201
    task_id = response.json()["data"]["task_id"]

    db = next(app.dependency_overrides[get_db]())
    try:
        row = db.execute(
            text(
                """
                SELECT triggered_by
                FROM tasks
                WHERE task_id = :task_id
                """
            ),
            {"task_id": task_id},
        ).one()
        assert row.triggered_by == "alice.ops"
    finally:
        db.close()