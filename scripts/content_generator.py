#!/usr/bin/env python3
"""
Optional helper: generate short copy for Douyin / social from daily API.
Usage: curl http://localhost:8000/api/v1/daily/aries | python scripts/content_generator.py
"""

import json
import sys


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("Paste JSON from /api/v1/daily/{sign}", file=sys.stderr)
        sys.exit(1)
    cn = data.get("sign_cn", "")
    score = data.get("overall_score", "")
    summary = data.get("summary", "")
    print(f"【{cn}今日运势参考】综合 {score} 分。{summary}")


if __name__ == "__main__":
    main()
