import json
from datetime import datetime

from sqlalchemy import String, case, cast, func, or_
from sqlalchemy.orm import Session

from app.models import Task, TaskEvent


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_task(self, task: Task) -> Task:
        self.db.add(task)
        return task

    def add_task_event(self, event: TaskEvent) -> TaskEvent:
        self.db.add(event)
        return event

    def update_task_status_with_event(
        self,
        task: Task,
        new_status: str,
        event: TaskEvent,
    ) -> None:
        """原子性地更新任务状态并追加审计事件（调用者负责 commit）"""
        task.status = new_status
        task.updated_at = event.created_at
        self.db.add(event)

    # ------------------------------------------------------------------
    # 查询方法
    # ------------------------------------------------------------------

    def _effective_updated_at(self):
        """返回用于排序/筛选的有效时间列表达式（updated_at 优先，回退 created_at）"""
        return case(
            (Task.updated_at.isnot(None), Task.updated_at),
            else_=Task.created_at,
        )

    def list_tasks(
        self,
        customer: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        effective_time = self._effective_updated_at()
        query = self.db.query(Task)

        if customer is not None:
            normalized_customer = customer.strip()
            raw_token = json.dumps(normalized_customer, ensure_ascii=False)
            escaped_token = json.dumps(normalized_customer, ensure_ascii=True)
            query = query.filter(
                or_(
                    cast(Task.customer_scope, String).contains(raw_token),
                    cast(Task.customer_scope, String).contains(escaped_token),
                )
            )
        if start_time is not None:
            query = query.filter(effective_time >= start_time)
        if end_time is not None:
            query = query.filter(effective_time <= end_time)

        total = query.count()
        tasks = (
            query
            .order_by(effective_time.desc(), Task.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return tasks, total

    def get_task_by_id(self, task_id: str) -> Task | None:
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def count_events_for_task(self, task_id: str) -> int:
        return (
            self.db.query(func.count(TaskEvent.id))
            .filter(TaskEvent.task_id == task_id)
            .scalar()
            or 0
        )

    def list_events_for_task(
        self,
        task_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[TaskEvent], int]:
        query = self.db.query(TaskEvent).filter(TaskEvent.task_id == task_id)
        total = query.count()
        events = (
            query
            .order_by(TaskEvent.created_at.asc(), TaskEvent.id.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return events, total
