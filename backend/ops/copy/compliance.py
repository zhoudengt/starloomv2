from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ComplianceResult:
    ok: bool
    violations: List[str]


def check_compliance(text: str, extra_banned: List[str]) -> ComplianceResult:
    violations: list[str] = []
    combined = list(extra_banned) + ["算命", "占卜"]
    for w in combined:
        if w and w in text:
            violations.append(f"包含禁用词: {w}")
    return ComplianceResult(ok=len(violations) == 0, violations=violations)


def strip_banned(text: str, extra_banned: List[str]) -> str:
    out = text
    for w in extra_banned + ["算命", "占卜"]:
        if w:
            out = out.replace(w, "参考")
    return out
