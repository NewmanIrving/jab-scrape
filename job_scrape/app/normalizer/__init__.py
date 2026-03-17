"""岗位数据规范化模块

提供URL规范化、job_id提取等功能，支持去重与数据一致性保证。
"""

from app.normalizer.lifecycle_service import LifecycleService
from app.normalizer.normalization_service import NormalizationService
from app.normalizer.url_normalizer import normalize_url_51job
from app.normalizer.job_id_extractor import extract_job_id_from_url_51job

__all__ = [
    "LifecycleService",
    "NormalizationService",
    "normalize_url_51job",
    "extract_job_id_from_url_51job",
]
