from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'success', 'failed', 'manual')",
            name="ck_tasks_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_scope: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )