from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawJobPosting(Base):
    __tablename__ = "raw_job_postings"
    __table_args__ = (
        Index(
            "ix_raw_job_postings_platform_company",
            "source_platform",
            "company_name",
        ),
        Index(
            "ix_raw_job_postings_platform_source_job_id",
            "source_platform",
            "source_job_id",
        ),
        Index(
            "ix_raw_job_postings_platform_source_url_canonical",
            "source_platform",
            "source_url_canonical",
        ),
        Index("ix_raw_job_postings_task_id", "task_id"),
        Index("ix_raw_job_postings_scraped_at", "scraped_at"),
        Index("ix_raw_job_postings_session_id", "session_id"),
        Index("ix_raw_job_postings_html_evidence_path", "html_evidence_path"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url_raw: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(String(256), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    salary_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    headcount_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    posted_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    experience_requirement_text: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    education_requirement_text: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    company_industry_text: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    job_description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    updated_at_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    experience_requirement_text_source: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    education_requirement_text_source: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    company_industry_text_source: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    job_description_text_source: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    # 扩展字段 (API数据)
    full_company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # SQLAlchemy 沿用 Integer 表示该字段（历史兼容）
    is_expire: Mapped[bool | None] = mapped_column(Integer, nullable=True)
    apply_time_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hr_active_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    parse_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ok"
    )
    parse_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_evidence_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    html_evidence_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 规范化字段 (Story 3.1)
    source_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url_canonical: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    times_seen: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Epic 2 缺失字段补齐 (Story 3.1)
    job_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    job_area_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirm_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
