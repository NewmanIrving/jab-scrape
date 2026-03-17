from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Task, TaskEvent
from app.services.task_repository import TaskRepository


class TaskValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _normalize_utc_time(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise TaskValidationError(
            "VAL_INVALID_TIME_FORMAT",
            f"{field_name} 必须为带时区的 ISO8601 UTC 时间",
        )

    if value.utcoffset() != UTC.utcoffset(value):
        raise TaskValidationError(
            "VAL_INVALID_TIMEZONE",
            f"{field_name} 必须使用 UTC 时区",
        )

    return value.astimezone(UTC)


def create_task(db: Session, customer_scope: list[str], operator: str) -> Task:
    normalized_scope = [
        item.strip() for item in customer_scope if item and item.strip()
    ]
    if not normalized_scope:
        raise TaskValidationError("VAL_CUSTOMER_SCOPE_EMPTY", "客户范围不能为空")

    created_at = datetime.now(UTC)
    task = Task(
        task_id=str(uuid4()),
        status="pending",
        customer_scope=normalized_scope,
        triggered_by=operator,
        created_at=created_at,
        updated_at=created_at,
    )
    task_event = TaskEvent(
        task_id=task.task_id,
        event_type="task.created",
        operator=operator,
        payload={"customer_scope_count": len(normalized_scope)},
        created_at=created_at,
    )

    repository = TaskRepository(db)

    try:
        repository.add_task(task)
        repository.add_task_event(task_event)
        db.commit()
        db.refresh(task)
    except SQLAlchemyError:
        db.rollback()
        raise

    return task


# ------------------------------------------------------------------
# 查询服务
# ------------------------------------------------------------------

class TaskQueryResult:
    """列表查询结果载体"""
    def __init__(self, tasks: list[Task], total: int, limit: int, offset: int) -> None:
        self.tasks = tasks
        self.total = total
        self.limit = limit
        self.offset = offset


class TaskEventsQueryResult:
    def __init__(
        self,
        events: list[TaskEvent],
        total: int,
        limit: int,
        offset: int,
    ) -> None:
        self.events = events
        self.total = total
        self.limit = limit
        self.offset = offset


def list_tasks(
    db: Session,
    customer: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> TaskQueryResult:
    if start_time is not None:
        start_time = _normalize_utc_time(start_time, "start_time")
    if end_time is not None:
        end_time = _normalize_utc_time(end_time, "end_time")

    if (
        start_time is not None
        and end_time is not None
        and start_time > end_time
    ):
        raise TaskValidationError(
            "VAL_INVALID_TIME_RANGE", "start_time 不能晚于 end_time"
        )

    repository = TaskRepository(db)
    tasks, total = repository.list_tasks(
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return TaskQueryResult(tasks=tasks, total=total, limit=limit, offset=offset)


def get_task(
    db: Session,
    task_id: str,
) -> tuple[Task, int]:
    """返回 (task, event_count)；任务不存在则抛出 TaskValidationError"""
    repository = TaskRepository(db)
    task = repository.get_task_by_id(task_id)
    if task is None:
        raise TaskValidationError("VAL_TASK_NOT_FOUND", "任务不存在")
    event_count = repository.count_events_for_task(task_id)
    return task, event_count


def get_task_events(
    db: Session,
    task_id: str,
    limit: int = 50,
    offset: int = 0,
) -> TaskEventsQueryResult:
    repository = TaskRepository(db)
    task = repository.get_task_by_id(task_id)
    if task is None:
        raise TaskValidationError("VAL_TASK_NOT_FOUND", "任务不存在")

    events, total = repository.list_events_for_task(
        task_id=task_id,
        limit=limit,
        offset=offset,
    )
    return TaskEventsQueryResult(
        events=events,
        total=total,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# Manual 动作服务
# ------------------------------------------------------------------

_VALID_MANUAL_ACTIONS: dict[str, str] = {
    "replay": "pending",
    "skip": "failed",
}


def apply_manual_action(
    db: Session,
    task_id: str,
    action: str,
    reason: str | None,
    operator: str,
) -> tuple[Task, str]:
    """执行 manual 动作（replay/skip），返回 (更新后的 task, previous_status)。

    错误时抛出 TaskValidationError；数据库异常时 rollback 后继续上抛。
    """
    if action not in _VALID_MANUAL_ACTIONS:
        raise TaskValidationError(
            "VAL_MANUAL_ACTION_INVALID",
            "不支持的动作，允许值为 replay 或 skip",
        )

    repository = TaskRepository(db)
    task = repository.get_task_by_id(task_id)
    if task is None:
        raise TaskValidationError("VAL_TASK_NOT_FOUND", "任务不存在")

    if task.status != "manual":
        raise TaskValidationError(
            "VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION",
            f"任务当前状态 {task.status!r} 不允许执行 manual 动作",
        )

    new_status = _VALID_MANUAL_ACTIONS[action]
    previous_status = task.status
    now = datetime.now(UTC)

    event = TaskEvent(
        task_id=task_id,
        event_type=f"task.manual.{action}",
        operator=operator,
        payload={
            "task_id": task_id,
            "session_id": None,
            "action": action,
            "reason": reason,
            "from_status": previous_status,
            "to_status": new_status,
            "timestamp": now.isoformat(),
        },
        created_at=now,
    )

    try:
        repository.update_task_status_with_event(task, new_status, event)
        db.commit()
        db.refresh(task)
    except SQLAlchemyError:
        db.rollback()
        raise

    return task, previous_status
