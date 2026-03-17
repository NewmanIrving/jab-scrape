"""Tests for scrape task runner with retry integration (Story 2.1 - Task 3)."""

from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.services.retry import RetryAttempt, RetryResult
from app.services.scrape_service import ScrapeOutcome, ScrapeServiceError
from app.services.scrape_task_runner import run_scrape_task
from app.services.task_service import TaskValidationError

SAMPLE_HTML = """
<html><body><div class="joblist-box">
  <div class="e">
    <a class="el" href="https://jobs.51job.com/123.html">
      <span class="jname">工程师</span>
    </a>
    <div class="cname"><a href="/co">公司A</a></div>
    <div class="info"><span class="at">北京</span></div>
  </div>
</div></body></html>
"""

DETAIL_HTML = """
<html><body>
  <div class="bmsg job_msg inbox">详情职责内容</div>
  <span class="msg ltype">03-16发布</span>
</body></html>
"""


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_path = tmp_path / "test.db"
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


def _create_task(
    db: Session,
    task_id: str = "task-run-001",
    status: str = "pending",
) -> Task:
    now = datetime.now(UTC)
    task = Task(
        task_id=task_id,
        status=status,
        customer_scope=["客户A"],
        triggered_by="test-op",
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    return task


class TestRunScrapeTaskSuccess:
    @patch("app.services.scrape_task_runner.execute_list_scrape_via_api_from_parsed")
    @patch("app.services.scrape_task_runner.parse_job_cards_from_api")
    @patch("app.services.scrape_task_runner.fetch_51job_api_with_playwright")
    def test_successful_scrape_cycle(
        self,
        mock_api_fetch,
        mock_parse_api,
        mock_execute_api,
        db_session: Session,
    ) -> None:
        _create_task(db_session)
        mock_api_fetch.return_value = RetryResult(
            success=True,
            result={"jobs": [{"jobId": "123"}]},
            total_attempts=1,
        )
        mock_parse_api.return_value = SimpleNamespace(
            cards=[{"job_id": "123"}],
            total_found=1,
            errors=[],
        )
        mock_execute_api.return_value = ScrapeOutcome(
            task_id="task-run-001",
            total_cards_found=1,
            total_persisted=1,
        )

        outcome = run_scrape_task(
            db=db_session,
            task_id="task-run-001",
            search_url="https://search.51job.com/list/",
            operator="test-op",
        )

        assert outcome.total_persisted == 1
        task = db_session.query(Task).filter(Task.task_id == "task-run-001").first()
        assert task.status == "success"

    @patch("app.services.scrape_task_runner.execute_list_scrape_via_api_from_parsed")
    @patch("app.services.scrape_task_runner.parse_job_cards_from_api")
    @patch("app.services.scrape_task_runner.fetch_51job_api_with_playwright")
    def test_task_transitions_pending_to_running_to_success(
        self,
        mock_api_fetch,
        mock_parse_api,
        mock_execute_api,
        db_session: Session,
    ) -> None:
        _create_task(db_session, status="pending")
        mock_api_fetch.return_value = RetryResult(
            success=True,
            result={"jobs": [{"jobId": "123"}]},
            total_attempts=1,
        )
        mock_parse_api.return_value = SimpleNamespace(
            cards=[{"job_id": "123"}],
            total_found=1,
            errors=[],
        )
        mock_execute_api.return_value = ScrapeOutcome(
            task_id="task-run-001",
            total_cards_found=1,
            total_persisted=1,
        )

        run_scrape_task(
            db=db_session,
            task_id="task-run-001",
            search_url="https://search.51job.com/list/",
        )

        # Check that task.started event was recorded
        events = db_session.query(TaskEvent).filter(
            TaskEvent.task_id == "task-run-001"
        ).all()
        event_types = [e.event_type for e in events]
        assert "task.started" in event_types
        assert "task.completed" in event_types


class TestRunScrapeTaskFailure:
    @patch("app.services.scrape_task_runner.fetch_51job_api_with_playwright")
    def test_fetch_failure_transitions_to_failed(
        self,
        mock_api_fetch,
        db_session: Session,
    ) -> None:
        _create_task(db_session, status="running")
        mock_api_fetch.return_value = RetryResult(
            success=False,
            total_attempts=3,
            attempts=[
                RetryAttempt(1, 1.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:00Z"),
                RetryAttempt(2, 3.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:01Z"),
                RetryAttempt(3, 9.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:04Z"),
            ],
            final_error_code="NET_TIMEOUT",
            final_error_message="超时",
        )

        with pytest.raises(ScrapeServiceError) as exc_info:
            run_scrape_task(
                db=db_session,
                task_id="task-run-001",
                search_url="https://search.51job.com/list/",
            )

        assert "重试" in exc_info.value.message

        task = db_session.query(Task).filter(Task.task_id == "task-run-001").first()
        assert task.status == "failed"

    @patch("app.services.scrape_task_runner.execute_list_scrape_via_api_from_parsed")
    @patch("app.services.scrape_task_runner.parse_job_cards_from_api")
    @patch("app.services.scrape_task_runner.fetch_51job_api_with_playwright")
    def test_api_mode_success_keeps_state_machine_and_no_detail_failed_event(
        self,
        mock_api_fetch,
        mock_parse_api,
        mock_execute_api,
        db_session: Session,
    ) -> None:
        _create_task(db_session, status="running")
        mock_api_fetch.return_value = RetryResult(
            success=True,
            result={"jobs": [{"jobId": "123"}]},
            total_attempts=1,
        )
        mock_parse_api.return_value = SimpleNamespace(
            cards=[{"job_id": "123"}],
            total_found=1,
            errors=[],
        )
        mock_execute_api.return_value = ScrapeOutcome(
            task_id="task-run-001",
            total_cards_found=1,
            total_persisted=1,
        )

        outcome = run_scrape_task(
            db=db_session,
            task_id="task-run-001",
            search_url="https://search.51job.com/list/",
        )

        assert outcome.detail_failed == 0
        task = db_session.query(Task).filter(Task.task_id == "task-run-001").first()
        assert task.status == "success"
        events = db_session.query(TaskEvent).filter(
            TaskEvent.task_id == "task-run-001"
        ).all()
        assert not any(e.event_type == "scrape.detail.failed" for e in events)

    @patch("app.services.scrape_task_runner.fetch_51job_api_with_playwright")
    def test_retry_attempts_recorded_in_audit(
        self,
        mock_api_fetch,
        db_session: Session,
    ) -> None:
        _create_task(db_session, status="running")
        mock_api_fetch.return_value = RetryResult(
            success=False,
            total_attempts=3,
            attempts=[
                RetryAttempt(1, 1.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:00Z"),
                RetryAttempt(2, 3.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:01Z"),
                RetryAttempt(3, 9.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:04Z"),
            ],
            final_error_code="NET_TIMEOUT",
            final_error_message="超时",
        )

        with pytest.raises(ScrapeServiceError):
            run_scrape_task(
                db=db_session,
                task_id="task-run-001",
                search_url="https://search.51job.com/list/",
            )

        events = db_session.query(TaskEvent).filter(
            TaskEvent.task_id == "task-run-001"
        ).all()
        failed_events = [e for e in events if e.event_type == "task.failed"]
        assert len(failed_events) == 1
        payload = failed_events[0].payload
        assert "retry_attempts" in payload
        assert len(payload["retry_attempts"]) == 3

    def test_task_not_found_raises(self, db_session: Session) -> None:
        with pytest.raises(TaskValidationError) as exc_info:
            run_scrape_task(
                db=db_session,
                task_id="nonexistent",
                search_url="https://search.51job.com/list/",
            )
        assert exc_info.value.code == "VAL_TASK_NOT_FOUND"

    @pytest.mark.parametrize("bad_status", ["success", "failed", "manual"])
    def test_invalid_task_status_rejected(
        self, bad_status: str, db_session: Session
    ) -> None:
        _create_task(db_session, status=bad_status)
        with pytest.raises(TaskValidationError) as exc_info:
            run_scrape_task(
                db=db_session,
                task_id="task-run-001",
                search_url="https://search.51job.com/list/",
            )
        assert exc_info.value.code == "VAL_TASK_STATUS_INVALID"


class TestRetryAuditOnSuccess:
    @patch("app.services.scrape_task_runner.execute_list_scrape_via_api_from_parsed")
    @patch("app.services.scrape_task_runner.parse_job_cards_from_api")
    @patch("app.services.scrape_task_runner.fetch_51job_api_with_playwright")
    def test_retry_event_recorded_on_eventual_success(
        self,
        mock_api_fetch,
        mock_parse_api,
        mock_execute_api,
        db_session: Session,
    ) -> None:
        _create_task(db_session, status="running")
        mock_api_fetch.return_value = RetryResult(
            success=True,
            result={"jobs": [{"jobId": "123"}]},
            total_attempts=2,
            attempts=[
                RetryAttempt(1, 1.0, "NET_TIMEOUT", "超时", "2026-03-15T00:00:00Z"),
            ],
        )
        mock_parse_api.return_value = SimpleNamespace(
            cards=[{"job_id": "123"}],
            total_found=1,
            errors=[],
        )
        mock_execute_api.return_value = ScrapeOutcome(
            task_id="task-run-001",
            total_cards_found=1,
            total_persisted=1,
        )

        run_scrape_task(
            db=db_session,
            task_id="task-run-001",
            search_url="https://search.51job.com/list/",
        )

        events = db_session.query(TaskEvent).filter(
            TaskEvent.task_id == "task-run-001"
        ).all()
        retry_events = [e for e in events if e.event_type == "scrape.fetch.retried"]
        assert len(retry_events) == 1
        assert retry_events[0].payload["outcome"] == "success"
