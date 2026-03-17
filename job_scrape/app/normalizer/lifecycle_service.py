"""生命周期字段维护服务（Story 3.2）。"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.raw_job_posting import RawJobPosting
from app.models.task_event import TaskEvent
from app.services.raw_job_repository import RawJobRepository
from app.services.task_repository import TaskRepository

logger = logging.getLogger(__name__)


@dataclass
class LifecycleUpdateResult:
    posting_id: int
    success: bool
    skipped: bool
    identity_type: str | None
    identity_value: str | None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    times_seen: int | None = None
    updated_rows: int = 0
    error_message: str | None = None


class LifecycleService:
    """维护 raw_job_postings 生命周期字段。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.raw_repo = RawJobRepository(db)
        self.task_repo = TaskRepository(db)

    def update_posting_lifecycle(
        self,
        posting_id: int,
        task_id: str | None = None,
    ) -> LifecycleUpdateResult:
        posting = self.raw_repo.get_by_id(posting_id)
        if not posting:
            return LifecycleUpdateResult(
                posting_id=posting_id,
                success=False,
                skipped=False,
                identity_type=None,
                identity_value=None,
                error_message=f"岗位记录不存在: {posting_id}",
            )

        resolved_task_id = task_id or posting.task_id
        identity_type, identity_value = self._resolve_identity(posting)

        if not identity_type or not identity_value:
            self._record_identity_missing_event(
                posting=posting,
                task_id=resolved_task_id,
            )
            self.db.commit()
            return LifecycleUpdateResult(
                posting_id=posting_id,
                success=False,
                skipped=True,
                identity_type=None,
                identity_value=None,
                error_message="岗位标识缺失",
            )

        try:
            first_seen_at, last_seen_at, times_seen = self.raw_repo.get_lifecycle_stats(
                source_platform=posting.source_platform,
                source_job_id=(
                    identity_value if identity_type == "source_job_id" else None
                ),
                source_url_canonical=(
                    identity_value
                    if identity_type == "source_url_canonical"
                    else None
                ),
            )

            reference_time = posting.scraped_at or datetime.now(UTC)
            first_seen_at = first_seen_at or reference_time
            last_seen_at = last_seen_at or reference_time
            times_seen = max(times_seen, 1)

            updated_rows = self.raw_repo.apply_lifecycle_fields_for_task_identity(
                task_id=resolved_task_id,
                source_platform=posting.source_platform,
                source_job_id=(
                    identity_value if identity_type == "source_job_id" else None
                ),
                source_url_canonical=(
                    identity_value
                    if identity_type == "source_url_canonical"
                    else None
                ),
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                times_seen=times_seen,
            )

            self._record_seen_updated_event(
                posting_id=posting.id,
                task_id=resolved_task_id,
                source_platform=posting.source_platform,
                identity_type=identity_type,
                identity_value=identity_value,
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                times_seen=times_seen,
                updated_rows=updated_rows,
            )
            self.db.commit()

            return LifecycleUpdateResult(
                posting_id=posting_id,
                success=True,
                skipped=False,
                identity_type=identity_type,
                identity_value=identity_value,
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                times_seen=times_seen,
                updated_rows=updated_rows,
            )
        except Exception as exc:
            self.db.rollback()
            logger.exception("生命周期更新失败 posting_id=%s", posting_id)
            self._record_seen_failed_event(
                posting_id=posting_id,
                task_id=resolved_task_id,
                source_platform=posting.source_platform,
                identity_type=identity_type,
                identity_value=identity_value,
                error_message=str(exc),
            )
            self.db.commit()
            return LifecycleUpdateResult(
                posting_id=posting_id,
                success=False,
                skipped=False,
                identity_type=identity_type,
                identity_value=identity_value,
                error_message=str(exc),
            )

    def _resolve_identity(
        self,
        posting: RawJobPosting,
    ) -> tuple[str | None, str | None]:
        if posting.source_job_id:
            return "source_job_id", posting.source_job_id
        if posting.source_url_canonical:
            return "source_url_canonical", posting.source_url_canonical
        return None, None

    def _record_identity_missing_event(
        self,
        *,
        posting: RawJobPosting,
        task_id: str,
    ) -> None:
        now = datetime.now(UTC)
        event = TaskEvent(
            task_id=task_id,
            event_type="lifecycle.identity.missing",
            operator="system",
            payload={
                "posting_id": posting.id,
                "source_platform": posting.source_platform,
                "source_job_id": posting.source_job_id,
                "source_url_canonical": posting.source_url_canonical,
                "task_id": task_id,
                "timestamp": now.isoformat(),
            },
            created_at=now,
        )
        self.task_repo.add_task_event(event)

    def _record_seen_updated_event(
        self,
        *,
        posting_id: int,
        task_id: str,
        source_platform: str,
        identity_type: str,
        identity_value: str,
        first_seen_at: datetime,
        last_seen_at: datetime,
        times_seen: int,
        updated_rows: int,
    ) -> None:
        now = datetime.now(UTC)
        event = TaskEvent(
            task_id=task_id,
            event_type="lifecycle.seen.updated",
            operator="system",
            payload={
                "posting_id": posting_id,
                "source_platform": source_platform,
                "identity_type": identity_type,
                "identity_value": identity_value,
                "first_seen_at": first_seen_at.isoformat(),
                "last_seen_at": last_seen_at.isoformat(),
                "times_seen": times_seen,
                "updated_rows": updated_rows,
                "task_id": task_id,
                "timestamp": now.isoformat(),
            },
            created_at=now,
        )
        self.task_repo.add_task_event(event)

    def _record_seen_failed_event(
        self,
        *,
        posting_id: int,
        task_id: str,
        source_platform: str,
        identity_type: str | None,
        identity_value: str | None,
        error_message: str,
    ) -> None:
        now = datetime.now(UTC)
        event = TaskEvent(
            task_id=task_id,
            event_type="lifecycle.seen.failed",
            operator="system",
            payload={
                "posting_id": posting_id,
                "source_platform": source_platform,
                "identity_type": identity_type,
                "identity_value": identity_value,
                "error_message": error_message,
                "task_id": task_id,
                "timestamp": now.isoformat(),
            },
            created_at=now,
        )
        self.task_repo.add_task_event(event)
