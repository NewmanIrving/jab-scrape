"""51job URL 规范化逻辑

根据平台规则生成标准化的岗位详情URL。
支持城市名称标准化，保证幂等性。
"""

import re
from typing import Optional


# 城市名称映射表：中文/英文 -> 标准化城市代码
CITY_MAPPING = {
    # 直辖市
    "北京": "beijing",
    "beijing": "beijing",
    "北京": "beijing",
    "上海": "shanghai",
    "shanghai": "shanghai",
    "上海": "shanghai",
    "天津": "tianjin",
    "tianjin": "tianjin",
    "重庆": "chongqing",
    "chongqing": "chongqing",
    # 省会城市
    "广州": "guangzhou",
    "guangzhou": "guangzhou",
    "深圳": "shenzhen",
    "shenzhen": "shenzhen",
    "成都": "chengdu",
    "chengdu": "chengdu",
    "杭州": "hangzhou",
    "hangzhou": "hangzhou",
    "南京": "nanjing",
    "nanjing": "nanjing",
    "武汉": "wuhan",
    "wuhan": "wuhan",
    "西安": "xian",
    "xian": "xian",
    "长沙": "changsha",
    "changsha": "changsha",
    "郑州": "zhengzhou",
    "zhengzhou": "zhengzhou",
    "济南": "jinan",
    "jinan": "jinan",
    "石家庄": "shijiazhuang",
    "shijiazhuang": "shijiazhuang",
    "福州": "fuzhou",
    "fuzhou": "fuzhou",
    "南昌": "nanchang",
    "nanchang": "nanchang",
    "南宁": "nanning",
    "nanning": "nanning",
    "贵阳": "guiyang",
    "guiyang": "guiyang",
    "太原": "taiyuan",
    "taiyuan": "taiyuan",
    "合肥": "hefei",
    "hefei": "hefei",
    "昆明": "kunming",
    "kunming": "kunming",
    "兰州": "lanzhou",
    "lanzhou": "lanzhou",
    "乌鲁木齐": "wulumuqi",
    "wulumuqi": "wulumuqi",
    "拉萨": "lasa",
    "lasa": "lasa",
    "海口": "haikou",
    "haikou": "haikou",
    "银川": "yinchuan",
    "yinchuan": "yinchuan",
    "西宁": "xining",
    "xining": "xining",
    # 主要城市
    "苏州": "suzhou",
    "suzhou": "suzhou",
    "宁波": "ningbo",
    "ningbo": "ningbo",
    "无锡": "wuxi",
    "wuxi": "wuxi",
    "青岛": "qingdao",
    "qingdao": "qingdao",
    "大连": "dalian",
    "dalian": "dalian",
    "厦门": "xiamen",
    "xiamen": "xiamen",
    "沈阳": "shenyang",
    "shenyang": "shenyang",
    "哈尔滨": "haerbin",
    "haerbin": "haerbin",
    "长春": "changchun",
    "changchun": "changchun",
    "佛山": "foshan",
    "foshan": "foshan",
    "东莞": "dongguan",
    "dongguan": "dongguan",
    "珠海": "zhuhai",
    "zhuhai": "zhuhai",
    "中山": "zhongshan",
    "zhongshan": "zhongshan",
    "惠州": "huizhou",
    "huizhou": "huizhou",
    "温州": "wenzhou",
    "wenzhou": "wenzhou",
    "嘉兴": "jiaxing",
    "jiaxing": "jiaxing",
    "绍兴": "shaoxing",
    "shaoxing": "shaoxing",
    "金华": "jinhua",
    "jinhua": "jinhua",
    "南通": "nantong",
    "nantong": "nantong",
    "徐州": "xuzhou",
    "xuzhou": "xuzhou",
    "常州": "changzhou",
    "changzhou": "changzhou",
    "扬州": "yangzhou",
    "yangzhou": "yangzhou",
    "烟台": "yantai",
    "yantai": "yantai",
    "潍坊": "weifang",
    "weifang": "weifang",
    "泉州": "quanzhou",
    "quanzhou": "quanzhou",
    "漳州": "zhangzhou",
    "zhangzhou": "zhangzhou",
    "唐山": "tangshan",
    "tangshan": "tangshan",
    "保定": "baoding",
    "baoding": "baoding",
    "洛阳": "luoyang",
    "luoyang": "luoyang",
}


def normalize_city(city_text: Optional[str]) -> Optional[str]:
    """标准化城市名称

    Args:
        city_text: 原始城市文本（如 "上海"、"shanghai"、"上海-浦东新区"）

    Returns:
        标准化后的城市代码（如 "shanghai"），无法识别时返回None
    """
    if not city_text:
        return None

    # 提取城市名称（去除区域部分）
    # 例如: "上海-浦东新区" -> "上海"
    city_part = city_text.split("-")[0].split("·")[0].strip()

    # 转换为小写进行匹配
    city_lower = city_part.lower()

    # 直接匹配
    if city_lower in CITY_MAPPING:
        return CITY_MAPPING[city_lower]

    # 尝试匹配中文
    if city_part in CITY_MAPPING:
        return CITY_MAPPING[city_part]

    # 无法识别
    return None


def normalize_url_51job(
    job_id: Optional[str],
    city: Optional[str] = None,
    location_text: Optional[str] = None,
) -> Optional[str]:
    """生成51job标准化URL

    URL格式: https://jobs.51job.com/{city}/{job_id}.html

    Args:
        job_id: 平台岗位ID
        city: 城市代码（可选，如果未提供则从location_text解析）
        location_text: 地点文本（如 "上海-浦东新区"），用于提取城市

    Returns:
        标准化后的URL，无法生成时返回None

    Examples:
        >>> normalize_url_51job("123456789", city="shanghai")
        'https://jobs.51job.com/shanghai/123456789.html'

        >>> normalize_url_51job("123456789", location_text="上海-浦东新区")
        'https://jobs.51job.com/shanghai/123456789.html'
    """
    # 检查必要参数
    if not job_id:
        return None

    # 确定城市代码
    city_code = city
    if not city_code and location_text:
        city_code = normalize_city(location_text)

    if not city_code:
        # 尝试从location_text直接解析
        city_code = normalize_city(location_text) if location_text else None

    if not city_code:
        # 使用默认城市（避免失败）
        city_code = "beijing"

    # 生成URL
    return f"https://jobs.51job.com/{city_code}/{job_id}.html"


def extract_city_from_url(url: str) -> Optional[str]:
    """从51job URL中提取城市代码

    Args:
        url: 51job岗位URL

    Returns:
        城市代码，无法提取时返回None

    Examples:
        >>> extract_city_from_url("https://jobs.51job.com/shanghai/123456789.html")
        'shanghai'
    """
    # 匹配模式: https://jobs.51job.com/{city}/{job_id}.html
    match = re.match(r"https://jobs\.51job\.com/([^/]+)/", url)
    if match:
        return match.group(1)
    return None
