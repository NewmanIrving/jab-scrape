"""从URL中提取51job岗位ID

提供兜底逻辑：当API数据未提供job_id时，从URL路径中解析提取。
"""

import re
from typing import Optional


# 51job URL模式
# 1. https://jobs.51job.com/shanghai/123456789.html
# 2. https://jobs.51job.com/123456789.html (较少见)
URL_PATTERN_51JOB = re.compile(
    r"https?://jobs\.51job\.com/(?:[^/]+/)?(\d+)\.html"
)


def extract_job_id_from_url_51job(url: str) -> Optional[str]:
    """从51job URL中提取岗位ID

    支持以下URL格式：
    - https://jobs.51job.com/shanghai/123456789.html
    - https://jobs.51job.com/123456789.html
    - http://jobs.51job.com/beijing/987654321.html

    Args:
        url: 51job岗位详情页URL

    Returns:
        提取的job_id，无法提取时返回None

    Examples:
        >>> extract_job_id_from_url_51job("https://jobs.51job.com/shanghai/123456789.html")
        '123456789'

        >>> extract_job_id_from_url_51job("https://jobs.51job.com/beijing/987654321.html")
        '987654321'
    """
    if not url:
        return None

    match = URL_PATTERN_51JOB.search(url)
    if match:
        return match.group(1)

    return None


def extract_job_id_safe(url: str) -> tuple[Optional[str], Optional[str]]:
    """安全提取job_id，返回(结果, 错误信息)

    Args:
        url: 51job岗位详情页URL

    Returns:
        (job_id, error_message) 元组
        - 成功时: (job_id, None)
        - 失败时: (None, error_message)
    """
    if not url:
        return None, "URL为空"

    job_id = extract_job_id_from_url_51job(url)
    if job_id:
        return job_id, None

    return None, f"无法从URL中解析job_id: {url}"


def is_valid_51job_url(url: str) -> bool:
    """检查URL是否为有效的51job岗位URL

    Args:
        url: 待检查的URL

    Returns:
        True表示是有效的51job岗位URL
    """
    if not url:
        return False
    return URL_PATTERN_51JOB.search(url) is not None
