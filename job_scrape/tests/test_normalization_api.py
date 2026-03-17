"""API-level tests for normalization endpoints (Story 3.1).

Tests the POST /tasks/{task_id}/normalize endpoint.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.raw_job_posting import RawJobPosting
from app.models.task import Task


AUTH_HEADERS = {"X-Operator": "test-op", "X-Role": "operator"}


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test_norm_api.db"
    engine = create_engine(f"sqlite:///{db_path}")
    testing_session_local = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _seed_task_and_postings(client: TestClient, task_id: str = "task-norm-api-001") -> None:
    """Seed a task and sample postings for normalization testing."""
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    now = datetime.now(UTC)

    # Create task
    task = Task(
        task_id=task_id,
        status="running",
        customer_scope=["客户A"],
        triggered_by="test-op",
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    # Create postings - one with job_id, one without
    posting1 = RawJobPosting(
        task_id=task_id,
        source_platform="51job",
        source_url_raw="https://jobs.51job.com/shanghai/123456789.html",
        company_name="测试公司A",
        job_title="Python开发",
        location_text="上海",
        scraped_at=now,
        source_job_id="123456789",
        job_id_source="api",
    )

    posting2 = RawJobPosting(
        task_id=task_id,
        source_platform="51job",
        source_url_raw="https://jobs.51job.com/beijing/987654321.html",
        company_name="测试公司B",
        job_title="Java开发",
        location_text="北京",
        scraped_at=now,
        source_job_id="987654321",
        job_id_source="api",
    )

    # Posting without canonical URL (should be normalized)
    posting3 = RawJobPosting(
        task_id=task_id,
        source_platform="51job",
        source_url_raw="https://jobs.51job.com/shanghai/555666777.html",
        company_name="测试公司C",
        job_title="前端开发",
        location_text="上海",
        scraped_at=now,
        source_job_id="555666777",
        job_id_source="api",
        source_url_canonical=None,  # Will be generated
    )

    db.add_all([posting1, posting2, posting3])
    db.commit()
    db.close()


class TestNormalizeTaskEndpoint:
    """Test POST /tasks/{task_id}/normalize endpoint."""

    def test_normalize_endpoint_returns_200(self, client: TestClient) -> None:
        """Test successful normalization returns 200."""
        _seed_task_and_postings(client)

        response = client.post(
            "/api/tasks/task-norm-api-001/normalize",
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["task_id"] == "task-norm-api-001"

    def test_normalize_response_format(self, client: TestClient) -> None:
        """Test response follows {data, meta, error} format."""
        _seed_task_and_postings(client)

        response = client.post(
            "/api/tasks/task-norm-api-001/normalize",
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        # Verify API response format
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        assert data["error"] is None

    def test_normalize_counts_correct(self, client: TestClient) -> None:
        """Test success/failed counts are correct."""
        _seed_task_and_postings(client)

        response = client.post(
            "/api/v1/tasks/task-norm-api-001/normalize",
            headers=AUTH_HEADERS,
        )

        data = response.json()
        result_data = data["data"]
        # All 3 postings should be normalized successfully
        assert result_data["success_count"] == 3
        assert result_data["failed_count"] == 0
        assert result_data["total_processed"] == 3

    def test_normalize_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Test normalizing nonexistent task returns 404."""
        response = client.post(
            "/api/v1/tasks/nonexistent-task/normalize",
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data

    def test_normalize_limit_parameter(self, client: TestClient) -> None:
        """Test limit parameter restricts processing count."""
        _seed_task_and_postings(client)

        response = client.post(
            "/api/v1/tasks/task-norm-api-001/normalize?limit=2",
            headers=AUTH_HEADERS,
        )

        data = response.json()
        result_data = data["data"]
        # Should only process 2 due to limit
        assert result_data["total_processed"] == 2
