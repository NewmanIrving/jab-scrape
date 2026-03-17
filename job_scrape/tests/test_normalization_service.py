"""Integration tests for normalization workflow (Story 3.1).

Tests the complete flow from job_id persistence to normalization.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.raw_job_posting import RawJobPosting
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.normalizer.normalization_service import NormalizationService


def _create_test_task(db: Session, task_id: str = "task-norm-001") -> Task:
    """Helper to create a task in the DB for testing."""
    now = datetime.now(UTC)
    task = Task(
        task_id=task_id,
        status="running",
        customer_scope=["测试客户"],
        triggered_by="test-operator",
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    return task


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_path = tmp_path / "test_norm.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


class TestJobIdPersistence:
    """Test job_id persistence from API data to database."""

    def test_job_id_persisted_from_api(self, db_session: Session) -> None:
        """Test that job_id from API is correctly persisted."""
        _create_test_task(db_session)
        now = datetime.now(UTC)

        # Create a posting with job_id from API
        posting = RawJobPosting(
            task_id="task-norm-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shanghai/123456789.html",
            company_name="测试公司",
            job_title="Python开发",
            location_text="上海",
            scraped_at=now,
            # Story 3.1 new fields
            source_job_id="123456789",
            job_id_source="api",
            job_tags=["五险一金", "带薪年假"],
            job_area_detail="上海-浦东新区",
            confirm_date="2026-03-15",
            company_type="民营公司",
            company_size="150-500人",
        )
        db_session.add(posting)
        db_session.commit()

        # Verify persistence
        retrieved = db_session.query(RawJobPosting).first()
        assert retrieved is not None
        assert retrieved.source_job_id == "123456789"
        assert retrieved.job_id_source == "api"
        assert retrieved.job_tags == ["五险一金", "带薪年假"]
        assert retrieved.job_area_detail == "上海-浦东新区"
        assert retrieved.confirm_date == "2026-03-15"
        assert retrieved.company_type == "民营公司"
        assert retrieved.company_size == "150-500人"

    def test_missing_fields_null_for_history(self, db_session: Session) -> None:
        """Test that historical data has null for new fields."""
        now = datetime.now(UTC)

        # Create a posting without new fields (historical data)
        posting = RawJobPosting(
            task_id="task-hist-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/beijing/999999999.html",
            company_name="历史公司",
            job_title="历史岗位",
            location_text="北京",
            scraped_at=now,
            # New fields should be null for historical data
            source_job_id=None,
            source_url_canonical=None,
            job_id_source=None,
            job_tags=None,
            job_area_detail=None,
            confirm_date=None,
            company_type=None,
            company_size=None,
        )
        db_session.add(posting)
        db_session.commit()

        # Verify historical data compatibility
        retrieved = db_session.query(RawJobPosting).first()
        assert retrieved.source_job_id is None
        assert retrieved.source_url_canonical is None
        assert retrieved.job_tags is None
        assert retrieved.job_area_detail is None


class TestNormalizationFlow:
    """Test normalization workflow end-to-end."""

    def test_normalize_posting_with_existing_job_id(
        self, db_session: Session
    ) -> None:
        """Test normalization when job_id already exists from API."""
        _create_test_task(db_session)
        now = datetime.now(UTC)

        posting = RawJobPosting(
            task_id="task-norm-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shanghai/123456789.html",
            company_name="测试公司",
            job_title="Python开发",
            location_text="上海",
            scraped_at=now,
            source_job_id="123456789",
            job_id_source="api",
        )
        db_session.add(posting)
        db_session.commit()
        posting_id = posting.id

        # Execute normalization
        service = NormalizationService(db_session)
        result = service.normalize_posting(posting_id, task_id="task-norm-001")

        # Verify result
        assert result.success is True
        assert result.source_job_id == "123456789"
        assert result.job_id_source == "api"
        assert result.source_url_canonical == "https://jobs.51job.com/shanghai/123456789.html"

        # Verify DB update
        db_session.refresh(posting)
        assert posting.source_url_canonical == "https://jobs.51job.com/shanghai/123456789.html"

    def test_normalize_posting_url_parse_fallback(
        self, db_session: Session
    ) -> None:
        """Test normalization with URL parsing fallback when no job_id."""
        _create_test_task(db_session)
        now = datetime.now(UTC)

        # Posting without job_id (will be extracted from URL)
        posting = RawJobPosting(
            task_id="task-norm-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/beijing/987654321.html",
            company_name="测试公司2",
            job_title="Java开发",
            location_text="北京",
            scraped_at=now,
            source_job_id=None,  # No job_id from API
            job_id_source=None,
        )
        db_session.add(posting)
        db_session.commit()
        posting_id = posting.id

        # Execute normalization
        service = NormalizationService(db_session)
        result = service.normalize_posting(posting_id, task_id="task-norm-001")

        # Verify result
        assert result.success is True
        assert result.source_job_id == "987654321"
        assert result.job_id_source == "url_parse"
        assert result.source_url_canonical == "https://jobs.51job.com/beijing/987654321.html"

    def test_normalize_failed_event_recorded(self, db_session: Session) -> None:
        """Test that failed normalization records an event."""
        _create_test_task(db_session)
        now = datetime.now(UTC)

        # Posting with invalid URL (cannot extract job_id)
        posting = RawJobPosting(
            task_id="task-norm-001",
            source_platform="51job",
            source_url_raw="https://example.com/job/123",  # Invalid 51job URL
            company_name="测试公司3",
            job_title="测试岗位",
            scraped_at=now,
            source_job_id=None,
            job_id_source=None,
        )
        db_session.add(posting)
        db_session.commit()
        posting_id = posting.id

        # Execute normalization
        service = NormalizationService(db_session)
        result = service.normalize_posting(posting_id, task_id="task-norm-001")

        # Verify failure
        assert result.success is False
        assert result.error_message is not None

        # Verify event was recorded
        events = (
            db_session.query(TaskEvent)
            .filter(TaskEvent.task_id == "task-norm-001")
            .filter(TaskEvent.event_type == "normalization.job_id.extract_failed")
            .all()
        )
        assert len(events) == 1
        payload = events[0].payload
        assert payload["posting_id"] == posting_id

        identity_missing_events = (
            db_session.query(TaskEvent)
            .filter(TaskEvent.task_id == "task-norm-001")
            .filter(TaskEvent.event_type == "lifecycle.identity.missing")
            .all()
        )
        assert len(identity_missing_events) == 1

    def test_normalization_completed_event_recorded(
        self, db_session: Session
    ) -> None:
        """Test that completed normalization records an event."""
        _create_test_task(db_session)
        now = datetime.now(UTC)

        posting = RawJobPosting(
            task_id="task-norm-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shanghai/111222333.html",
            company_name="测试公司4",
            job_title="测试",
            location_text="上海",
            scraped_at=now,
            source_job_id="111222333",
            job_id_source="api",
        )
        db_session.add(posting)
        db_session.commit()
        posting_id = posting.id

        # Execute normalization
        service = NormalizationService(db_session)
        service.normalize_posting(posting_id, task_id="task-norm-001")

        # Verify event was recorded
        events = (
            db_session.query(TaskEvent)
            .filter(TaskEvent.task_id == "task-norm-001")
            .filter(TaskEvent.event_type == "normalization.completed")
            .all()
        )
        assert len(events) == 1
        payload = events[0].payload
        assert payload["source_job_id"] == "111222333"
        assert payload["job_id_source"] == "api"


class TestNormalizationIdempotency:
    """Test normalization idempotency."""

    def test_idempotent_normalization(self, db_session: Session) -> None:
        """Test that running normalization multiple times produces same result."""
        _create_test_task(db_session)
        now = datetime.now(UTC)

        posting = RawJobPosting(
            task_id="task-norm-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shanghai/444555666.html",
            company_name="测试公司5",
            job_title="测试",
            location_text="上海",
            scraped_at=now,
            source_job_id="444555666",
            job_id_source="api",
        )
        db_session.add(posting)
        db_session.commit()
        posting_id = posting.id

        service = NormalizationService(db_session)

        # Run normalization twice
        result1 = service.normalize_posting(posting_id, task_id="task-norm-001")
        result2 = service.normalize_posting(posting_id, task_id="task-norm-001")

        # Results should be identical
        assert result1.source_url_canonical == result2.source_url_canonical
        assert result1.source_job_id == result2.source_job_id


class TestNormalizationWithLifecycle:
    """Test Story 3.2 lifecycle integration into normalization flow."""

    def test_normalization_triggers_lifecycle_update(
        self,
        db_session: Session,
    ) -> None:
        _create_test_task(db_session, "task-norm-hist")
        _create_test_task(db_session, "task-norm-new")
        t1 = datetime.now(UTC)
        t2 = datetime.now(UTC)

        historical = RawJobPosting(
            task_id="task-norm-hist",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/hangzhou/654321987.html",
            company_name="历史公司",
            job_title="后端工程师",
            location_text="杭州",
            scraped_at=t1,
            source_job_id="654321987",
            source_url_canonical="https://jobs.51job.com/hangzhou/654321987.html",
            job_id_source="api",
        )
        current = RawJobPosting(
            task_id="task-norm-new",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/hangzhou/654321987.html",
            company_name="当前公司",
            job_title="后端工程师",
            location_text="杭州",
            scraped_at=t2,
            source_job_id="654321987",
            source_url_canonical=None,
            job_id_source="api",
        )
        db_session.add_all([historical, current])
        db_session.commit()

        service = NormalizationService(db_session)
        result = service.normalize_posting(current.id, task_id="task-norm-new")

        assert result.success is True
        db_session.refresh(current)
        assert current.source_url_canonical == "https://jobs.51job.com/hangzhou/654321987.html"
        assert current.times_seen == 2
        assert current.first_seen_at is not None
        assert current.last_seen_at is not None

        event = (
            db_session.query(TaskEvent)
            .filter(TaskEvent.task_id == "task-norm-new")
            .filter(TaskEvent.event_type == "lifecycle.seen.updated")
            .first()
        )
        assert event is not None
        assert event.payload["times_seen"] == 2

    def test_lifecycle_failure_does_not_block_normalization(
        self,
        db_session: Session,
    ) -> None:
        _create_test_task(db_session, "task-norm-isolation")
        posting = RawJobPosting(
            task_id="task-norm-isolation",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/nanjing/666777888.html",
            company_name="隔离公司",
            job_title="测试开发",
            location_text="南京",
            scraped_at=datetime.now(UTC),
            source_job_id="666777888",
            source_url_canonical=None,
            job_id_source="api",
        )
        db_session.add(posting)
        db_session.commit()

        with patch(
            "app.normalizer.normalization_service.LifecycleService.update_posting_lifecycle",
            side_effect=RuntimeError("lifecycle boom"),
        ):
            service = NormalizationService(db_session)
            result = service.normalize_posting(
                posting.id,
                task_id="task-norm-isolation",
            )

        assert result.success is True
        db_session.refresh(posting)
        assert posting.source_url_canonical == "https://jobs.51job.com/nanjing/666777888.html"
