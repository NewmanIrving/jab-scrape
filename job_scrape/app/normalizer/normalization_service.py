"""规范化编排服务

协调URL规范化、job_id提取、数据库更新与事件记录。
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.task_event import TaskEvent
from app.normalizer.lifecycle_service import LifecycleService
from app.normalizer.url_normalizer import normalize_url_51job
from app.services.raw_job_repository import RawJobRepository
from app.services.task_repository import TaskRepository

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    """规范化操作结果"""

    posting_id: int
    success: bool
    source_job_id: Optional[str]
    source_url_canonical: Optional[str]
    job_id_source: Optional[str]  # "api" | "url_parse"
    error_message: Optional[str] = None


class NormalizationService:
    """规范化服务"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.raw_repo = RawJobRepository(db)
        self.task_repo = TaskRepository(db)
        self.lifecycle_service = LifecycleService(db)

    def normalize_posting(
        self,
        posting_id: int,
        task_id: Optional[str] = None,
    ) -> NormalizationResult:
        """规范化单个岗位记录

        执行流程：
        1. 检查source_job_id是否已存在
        2. 若不存在，从URL提取并更新job_id_source为url_parse
        3. 生成source_url_canonical
        4. 更新数据库记录
        5. 记录审计事件

        Args:
            posting_id: 岗位记录ID
            task_id: 任务ID（用于事件记录）

        Returns:
            NormalizationResult: 规范化结果
        """
        # 获取岗位记录
        posting = self.raw_repo.get_by_id(posting_id)
        if not posting:
            return NormalizationResult(
                posting_id=posting_id,
                success=False,
                source_job_id=None,
                source_url_canonical=None,
                job_id_source=None,
                error_message=f"岗位记录不存在: {posting_id}",
            )

        # Step 1: 检查source_job_id是否已存在
        source_job_id = posting.source_job_id
        job_id_source = posting.job_id_source

        if not source_job_id:
            # Step 2: 从URL提取job_id（兜底逻辑）
            extracted_id, error_msg = self._extract_job_id_from_url(
                posting.source_url_raw
            )
            if extracted_id:
                source_job_id = extracted_id
                job_id_source = "url_parse"
            else:
                # 提取失败，记录事件
                self._record_normalization_failed_event(
                    posting_id=posting_id,
                    task_id=task_id or posting.task_id,
                    source_url_raw=posting.source_url_raw,
                    error_message=error_msg,
                )
                self.db.commit()
                self._apply_lifecycle_update_non_blocking(
                    posting_id=posting_id,
                    task_id=task_id or posting.task_id,
                )
                return NormalizationResult(
                    posting_id=posting_id,
                    success=False,
                    source_job_id=None,
                    source_url_canonical=None,
                    job_id_source=None,
                    error_message=error_msg,
                )

        # Step 3: 生成规范化URL
        source_url_canonical = normalize_url_51job(
            job_id=source_job_id,
            location_text=posting.location_text,
        )

        # Step 4: 更新数据库
        self.raw_repo.apply_normalization_result(
            posting,
            source_job_id=source_job_id,
            source_url_canonical=source_url_canonical,
            job_id_source=job_id_source,
        )

        # Step 5: 记录审计事件
        self._record_normalization_completed_event(
            posting_id=posting_id,
            task_id=task_id or posting.task_id,
            source_url_raw=posting.source_url_raw,
            source_url_canonical=source_url_canonical,
            source_job_id=source_job_id,
            job_id_source=job_id_source,
        )

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"提交规范化结果失败: {e}")
            return NormalizationResult(
                posting_id=posting_id,
                success=False,
                source_job_id=source_job_id,
                source_url_canonical=source_url_canonical,
                job_id_source=job_id_source,
                error_message=f"数据库提交失败: {e}",
            )

        self._apply_lifecycle_update_non_blocking(
            posting_id=posting_id,
            task_id=task_id or posting.task_id,
        )

        return NormalizationResult(
            posting_id=posting_id,
            success=True,
            source_job_id=source_job_id,
            source_url_canonical=source_url_canonical,
            job_id_source=job_id_source,
        )

    def normalize_task(
        self,
        task_id: str,
        limit: int = 100,
    ) -> list[NormalizationResult]:
        """规范化任务下的所有岗位记录

        Args:
            task_id: 任务ID
            limit: 最大处理数量

        Returns:
            list[NormalizationResult]: 规范化结果列表
        """
        postings = self.raw_repo.list_for_normalization(task_id=task_id, limit=limit)
        results = []

        for posting in postings:
            result = self.normalize_posting(posting.id, task_id=task_id)
            results.append(result)

        return results

    def _extract_job_id_from_url(
        self,
        url: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """从URL提取job_id

        Args:
            url: 原始URL

        Returns:
            (job_id, error_message)
        """
        from app.normalizer.job_id_extractor import extract_job_id_safe

        return extract_job_id_safe(url)

    def _record_normalization_completed_event(
        self,
        posting_id: int,
        task_id: str,
        source_url_raw: str,
        source_url_canonical: Optional[str],
        source_job_id: str,
        job_id_source: str,
    ) -> None:
        """记录规范化完成事件"""
        now = datetime.now(UTC)
        event = TaskEvent(
            task_id=task_id,
            event_type="normalization.completed",
            operator="system",
            payload={
                "posting_id": posting_id,
                "source_url_raw": source_url_raw,
                "source_url_canonical": source_url_canonical,
                "source_job_id": source_job_id,
                "job_id_source": job_id_source,
                "task_id": task_id,
                "timestamp": now.isoformat(),
            },
            created_at=now,
        )
        self.task_repo.add_task_event(event)

    def _record_normalization_failed_event(
        self,
        posting_id: int,
        task_id: str,
        source_url_raw: str,
        error_message: str,
    ) -> None:
        """记录规范化失败事件"""
        now = datetime.now(UTC)
        event = TaskEvent(
            task_id=task_id,
            event_type="normalization.job_id.extract_failed",
            operator="system",
            payload={
                "posting_id": posting_id,
                "source_url_raw": source_url_raw,
                "error_message": error_message,
                "task_id": task_id,
                "timestamp": now.isoformat(),
            },
            created_at=now,
        )
        self.task_repo.add_task_event(event)

    def _apply_lifecycle_update_non_blocking(
        self,
        *,
        posting_id: int,
        task_id: str,
    ) -> None:
        """生命周期更新失败不影响规范化主流程。"""
        try:
            result = self.lifecycle_service.update_posting_lifecycle(
                posting_id=posting_id,
                task_id=task_id,
            )
            if not result.success and not result.skipped:
                logger.warning(
                    "生命周期更新失败但已隔离 posting_id=%s error=%s",
                    posting_id,
                    result.error_message,
                )
        except Exception:
            self.db.rollback()
            logger.exception("生命周期更新异常已隔离 posting_id=%s", posting_id)
