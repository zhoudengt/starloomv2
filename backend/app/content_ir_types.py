"""Content IR — shared structure for markdown_to_ir output (version 1)."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

CONTENT_IR_VERSION: Literal["1"] = "1"


class ContentIrMeta(TypedDict, total=False):
    title: str
    subtitle: str
    reading_minutes: int
    tags: list[str]
    cover_image: str
    transit_basis: str


class BlockHeading(TypedDict):
    type: Literal["heading"]
    level: Literal[2, 3]
    text: str


class BlockParagraph(TypedDict):
    type: Literal["paragraph"]
    text: str


class BlockList(TypedDict):
    type: Literal["list"]
    ordered: bool
    items: list[str]


class BlockQuote(TypedDict):
    type: Literal["quote"]
    text: str
    source: NotRequired[str]


CalloutStyle = Literal["tip", "warning", "insight", "action"]


class BlockCallout(TypedDict):
    type: Literal["callout"]
    style: CalloutStyle
    title: NotRequired[str]
    text: str


class BlockKeywordTag(TypedDict):
    type: Literal["keyword_tag"]
    keywords: list[str]


class ActionChecklistItem(TypedDict, total=False):
    scene: str
    action: str
    effect: str


class BlockActionChecklist(TypedDict):
    type: Literal["action_checklist"]
    items: list[ActionChecklistItem]


class BlockDivider(TypedDict):
    type: Literal["divider"]


class BlockImage(TypedDict):
    type: Literal["image"]
    src: str
    alt: NotRequired[str]
    caption: NotRequired[str]


ContentBlock = (
    BlockHeading
    | BlockParagraph
    | BlockList
    | BlockQuote
    | BlockCallout
    | BlockKeywordTag
    | BlockActionChecklist
    | BlockDivider
    | BlockImage
)


class ContentIr(TypedDict):
    version: Literal["1"]
    meta: ContentIrMeta
    blocks: list[dict[str, Any]]  # ContentBlock union serialized as dicts
