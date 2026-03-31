"""SSE formatting helpers for report streaming."""

import json
from typing import Any, AsyncGenerator, Dict


def sse_line(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_done(report_id: str) -> AsyncGenerator[str, None]:
    yield sse_line({"type": "done", "report_id": report_id})
