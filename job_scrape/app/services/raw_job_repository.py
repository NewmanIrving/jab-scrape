from datetime import datetime

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.raw_job_posting import RawJobPosting


class RawJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_posting(self, posting: RawJobPosting) -> RawJobPosting:
        self.db.add(posting)
        return posting

    def add_postings_bulk(self, postings: list[RawJobPosting]) -> list[RawJobPosting]:
        self.db.add_all(postings)
        return postings

    def count_by_task(self, task_id: str) -> int:
        return (
            self.db.query(RawJobPosting)
            .filter(RawJobPosting.task_id == task_id)
            .count()
        )

    def list_by_task(
        self,
        task_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RawJobPosting], int]:
        query = self.db.query(RawJobPosting).filter(
            RawJobPosting.task_id == task_id
        )
        total = query.count()
        postings = (
            query.order_by(RawJobPosting.id.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return postings, total

    def list_for_detail_enrichment(self, task_id: str) -> list[RawJobPosting]:
        return (
            self.db.query(RawJobPosting)
            .filter(RawJobPosting.task_id == task_id)
            .filter(RawJobPosting.source_url_raw.isnot(None))
            .order_by(RawJobPosting.id.asc())
            .all()
        )

    def apply_detail_merge_result(
        self,
        posting: RawJobPosting,
        *,
        job_description_text: str | None,
        posted_at: str | None,
        updated_at_text: str | None,
        experience_requirement_text: str | None,
        education_requirement_text: str | None,
        company_industry_text: str | None,
        posted_at_source: str | None,
        updated_at_source: str | None,
        experience_requirement_text_source: str | None,
        education_requirement_text_source: str | None,
        company_industry_text_source: str | None,
        job_description_text_source: str | None,
        parse_notes: str | None,
    ) -> RawJobPosting:
        posting.job_description_text = job_description_text
        posting.posted_at = posted_at
        posting.updated_at_text = updated_at_text
        posting.experience_requirement_text = experience_requirement_text
        posting.education_requirement_text = education_requirement_text
        posting.company_industry_text = company_industry_text

        posting.posted_at_source = posted_at_source
        posting.updated_at_source = updated_at_source
        posting.experience_requirement_text_source = experience_requirement_text_source
        posting.education_requirement_text_source = education_requirement_text_source
        posting.company_industry_text_source = company_industry_text_source
        posting.job_description_text_source = job_description_text_source

        if parse_notes:
            posting.parse_status = "partial"
            if posting.parse_notes:
                posting.parse_notes = f"{posting.parse_notes}; {parse_notes}"
            else:
                posting.parse_notes = parse_notes

        self.db.add(posting)
        return posting

    # Story 3.1: 规范化相关方法

    def list_for_normalization(
        self,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[RawJobPosting]:
        """获取需要规范化的岗位列表（未生成source_url_canonical的记录）"""
        query = self.db.query(RawJobPosting).filter(
            RawJobPosting.source_url_canonical.is_(None)
        )
        if task_id:
            query = query.filter(RawJobPosting.task_id == task_id)
        return query.order_by(RawJobPosting.id.asc()).limit(limit).all()

    def get_by_id(self, posting_id: int) -> RawJobPosting | None:
        """根据ID获取岗位记录"""
        return self.db.query(RawJobPosting).filter(
            RawJobPosting.id == posting_id
        ).first()

    def apply_normalization_result(
        self,
        posting: RawJobPosting,
        *,
        source_job_id: str | None,
        source_url_canonical: str | None,
        job_id_source: str | None,
    ) -> RawJobPosting:
        """应用规范化结果到岗位记录"""
        posting.source_job_id = source_job_id
        posting.source_url_canonical = source_url_canonical
        posting.job_id_source = job_id_source
        self.db.add(posting)
        return posting

    # Story 3.2: 生命周期统计与写入

    def get_lifecycle_stats(
        self,
        *,
        source_platform: str,
        source_job_id: str | None,
        source_url_canonical: str | None,
    ) -> tuple[datetime | None, datetime | None, int]:
        """按岗位标识汇总首次/最近出现时间与任务级出现次数。"""
        filters = self._build_identity_filters(
            source_platform=source_platform,
            source_job_id=source_job_id,
            source_url_canonical=source_url_canonical,
        )

        row = (
            self.db.query(
                func.min(RawJobPosting.scraped_at).label("first_seen_at"),
                func.max(RawJobPosting.scraped_at).label("last_seen_at"),
                func.count(distinct(RawJobPosting.task_id)).label("times_seen"),
            )
            .filter(*filters)
            .one()
        )
        return row.first_seen_at, row.last_seen_at, int(row.times_seen or 0)

    def apply_lifecycle_fields_for_task_identity(
        self,
        *,
        task_id: str,
        source_platform: str,
        source_job_id: str | None,
        source_url_canonical: str | None,
        first_seen_at: datetime,
        last_seen_at: datetime,
        times_seen: int,
    ) -> int:
        """将生命周期字段批量写回同一任务内的重复岗位记录。"""
        filters = self._build_identity_filters(
            source_platform=source_platform,
            source_job_id=source_job_id,
            source_url_canonical=source_url_canonical,
        )

        return int(
            self.db.query(RawJobPosting)
            .filter(RawJobPosting.task_id == task_id, *filters)
            .update(
                {
                    RawJobPosting.first_seen_at: first_seen_at,
                    RawJobPosting.last_seen_at: last_seen_at,
                    RawJobPosting.times_seen: times_seen,
                },
                synchronize_session=False,
            )
        )

    def _build_identity_filters(
        self,
        *,
        source_platform: str,
        source_job_id: str | None,
        source_url_canonical: str | None,
    ) -> list:
        filters = [RawJobPosting.source_platform == source_platform]
        if source_job_id:
            filters.append(RawJobPosting.source_job_id == source_job_id)
            return filters
        if source_url_canonical:
            filters.append(RawJobPosting.source_url_canonical == source_url_canonical)
            return filters
        msg = "岗位标识缺失：source_job_id 与 source_url_canonical 不能同时为空"
        raise ValueError(msg)
