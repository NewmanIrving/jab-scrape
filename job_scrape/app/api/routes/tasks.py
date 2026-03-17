import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_operator, get_db
from app.api.schemas.task import (
    ApiResponse,
    ManualActionData,
    ManualActionRequest,
    TaskCreateData,
    TaskCreateRequest,
    TaskDetail,
    TaskEventItem,
    TaskListItem,
    TaskListMeta,
    TaskProgress,
)
from app.services.task_service import (
    TaskValidationError,
    apply_manual_action,
    create_task,
    get_task,
    get_task_events,
    list_tasks,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "meta": None,
            "error": {"code": code, "message": message, "details": {}},
        },
    )


def _effective_updated_at(task) -> datetime:
    return task.updated_at if task.updated_at is not None else task.created_at


@router.post("/tasks", response_model=ApiResponse, status_code=201)
def create_task_endpoint(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_operator: str = Depends(get_current_operator),
) -> ApiResponse | JSONResponse:
    try:
        task = create_task(
            db=db,
            customer_scope=payload.customer_scope,
            operator=current_operator,
        )
    except TaskValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "meta": None,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": {},
                },
            },
        )
    except SQLAlchemyError:
        logger.exception("database error while creating task")
        return JSONResponse(
            status_code=500,
            content={
                "data": None,
                "meta": None,
                "error": {
                    "code": "INT_TASK_CREATE_FAILED",
                    "message": "任务创建失败",
                    "details": {},
                },
            },
        )

    return ApiResponse(
        data=TaskCreateData(
            task_id=task.task_id,
            status=task.status,
            triggered_by=task.triggered_by,
            created_at=task.created_at,
        ),
        meta=None,
        error=None,
    )


@router.get("/tasks", response_model=ApiResponse)
def list_tasks_endpoint(
    customer: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_operator: str = Depends(get_current_operator),
) -> ApiResponse | JSONResponse:
    try:
        result = list_tasks(
            db=db,
            customer=customer,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
    except TaskValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "meta": None,
                "error": {"code": exc.code, "message": exc.message, "details": {}},
            },
        )

    items = [
        TaskListItem(
            task_id=t.task_id,
            status=t.status,
            customer_scope=t.customer_scope,
            triggered_by=t.triggered_by,
            created_at=t.created_at,
            updated_at=_effective_updated_at(t),
        )
        for t in result.tasks
    ]

    return ApiResponse(
        data=[item.model_dump() for item in items],
        meta=TaskListMeta(
            total=result.total,
            limit=result.limit,
            offset=result.offset,
        ).model_dump(),
        error=None,
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse)
def get_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_operator: str = Depends(get_current_operator),
) -> ApiResponse | JSONResponse:
    try:
        task, event_count = get_task(db=db, task_id=task_id)
    except TaskValidationError as exc:
        return JSONResponse(
            status_code=404,
            content={
                "data": None,
                "meta": None,
                "error": {"code": exc.code, "message": exc.message, "details": {}},
            },
        )

    eff_updated_at = _effective_updated_at(task)
    detail = TaskDetail(
        task_id=task.task_id,
        status=task.status,
        customer_scope=task.customer_scope,
        triggered_by=task.triggered_by,
        created_at=task.created_at,
        updated_at=eff_updated_at,
        progress=TaskProgress(
            current_status=task.status,
            updated_at=eff_updated_at,
            event_count=event_count,
        ),
    )

    return ApiResponse(
        data=detail.model_dump(),
        meta=None,
        error=None,
    )


@router.get("/tasks/{task_id}/events", response_model=ApiResponse)
def list_task_events_endpoint(
    task_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_operator: str = Depends(get_current_operator),
) -> ApiResponse | JSONResponse:
    try:
        result = get_task_events(
            db=db,
            task_id=task_id,
            limit=limit,
            offset=offset,
        )
    except TaskValidationError as exc:
        return _error_response(
            status_code=404,
            code=exc.code,
            message=exc.message,
        )

    items = []
    for event in result.events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        items.append(
            TaskEventItem(
                task_id=event.task_id,
                session_id=payload.get("session_id"),
                event_type=event.event_type,
                operator=event.operator,
                payload=payload,
                error_code=payload.get("error_code"),
                error_message=payload.get("error_message"),
                created_at=event.created_at,
            )
        )

    return ApiResponse(
        data=[item.model_dump() for item in items],
        meta=TaskListMeta(
            total=result.total,
            limit=result.limit,
            offset=result.offset,
        ).model_dump(),
        error=None,
    )


# 错误码 → HTTP 状态码映射（manual 动作专用）
_MANUAL_ERROR_STATUS: dict[str, int] = {
    "VAL_TASK_NOT_FOUND": 404,
    "VAL_MANUAL_ACTION_INVALID": 422,
    "VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION": 409,
}


@router.post("/tasks/{task_id}/actions/manual", response_model=ApiResponse)
def manual_action_endpoint(
    task_id: str,
    payload: ManualActionRequest,
    db: Session = Depends(get_db),
    current_operator: str = Depends(get_current_operator),
) -> ApiResponse | JSONResponse:
    try:
        task, previous_status = apply_manual_action(
            db=db,
            task_id=task_id,
            action=payload.action,
            reason=payload.reason,
            operator=current_operator,
        )
    except TaskValidationError as exc:
        status_code = _MANUAL_ERROR_STATUS.get(exc.code, 422)
        return _error_response(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
        )
    except SQLAlchemyError:
        logger.exception("database error on manual action task=%s", task_id)
        return _error_response(
            status_code=500,
            code="INT_TASK_MANUAL_ACTION_FAILED",
            message="执行动作失败",
        )

    eff_updated_at = _effective_updated_at(task)
    data = ManualActionData(
        task_id=task.task_id,
        previous_status=previous_status,
        current_status=task.status,
        action=payload.action,
        operator=current_operator,
        updated_at=eff_updated_at,
    )
    return ApiResponse(data=data.model_dump(), meta=None, error=None)
