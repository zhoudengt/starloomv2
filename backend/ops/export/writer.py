from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from ops.copy.compliance import check_compliance
from ops.copy.generate import CopyBundle
from ops.paths import day_dir
from ops.ranking.rank import RankedAngle
from ops.visual.bundle import MultimodalBundle


def write_day_bundle(
    d: date,
    manifest: Dict[str, Any],
    copy: CopyBundle,
    multi: MultimodalBundle,
    preview: bool,
) -> Path:
    root = day_dir(d)
    if not preview:
        root.mkdir(parents=True, exist_ok=True)

    def _write(name: str, payload: Any) -> None:
        if preview:
            return
        path = root / name
        if isinstance(payload, (dict, list)):
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            path.write_text(str(payload), encoding="utf-8")

    cr = check_compliance(copy.copy_md, manifest.get("banned_words") or [])
    manifest["compliance"] = {"ok": cr.ok, "violations": cr.violations}

    _write("manifest.json", manifest)
    _write(
        "copy.md",
        "\n".join(
            [
                f"# {copy.titles[0] if copy.titles else 'StarLoom 运营稿'}\n",
                copy.copy_md,
                "\n## 标题备选\n",
                "\n".join(f"- {t}" for t in copy.titles),
                "\n## 评论引导\n",
                copy.comment_cta,
                "\n## 转发语备选\n",
                "\n".join(f"- {s}" for s in copy.share_lines),
            ]
        ),
    )
    _write("carousel.json", multi.carousel)
    _write("video_spec.json", multi.video_spec)
    _write("media_prompts.json", multi.media_prompts)
    _write("voice.txt", multi.voice_txt)

    return root
