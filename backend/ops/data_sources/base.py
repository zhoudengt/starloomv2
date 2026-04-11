from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List


@dataclass
class HotKeywordResult:
    source: str
    keywords: List[str]
    fetched_at: str = ""
    raw_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class NewsHeadline:
    source: str
    title: str
    link: str = ""
    published: str = ""


@dataclass
class CalendarContext:
    holiday_label: str | None
    holiday_weight: float
    suggested_cta: str | None
    banned_words: List[str]
