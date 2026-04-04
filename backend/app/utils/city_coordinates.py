"""Preset coordinates + IANA timezone for major CN cities (offline, no GeoNames)."""

from __future__ import annotations

from typing import Optional, Tuple

# name -> (lat, lon, tz)
# 含各省会/自治区首府及常用城市；「甘肃」与兰州同坐标便于选省名。
_CN_CITIES: dict[str, Tuple[float, float, str]] = {
    "北京": (39.9042, 116.4074, "Asia/Shanghai"),
    "上海": (31.2304, 121.4737, "Asia/Shanghai"),
    "天津": (39.3434, 117.3616, "Asia/Shanghai"),
    "重庆": (29.5630, 106.5516, "Asia/Shanghai"),
    "广州": (23.1291, 113.2644, "Asia/Shanghai"),
    "深圳": (22.5431, 114.0579, "Asia/Shanghai"),
    "杭州": (30.2741, 120.1551, "Asia/Shanghai"),
    "南京": (32.0603, 118.7969, "Asia/Shanghai"),
    "成都": (30.5728, 104.0668, "Asia/Shanghai"),
    "武汉": (30.5928, 114.3055, "Asia/Shanghai"),
    "西安": (34.3416, 108.9398, "Asia/Shanghai"),
    "苏州": (31.2989, 120.5853, "Asia/Shanghai"),
    "郑州": (34.7466, 113.6254, "Asia/Shanghai"),
    "长沙": (28.2280, 112.9388, "Asia/Shanghai"),
    "沈阳": (41.8057, 123.4328, "Asia/Shanghai"),
    "青岛": (36.0671, 120.3826, "Asia/Shanghai"),
    "厦门": (24.4798, 118.0894, "Asia/Shanghai"),
    "哈尔滨": (45.8038, 126.5350, "Asia/Shanghai"),
    "昆明": (25.0406, 102.7123, "Asia/Shanghai"),
    "大连": (38.9140, 121.6147, "Asia/Shanghai"),
    "济南": (36.6512, 117.1201, "Asia/Shanghai"),
    "合肥": (31.8206, 117.2272, "Asia/Shanghai"),
    "福州": (26.0745, 119.2965, "Asia/Shanghai"),
    "石家庄": (38.0428, 114.5149, "Asia/Shanghai"),
    "太原": (37.8706, 112.5489, "Asia/Shanghai"),
    "长春": (43.8171, 125.3235, "Asia/Shanghai"),
    "南昌": (28.6820, 115.8579, "Asia/Shanghai"),
    "海口": (20.0440, 110.1999, "Asia/Shanghai"),
    "贵阳": (26.6470, 106.6302, "Asia/Shanghai"),
    "兰州": (36.0611, 103.8343, "Asia/Shanghai"),
    "甘肃": (36.0611, 103.8343, "Asia/Shanghai"),
    "西宁": (36.6171, 101.7782, "Asia/Shanghai"),
    "银川": (38.4872, 106.2309, "Asia/Shanghai"),
    "乌鲁木齐": (43.8256, 87.6168, "Asia/Shanghai"),
    "拉萨": (29.6500, 91.1000, "Asia/Shanghai"),
    "呼和浩特": (40.8424, 111.7492, "Asia/Shanghai"),
    "南宁": (22.8170, 108.3665, "Asia/Shanghai"),
    "香港": (22.3193, 114.1694, "Asia/Hong_Kong"),
    "台北": (25.0330, 121.5654, "Asia/Taipei"),
    "澳门": (22.1987, 113.5439, "Asia/Macau"),
    # 省 / 自治区 / 直辖市全称别名 → 省会或首府坐标（与上方城市一致）
    "河北": (38.0428, 114.5149, "Asia/Shanghai"),
    "山西": (37.8706, 112.5489, "Asia/Shanghai"),
    "辽宁": (41.8057, 123.4328, "Asia/Shanghai"),
    "吉林": (43.8171, 125.3235, "Asia/Shanghai"),
    "黑龙江": (45.8038, 126.5350, "Asia/Shanghai"),
    "江苏": (32.0603, 118.7969, "Asia/Shanghai"),
    "浙江": (30.2741, 120.1551, "Asia/Shanghai"),
    "安徽": (31.8206, 117.2272, "Asia/Shanghai"),
    "福建": (26.0745, 119.2965, "Asia/Shanghai"),
    "江西": (28.6820, 115.8579, "Asia/Shanghai"),
    "山东": (36.6512, 117.1201, "Asia/Shanghai"),
    "河南": (34.7466, 113.6254, "Asia/Shanghai"),
    "湖北": (30.5928, 114.3055, "Asia/Shanghai"),
    "湖南": (28.2280, 112.9388, "Asia/Shanghai"),
    "广东": (23.1291, 113.2644, "Asia/Shanghai"),
    "海南": (20.0440, 110.1999, "Asia/Shanghai"),
    "四川": (30.5728, 104.0668, "Asia/Shanghai"),
    "贵州": (26.6470, 106.6302, "Asia/Shanghai"),
    "云南": (25.0406, 102.7123, "Asia/Shanghai"),
    "陕西": (34.3416, 108.9398, "Asia/Shanghai"),
    "青海": (36.6171, 101.7782, "Asia/Shanghai"),
    "台湾": (25.0330, 121.5654, "Asia/Taipei"),
    "内蒙古": (40.8424, 111.7492, "Asia/Shanghai"),
    "广西": (22.8170, 108.3665, "Asia/Shanghai"),
    "西藏": (29.6500, 91.1000, "Asia/Shanghai"),
    "宁夏": (38.4872, 106.2309, "Asia/Shanghai"),
    "新疆": (43.8256, 87.6168, "Asia/Shanghai"),
    "北京市": (39.9042, 116.4074, "Asia/Shanghai"),
    "天津市": (39.3434, 117.3616, "Asia/Shanghai"),
    "上海市": (31.2304, 121.4737, "Asia/Shanghai"),
    "重庆市": (29.5630, 106.5516, "Asia/Shanghai"),
}

DEFAULT_LAT = 39.9042
DEFAULT_LON = 116.4074
DEFAULT_TZ = "Asia/Shanghai"
DEFAULT_LABEL = "北京（默认）"


def resolve_city(
    place_name: Optional[str],
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    tz_str: Optional[str] = None,
) -> tuple[float, float, str, str]:
    """
    Returns (lat, lon, tz_str, label).
    If lat/lon provided, use them; else map place_name; else Beijing default.
    """
    if lat is not None and lon is not None:
        tz = tz_str or DEFAULT_TZ
        label = place_name or f"{lat:.4f}°N {lon:.4f}°E"
        return float(lat), float(lon), tz, label
    if place_name:
        key = place_name.strip()
        if key in _CN_CITIES:
            la, lo, tz = _CN_CITIES[key]
            return la, lo, tz_str or tz, key
    return DEFAULT_LAT, DEFAULT_LON, tz_str or DEFAULT_TZ, DEFAULT_LABEL


def list_city_names() -> list[str]:
    return sorted(_CN_CITIES.keys())
