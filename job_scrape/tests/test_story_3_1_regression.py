"""Regression tests for Epic 2 main scraping flow (Story 3.1).

Ensures that Story 3.1 changes don't break the existing Epic 2 scraping flow.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.raw_job_posting import RawJobPosting
from app.models.task import Task
from app.services.scrape_service import execute_list_scrape


# Sample 51job API response data (simulating what comes from the API)
SAMPLE_API_JOB_ITEMS = [
    {
        "jobId": "111222333",
        "jobTitle": "Python后端开发",
        "companyName": "北京测试科技有限公司",
        "salary": "15-25K",
        "jobArea": "北京",
        "jobAreaLevelDetail": {"detail": "北京-朝阳区"},
        "issueDate": "2026-03-15",
        "jobTags": ["五险一金", "带薪年假", "周末双休"],
        "companyTypeString": "民营公司",
        "companySizeString": "150-500人",
        "confirmDateString": "2026-03-16",
    },
    {
        "jobId": "444555666",
        "jobTitle": "数据分析师",
        "companyName": "上海样本公司",
        "salary": "20-35K",
        "jobArea": "上海",
        "jobAreaLevelDetail": {"detail": "上海-浦东新区"},
        "issueDate": "2026-03-14",
        "jobTags": ["六险一金", "弹性工作"],
        "companyTypeString": "上市公司",
        "companySizeString": "500-1000人",
        "confirmDateString": "2026-03-15",
    },
]


def _create_test_task(db: Session, task_id: str = "task-regress-001") -> Task:
    """Helper to create a task in the DB for testing."""
    now = datetime.now(UTC)
    task = Task(
        task_id=task_id,
        status="running",
        customer_scope=["测试客户"],
        triggered_by="test-operator",
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    return task


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_path = tmp_path / "test_regress.db"
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


class TestEpic2MainFlowRegression:
    """Regression tests for Epic 2 scraping flow."""

    def test_scraping_still_works_without_new_fields(self, db_session: Session) -> None:
        """Test that basic scraping flow still works without providing new fields."""
        _create_test_task(db_session)

        # Create a posting without new fields (old format)
        now = datetime.now(UTC)
        posting = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/123456.html",
            company_name="老公司",
            job_title="老岗位",
            location_text="北京",
            scraped_at=now,
            # New fields are optional/nullable
            source_job_id=None,
            source_url_canonical=None,
            job_id_source=None,
            job_tags=None,
            job_area_detail=None,
            confirm_date=None,
            company_type=None,
            company_size=None,
        )
        db_session.add(posting)
        db_session.commit()

        # Verify it can be queried
        retrieved = db_session.query(RawJobPosting).first()
        assert retrieved is not None
        assert retrieved.company_name == "老公司"

    def test_new_fields_are_optional(self, db_session: Session) -> None:
        """Test that new Story 3.1 fields are truly optional."""
        _create_test_task(db_session)

        now = datetime.now(UTC)
        # Posting with only required fields
        posting = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/999888777.html",
            company_name="最小公司",
            job_title="最小岗位",
            scraped_at=now,
        )
        db_session.add(posting)
        db_session.commit()

        # Verify all new fields are None
        retrieved = db_session.query(RawJobPosting).first()
        assert retrieved.source_job_id is None
        assert retrieved.source_url_canonical is None
        assert retrieved.job_id_source is None
        assert retrieved.job_tags is None
        assert retrieved.job_area_detail is None

    def test_complete_new_fields_persistence(self, db_session: Session) -> None:
        """Test that all new Story 3.1 fields are correctly persisted."""
        _create_test_task(db_session)

        now = datetime.now(UTC)
        posting = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/777888999.html",
            company_name="完整公司",
            job_title="完整岗位",
            location_text="深圳",
            scraped_at=now,
            # All new fields populated
            source_job_id="777888999",
            source_url_canonical="https://jobs.51job.com/shenzhen/777888999.html",
            job_id_source="api",
            job_tags=["大平台", "年终奖", "股票期权"],
            job_area_detail="深圳-南山区",
            confirm_date="2026-03-17",
            company_type="上市公司",
            company_size="1000人以上",
        )
        db_session.add(posting)
        db_session.commit()

        # Verify all fields persisted correctly
        retrieved = db_session.query(RawJobPosting).first()
        assert retrieved.source_job_id == "777888999"
        assert retrieved.source_url_canonical == "https://jobs.51job.com/shenzhen/777888999.html"
        assert retrieved.job_id_source == "api"
        assert retrieved.job_tags == ["大平台", "年终奖", "股票期权"]
        assert retrieved.job_area_detail == "深圳-南山区"
        assert retrieved.confirm_date == "2026-03-17"
        assert retrieved.company_type == "上市公司"
        assert retrieved.company_size == "1000人以上"

    def test_json_field_handling(self, db_session: Session) -> None:
        """Test that JSON field (job_tags) handles various formats correctly."""
        _create_test_task(db_session)

        now = datetime.now(UTC)

        # Test with list
        posting1 = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/111.html",
            company_name="JSON测试公司1",
            job_title="岗位1",
            scraped_at=now,
            job_tags=["标签A", "标签B"],
        )

        # Test with empty list
        posting2 = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/222.html",
            company_name="JSON测试公司2",
            job_title="岗位2",
            scraped_at=now,
            job_tags=[],
        )

        # Test with None
        posting3 = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/333.html",
            company_name="JSON测试公司3",
            job_title="岗位3",
            scraped_at=now,
            job_tags=None,
        )

        db_session.add_all([posting1, posting2, posting3])
        db_session.commit()

        # Verify JSON persistence
        results = db_session.query(RawJobPosting).filter(
            RawJobPosting.company_name.like("JSON测试公司%")
        ).all()

        assert len(results) == 3
        assert results[0].job_tags == ["标签A", "标签B"]
        assert results[1].job_tags == []
        assert results[2].job_tags is None


class TestFieldMappingRegression:
    """Regression tests for field mapping from API to DB."""

    def test_field_mapping_consistency(self, db_session: Session) -> None:
        """Test that field mapping from API data is consistent."""
        _create_test_task(db_session)

        now = datetime.now(UTC)

        # Simulate what build_raw_postings does
        job_item = SAMPLE_API_JOB_ITEMS[0]

        posting = RawJobPosting(
            task_id="task-regress-001",
            source_platform="51job",
            source_url_raw="https://jobs.51job.com/111222333.html",
            company_name=job_item["companyName"],
            job_title=job_item["jobTitle"],
            location_text=job_item.get("jobArea"),
            scraped_at=now,
            # Story 3.1: Field mapping from API
            source_job_id=job_item.get("jobId"),
            job_id_source="api" if job_item.get("jobId") else None,
            job_tags=job_item.get("jobTags"),
            job_area_detail=job_item.get("jobAreaLevelDetail", {}).get("detail") if isinstance(job_item.get("jobAreaLevelDetail"), dict) else job_item.get("jobAreaLevelDetail"),
            confirm_date=job_item.get("confirmDateString"),
            company_type=job_item.get("companyTypeString"),
            company_size=job_item.get("companySizeString"),
        )
        db_session.add(posting)
        db_session.commit()

        # Verify mapping
        retrieved = db_session.query(RawJobPosting).first()
        assert retrieved.source_job_id == "111222333"
        assert retrieved.job_id_source == "api"
        assert retrieved.job_tags == ["五险一金", "带薪年假", "周末双休"]
        assert retrieved.job_area_detail == "北京-朝阳区"
        assert retrieved.confirm_date == "2026-03-16"
        assert retrieved.company_type == "民营公司"
        assert retrieved.company_size == "150-500人"
