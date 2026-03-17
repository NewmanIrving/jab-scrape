from collections.abc import Generator

from fastapi import Header
from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_operator(
    x_operator: str | None = Header(default=None, alias="X-Operator"),
) -> str:
    if x_operator is None:
        return "system"

    normalized = x_operator.strip()
    return normalized or "system"