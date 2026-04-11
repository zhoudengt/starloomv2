"""Markdown → Content IR (v1). Deterministic parsing + pattern upgrades."""

from __future__ import annotations

import math
import re
from typing import Any, Optional

from app.content_ir_types import CONTENT_IR_VERSION, ContentIrMeta

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def markdown_to_ir(raw_md: str, meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Convert markdown string to Content IR v1 dict (JSON-serializable).

    `meta` may include: title, subtitle, tags, cover_image, transit_basis
    (merged into output meta; reading_minutes computed from body).
    """
    text = (raw_md or "").replace("\r\n", "\n").strip()
    out_meta: ContentIrMeta = {}
    if meta:
        for k in ("title", "subtitle", "tags", "cover_image", "transit_basis"):
            if k in meta and meta[k] is not None:
                out_meta[k] = meta[k]  # type: ignore[literal-required]

    if not text:
        out_meta["reading_minutes"] = 0
        return {"version": CONTENT_IR_VERSION, "meta": dict(out_meta), "blocks": []}

    lines = text.split("\n")
    blocks = _parse_blocks(lines)
    blocks = _upgrade_blocks(blocks)

    minutes = _estimate_reading_minutes(blocks)
    out_meta["reading_minutes"] = minutes

    # First H2/H3 as subtitle hint if missing
    if "subtitle" not in out_meta:
        for b in blocks:
            if b.get("type") == "heading":
                out_meta["subtitle"] = b.get("text", "")[:120]
                break

    return {
        "version": CONTENT_IR_VERSION,
        "meta": dict(out_meta),
        "blocks": blocks,
    }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_IMG_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")
_LIST_UL = re.compile(r"^(\s*)[-*]\s+(.*)$")
_LIST_OL = re.compile(r"^(\s*)\d+\.\s+(.*)$")


def _parse_blocks(lines: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("### "):
            blocks.append({"type": "heading", "level": 3, "text": stripped[4:].strip()})
            i += 1
            continue
        if stripped.startswith("## ") and not stripped.startswith("### "):
            blocks.append({"type": "heading", "level": 2, "text": stripped[3:].strip()})
            i += 1
            continue

        if stripped == "---":
            blocks.append({"type": "divider"})
            i += 1
            continue

        if stripped.startswith("> "):
            qlines = []
            while i < n:
                s = lines[i].strip()
                if not s and qlines:
                    break
                if s.startswith("> "):
                    qlines.append(s[2:].strip())
                    i += 1
                elif s and qlines:
                    qlines.append(s)
                    i += 1
                else:
                    break
            if qlines:
                blocks.append({"type": "quote", "text": "\n".join(qlines)})
            continue

        mimg = _IMG_RE.match(stripped)
        if mimg:
            blocks.append(
                {
                    "type": "image",
                    "src": mimg.group(2).strip(),
                    "alt": (mimg.group(1) or "").strip() or None,
                }
            )
            i += 1
            continue

        ul = _LIST_UL.match(raw)
        ol = _LIST_OL.match(raw)
        if ul or ol:
            ordered = bool(ol)
            items: list[str] = []
            while i < n:
                line = lines[i]
                mu = _LIST_UL.match(line)
                mo = _LIST_OL.match(line)
                if ordered and mo:
                    items.append(mo.group(2).strip())
                    i += 1
                elif not ordered and mu:
                    items.append(mu.group(2).strip())
                    i += 1
                elif ordered and mu:
                    break
                elif not ordered and mo:
                    break
                elif not line.strip():
                    break
                else:
                    break
            if items:
                blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue

        # paragraph: merge consecutive non-special lines
        buf: list[str] = []
        while i < n:
            s = lines[i]
            st = s.strip()
            if not st:
                break
            if (
                st.startswith("### ")
                or (st.startswith("## ") and not st.startswith("### "))
                or st == "---"
                or st.startswith("> ")
                or _LIST_UL.match(s)
                or _LIST_OL.match(s)
                or _IMG_RE.match(st)
            ):
                if buf:
                    break
                break
            buf.append(s.rstrip())
            i += 1
        para = "\n".join(buf).strip()
        if para:
            blocks.append({"type": "paragraph", "text": para})
        elif not buf and i < n and not lines[i].strip():
            i += 1

    return blocks


# ---------------------------------------------------------------------------
# Upgrades (pattern → rich blocks)
# ---------------------------------------------------------------------------

_KEYWORD_RE = re.compile(
    r"(?:本周|今日)?(?:职场)?关键词[：:]\s*(.+)$",
    re.I,
)


def _upgrade_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        bt = b.get("type")
        if bt == "list":
            upgraded = _try_action_checklist(b)
            if upgraded is not None:
                out.append(upgraded)
                continue
        if bt == "paragraph":
            pb = _try_upgrade_paragraph(b)
            if isinstance(pb, list):
                out.extend(pb)
            else:
                out.append(pb)
            continue
        out.append(b)
    return out


def _try_action_checklist(b: dict[str, Any]) -> Optional[dict[str, Any]]:
    items = b.get("items") or []
    if len(items) < 1:
        return None
    if not any("场景" in it and "做法" in it for it in items):
        return None
    parsed: list[dict[str, str]] = []
    for it in items:
        scene, action, effect = _parse_action_item(it)
        parsed.append(
            {
                "scene": scene or "",
                "action": action or it,
                "effect": effect or "",
            }
        )
    return {"type": "action_checklist", "items": parsed}


def _parse_action_item(text: str) -> tuple[str, str, str]:
    """Extract 场景/做法/效果 from a single list line."""
    t = text.strip()
    scene = ""
    action = ""
    effect = ""
    for label in ("场景", "做法", "效果"):
        m = re.search(rf"\*\*{label}\*\*[：:\s]*(.+?)(?=(?:\*\*(?:场景|做法|效果)\*\*)|$)", t, re.S)
        if m:
            val = m.group(1).strip()
            if label == "场景":
                scene = val
            elif label == "做法":
                action = val
            else:
                effect = val
    if not action and not scene:
        action = t
    return scene, action, effect


def _try_upgrade_paragraph(b: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any]:
    text = (b.get("text") or "").strip()
    if not text:
        return b

    # Callout: leading emoji or markers
    if text.startswith("💡"):
        return {"type": "callout", "style": "tip", "text": text.lstrip("💡").strip()}
    if text.startswith("⚠️"):
        return {"type": "callout", "style": "warning", "text": text.lstrip("⚠️").strip()}
    if text.startswith(("建议：", "提示：", "注意：")):
        return {"type": "callout", "style": "insight", "title": text[:2], "text": text[3:].strip()}

    mk = _KEYWORD_RE.search(text.replace("\n", " "))
    if mk:
        rest = mk.group(1).strip()
        parts = re.split(r"[，、,|｜]", rest)
        kws = [p.strip() for p in parts if p.strip()][:12]
        if kws:
            return {"type": "keyword_tag", "keywords": kws}

    return b


def _estimate_reading_minutes(blocks: list[dict[str, Any]]) -> int:
    total = 0
    for b in blocks:
        t = b.get("type")
        if t in ("paragraph", "quote", "callout"):
            total += len((b.get("text") or ""))
        elif t == "heading":
            total += len((b.get("text") or ""))
        elif t == "list":
            for it in b.get("items") or []:
                total += len(str(it))
        elif t == "action_checklist":
            for it in b.get("items") or []:
                if isinstance(it, dict):
                    total += len(it.get("scene", "")) + len(it.get("action", "")) + len(it.get("effect", ""))
    if total <= 0:
        return 1
    return max(1, math.ceil(total / 400))
