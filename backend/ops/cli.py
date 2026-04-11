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

    p_daily = sub.add_parser("daily", help="生成当日 out/ 物料包")
    p_daily.add_argument("--date", type=str, default="", help="YYYY-MM-DD，默认今天")
    p_daily.add_argument("--no-media", action="store_true", help="不调用万相生成图片/视频（仅文案与 JSON）")
    p_daily.add_argument("--with-video", action="store_true", help="本次强制生成文生视频（覆盖 OPS_WAN_VIDEO_ENABLED=false）")

    p_prev = sub.add_parser("preview", help="仅打印摘要，不写文件")
    p_prev.add_argument("--date", type=str, default="", help="YYYY-MM-DD")
    p_prev.add_argument("--no-media", action="store_true", help="同 daily：预览模式不写文件，此参数无效果")

    p_h5 = sub.add_parser("h5", help="生成 H5 App 内容（tips + 文章）写入 MySQL")
    p_h5.add_argument("--date", type=str, default="", help="YYYY-MM-DD，默认今天")
    p_h5.add_argument("--skip-articles", action="store_true", help="仅生成 tips，跳过文章（不需要 LLM）")

    p_all = sub.add_parser("all", help="同时运行 daily（抖音物料）+ h5（App 内容）")
    p_all.add_argument("--date", type=str, default="", help="YYYY-MM-DD")
    p_all.add_argument("--no-media", action="store_true", help="不调用万相")

    args = parser.parse_args()

    d: date | None = None
    if getattr(args, "date", None) and args.date:
        d = date.fromisoformat(args.date)

    if args.cmd == "h5":
        from ops.pipeline import run_h5_content

        result = asyncio.run(
            run_h5_content(d, skip_articles=getattr(args, "skip_articles", False))
        )
        print(result)
    elif args.cmd == "all":
        from ops.pipeline import run_daily, run_h5_content

        skip_media = getattr(args, "no_media", False)

        async def _run_all():
            daily_r = await run_daily(d, skip_wan_media=skip_media)
            h5_r = await run_h5_content(d)
            return {"daily": daily_r, "h5": h5_r}

        result = asyncio.run(_run_all())
        print(result)
    else:
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
