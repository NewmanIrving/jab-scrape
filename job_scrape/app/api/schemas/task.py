from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    customer_scope: list[str]


class TaskCreateData(BaseModel):
    task_id: str
    status: str
    triggered_by: str
    created_at: datetime


class TaskProgress(BaseModel):
    current_status: str
    updated_at: datetime
    event_count: int


class TaskListItem(BaseModel):
    task_id: str
    status: str
    customer_scope: list[str]
    triggered_by: str
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskListItem):
    progress: TaskProgress


class TaskListMeta(BaseModel):
    total: int
    limit: int
    offset: int


class TaskEventItem(BaseModel):
    task_id: str
    session_id: str | None
    event_type: str
    operator: str
    payload: dict
    error_code: str | None
    error_message: str | None
    created_at: datetime


class ApiError(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ApiResponse(BaseModel):
    data: Any
    meta: Any
    error: ApiError | None


class ManualActionRequest(BaseModel):
    action: str
    reason: str | None = Field(default=None, max_length=500)


class ManualActionData(BaseModel):
    task_id: str
    previous_status: str
    current_status: str
    action: str
    operator: str
    updated_at: datetime
