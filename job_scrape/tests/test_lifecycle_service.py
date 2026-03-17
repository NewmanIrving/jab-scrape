"""Unit tests for lifecycle field maintenance (Story 3.2)."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.raw_job_posting import RawJobPosting
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.normalizer.lifecycle_service import LifecycleService


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None)


def _seconds_between(a: datetime | None, b: datetime | None) -> float:
    if a is None or b is None:
        return 0.0
    return abs((_naive(a) - _naive(b)).total_seconds())


def _create_task(db: Session, task_id: str) -> None:
    now = datetime.now(UTC)
    task = Task(
        task_id=task_id,
        status="running",
        customer_scope=["测试客户"],
        triggered_by="test-op",
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_path = tmp_path / "test_lifecycle.db"
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


class TestLifecycleService:
    def test_first_seen_initialized_for_first_appearance(
        self,
        db_session: Session,
    ) -> None:
        _create_task(db_session, "task-life-001")
        scraped_at = datetime.now(UTC)
        posting = RawJobPosting(
            task_id="task-life-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shanghai/10001.html",
            source_job_id="10001",
            source_url_canonical="https://jobs.51job.com/shanghai/10001.html",
            company_name="样本公司",
            job_title="Python开发",
            scraped_at=scraped_at,
        )
        db_session.add(posting)
        db_session.commit()

        service = LifecycleService(db_session)
        result = service.update_posting_lifecycle(posting.id, task_id="task-life-001")

        assert result.success is True
        assert result.times_seen == 1
        db_session.refresh(posting)
        assert posting.times_seen == 1
        assert _seconds_between(posting.first_seen_at, scraped_at) < 1
        assert _seconds_between(posting.last_seen_at, scraped_at) < 1

    def test_reappearance_in_new_task_increments_times_seen(
        self,
        db_session: Session,
    ) -> None:
        _create_task(db_session, "task-life-hist")
        _create_task(db_session, "task-life-new")
        t1 = datetime.now(UTC) - timedelta(days=1)
        t2 = datetime.now(UTC)

        posting_old = RawJobPosting(
            task_id="task-life-hist",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/beijing/20002.html",
            source_job_id="20002",
            source_url_canonical="https://jobs.51job.com/beijing/20002.html",
            company_name="历史公司",
            job_title="后端开发",
            scraped_at=t1,
        )
        posting_new = RawJobPosting(
            task_id="task-life-new",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/beijing/20002.html",
            source_job_id="20002",
            source_url_canonical="https://jobs.51job.com/beijing/20002.html",
            company_name="当前公司",
            job_title="后端开发",
            scraped_at=t2,
        )
        db_session.add_all([posting_old, posting_new])
        db_session.commit()

        service = LifecycleService(db_session)
        service.update_posting_lifecycle(posting_old.id, task_id="task-life-hist")
        result = service.update_posting_lifecycle(
            posting_new.id,
            task_id="task-life-new",
        )

        assert result.success is True
        assert result.times_seen == 2
        db_session.refresh(posting_new)
        assert posting_new.times_seen == 2
        assert _seconds_between(posting_new.first_seen_at, t1) < 1
        assert _seconds_between(posting_new.last_seen_at, t2) < 1

    def test_duplicate_rows_in_same_task_count_once(
        self,
        db_session: Session,
    ) -> None:
        _create_task(db_session, "task-life-dup")
        t1 = datetime.now(UTC) - timedelta(minutes=5)
        t2 = datetime.now(UTC)

        posting1 = RawJobPosting(
            task_id="task-life-dup",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shenzhen/30003.html",
            source_job_id="30003",
            source_url_canonical="https://jobs.51job.com/shenzhen/30003.html",
            company_name="公司A",
            job_title="测试开发",
            scraped_at=t1,
        )
        posting2 = RawJobPosting(
            task_id="task-life-dup",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/shenzhen/30003.html",
            source_job_id="30003",
            source_url_canonical="https://jobs.51job.com/shenzhen/30003.html",
            company_name="公司A",
            job_title="测试开发",
            scraped_at=t2,
        )
        db_session.add_all([posting1, posting2])
        db_session.commit()

        service = LifecycleService(db_session)
        result = service.update_posting_lifecycle(posting2.id, task_id="task-life-dup")

        assert result.success is True
        assert result.updated_rows == 2
        assert result.times_seen == 1
        db_session.refresh(posting1)
        db_session.refresh(posting2)
        assert posting1.times_seen == 1
        assert posting2.times_seen == 1
        assert _seconds_between(posting1.first_seen_at, t1) < 1
        assert _seconds_between(posting2.last_seen_at, t2) < 1

    def test_fallback_to_canonical_identity_when_job_id_missing(
        self,
        db_session: Session,
    ) -> None:
        _create_task(db_session, "task-life-canon-1")
        _create_task(db_session, "task-life-canon-2")
        canonical = "https://jobs.51job.com/guangzhou/40004.html"
        t1 = datetime.now(UTC) - timedelta(days=2)
        t2 = datetime.now(UTC)

        posting_old = RawJobPosting(
            task_id="task-life-canon-1",
            source_platform="51job",
            source_url_raw=canonical,
            source_job_id=None,
            source_url_canonical=canonical,
            company_name="公司B",
            job_title="算法工程师",
            scraped_at=t1,
        )
        posting_new = RawJobPosting(
            task_id="task-life-canon-2",
            source_platform="51job",
            source_url_raw=canonical,
            source_job_id=None,
            source_url_canonical=canonical,
            company_name="公司B",
            job_title="算法工程师",
            scraped_at=t2,
        )
        db_session.add_all([posting_old, posting_new])
        db_session.commit()

        service = LifecycleService(db_session)
        service.update_posting_lifecycle(posting_old.id, task_id="task-life-canon-1")
        result = service.update_posting_lifecycle(
            posting_new.id,
            task_id="task-life-canon-2",
        )

        assert result.success is True
        assert result.identity_type == "source_url_canonical"
        assert result.times_seen == 2

    def test_missing_identity_records_event_and_skips(
        self,
        db_session: Session,
    ) -> None:
        _create_task(db_session, "task-life-missing")
        posting = RawJobPosting(
            task_id="task-life-missing",
            source_platform="51job",
            source_url_raw="https://example.com/no-id",
            source_job_id=None,
            source_url_canonical=None,
            company_name="缺失公司",
            job_title="未知岗位",
            scraped_at=datetime.now(UTC),
        )
        db_session.add(posting)
        db_session.commit()

        service = LifecycleService(db_session)
        result = service.update_posting_lifecycle(
            posting.id,
            task_id="task-life-missing",
        )

        assert result.success is False
        assert result.skipped is True
        db_session.refresh(posting)
        assert posting.first_seen_at is None
        assert posting.last_seen_at is None
        assert posting.times_seen is None

        event = (
            db_session.query(TaskEvent)
            .filter(TaskEvent.task_id == "task-life-missing")
            .filter(TaskEvent.event_type == "lifecycle.identity.missing")
            .first()
        )
        assert event is not None
