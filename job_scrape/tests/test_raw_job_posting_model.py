"""Tests for the RawJobPosting model and migration (Story 2.1 - Task 1)."""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.raw_job_posting import RawJobPosting


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


def test_raw_job_postings_table_created(db_session: Session) -> None:
    """raw_job_postings table should exist after metadata.create_all."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    assert "raw_job_postings" in tables


def test_raw_job_postings_indexes_exist(db_session: Session) -> None:
    """Required indexes should exist on the table."""
    inspector = inspect(db_session.bind)
    indexes = inspector.get_indexes("raw_job_postings")
    index_names = {idx["name"] for idx in indexes}
    assert "ix_raw_job_postings_task_id" in index_names
    assert "ix_raw_job_postings_platform_company" in index_names
    assert "ix_raw_job_postings_platform_source_job_id" in index_names
    assert "ix_raw_job_postings_platform_source_url_canonical" in index_names
    assert "ix_raw_job_postings_scraped_at" in index_names
    assert "ix_raw_job_postings_session_id" in index_names


def test_insert_raw_job_posting_with_required_fields(db_session: Session) -> None:
    """Should insert a record with all required baseline fields."""
    now = datetime.now(UTC)
    posting = RawJobPosting(
        task_id="task-001",
        session_id="sess-001",
        source_platform="51job",
        source_url_raw="https://search.51job.com/list/...",
        company_name="测试公司",
        job_title="Python开发工程师",
        scraped_at=now,
        parse_status="ok",
    )
    db_session.add(posting)
    db_session.commit()
    db_session.refresh(posting)

    assert posting.id is not None
    assert posting.task_id == "task-001"
    assert posting.source_platform == "51job"
    assert posting.company_name == "测试公司"
    assert posting.job_title == "Python开发工程师"
    assert posting.salary_text is None
    assert posting.location_text is None


def test_insert_raw_job_posting_with_all_visible_fields(db_session: Session) -> None:
    """Should insert a record with all list-page visible fields populated."""
    now = datetime.now(UTC)
    posting = RawJobPosting(
        task_id="task-002",
        source_platform="51job",
        source_url_raw="https://search.51job.com/list/...",
        company_name="样本公司A",
        job_title="数据分析师",
        salary_text="15-25K",
        location_text="上海-浦东新区",
        headcount_text="招3人",
        posted_at="03-15发布",
        updated_at_text="2026-03-15",
        experience_requirement_text="3-5年经验",
        education_requirement_text="本科",
        company_industry_text="互联网/电子商务",
        job_description_text="负责后端系统开发",
        posted_at_source="detail",
        updated_at_source="detail",
        experience_requirement_text_source="detail",
        education_requirement_text_source="detail",
        company_industry_text_source="detail",
        job_description_text_source="detail",
        scraped_at=now,
        parse_status="ok",
    )
    db_session.add(posting)
    db_session.commit()
    db_session.refresh(posting)

    assert posting.salary_text == "15-25K"
    assert posting.location_text == "上海-浦东新区"
    assert posting.headcount_text == "招3人"
    assert posting.experience_requirement_text == "3-5年经验"
    assert posting.education_requirement_text == "本科"
    assert posting.company_industry_text == "互联网/电子商务"
    assert posting.job_description_text == "负责后端系统开发"
    assert posting.posted_at_source == "detail"
    assert posting.updated_at_source == "detail"
    assert posting.experience_requirement_text_source == "detail"
    assert posting.education_requirement_text_source == "detail"
    assert posting.company_industry_text_source == "detail"
    assert posting.job_description_text_source == "detail"


def test_parse_status_records_failure(db_session: Session) -> None:
    """Should allow recording parse failures with notes."""
    now = datetime.now(UTC)
    posting = RawJobPosting(
        task_id="task-003",
        source_platform="51job",
        source_url_raw="https://search.51job.com/list/...",
        company_name="异常公司",
        job_title="未知岗位",
        scraped_at=now,
        parse_status="partial",
        parse_notes="salary_text: 解析失败 - 元素不存在",
    )
    db_session.add(posting)
    db_session.commit()
    db_session.refresh(posting)

    assert posting.parse_status == "partial"
    assert "解析失败" in posting.parse_notes


def test_utc_timestamp_preserved(db_session: Session) -> None:
    """scraped_at should preserve UTC timezone."""
    now = datetime.now(UTC)
    posting = RawJobPosting(
        task_id="task-004",
        source_platform="51job",
        source_url_raw="https://search.51job.com/list/...",
        company_name="时间公司",
        job_title="测试岗",
        scraped_at=now,
        parse_status="ok",
    )
    db_session.add(posting)
    db_session.commit()
    db_session.refresh(posting)

    # SQLite loses timezone info, but the value should be close to now
    delta_seconds = abs(
        (
            posting.scraped_at.replace(tzinfo=None)
            - now.replace(tzinfo=None)
        ).total_seconds()
    )
    assert delta_seconds < 2


def test_story_3_2_lifecycle_fields_are_nullable(db_session: Session) -> None:
    """Story 3.2 lifecycle fields should be nullable for historical rows."""
    posting = RawJobPosting(
        task_id="task-005",
        source_platform="51job",
        source_url_raw="https://jobs.51job.com/beijing/50005.html",
        company_name="历史兼容公司",
        job_title="历史岗位",
        scraped_at=datetime.now(UTC),
    )
    db_session.add(posting)
    db_session.commit()
    db_session.refresh(posting)

    assert posting.first_seen_at is None
    assert posting.last_seen_at is None
    assert posting.times_seen is None
