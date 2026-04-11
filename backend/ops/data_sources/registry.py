from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ops.config import get_ops_settings
from ops.data_sources.base import CalendarContext, HotKeywordResult, NewsHeadline
from ops.data_sources.calendar_config import calendar_for_date
from ops.data_sources.rss import fetch_rss_titles
from ops.data_sources.weibo import fetch_weibo_hourly_trends
from ops.data_sources.zhihu import fetch_zhihu_hot
from ops.data_sources.xiaohongshu import fetch_xhs_hot_keywords, fetch_xhs_astro_titles


@dataclass
class ExternalBundle:
    calendar: dict
    weibo: HotKeywordResult
    rss_headlines: list[NewsHeadline]
    zhihu_headlines: list[NewsHeadline]
    xhs_keywords: HotKeywordResult
    xhs_headlines: list[NewsHeadline]
    fetched_at: str


def fetch_all_external(for_date) -> ExternalBundle:
    ops = get_ops_settings()
    cal = calendar_for_date(for_date)

    weibo = fetch_weibo_hourly_trends(ops.weibo_access_token)

    headlines: list[NewsHeadline] = []
    for u in ops.rss_urls_list:
        headlines.extend(fetch_rss_titles(u))

    zhihu = fetch_zhihu_hot()
    xhs_kw = fetch_xhs_hot_keywords()
    xhs_titles = fetch_xhs_astro_titles()

    return ExternalBundle(
        calendar=cal,
        weibo=weibo,
        rss_headlines=headlines,
        zhihu_headlines=zhihu,
        xhs_keywords=xhs_kw,
        xhs_headlines=xhs_titles,
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )


def to_calendar_context(cal: dict) -> CalendarContext:
    return CalendarContext(
        holiday_label=cal.get("holiday_label"),
        holiday_weight=float(cal.get("holiday_weight", 1.0)),
        suggested_cta=cal.get("suggested_cta"),
        banned_words=list(cal.get("banned_words") or []),
    )
