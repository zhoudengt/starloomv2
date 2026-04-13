"""CLI：cd backend && python -m ops.cli daily|preview"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path


def _ensure_backend_path() -> None:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)


def main() -> None:
    _ensure_backend_path()

    parser = argparse.ArgumentParser(description="StarLoom 运营内容流水线")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_daily = sub.add_parser("daily", help="生成当日物料包（抖音 + 轮播入库）")
    p_daily.add_argument("--date", type=str, default="", help="YYYY-MM-DD，默认今天")
    p_daily.add_argument("--no-media", action="store_true", help="不调用万相生成图片/视频（仅文案与 JSON）")
    p_daily.add_argument("--with-video", action="store_true", help="本次强制生成文生视频")

    p_prev = sub.add_parser("preview", help="仅打印摘要，不写文件")
    p_prev.add_argument("--date", type=str, default="", help="YYYY-MM-DD")

    args = parser.parse_args()

    d: date | None = None
    if getattr(args, "date", None) and args.date:
        d = date.fromisoformat(args.date)

    from ops.pipeline import run_daily

    preview = args.cmd == "preview"
    skip_media = getattr(args, "no_media", False)
    video_ov = True if getattr(args, "with_video", False) else None
    result = asyncio.run(
        run_daily(
            d,
            preview=preview,
            skip_wan_media=skip_media,
            video_override=video_ov,
        )
    )
    print(result)


if __name__ == "__main__":
    main()
