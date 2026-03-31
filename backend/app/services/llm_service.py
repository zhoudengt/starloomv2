"""LLM: Coze + Bailian with fallback."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BaseLLMService(ABC):
    @abstractmethod
    async def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Non-streaming completion."""

    @abstractmethod
    async def stream_generate(
        self, prompt: str, params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text deltas (plain text)."""


def _extract_json_object(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return None
    return None


class CozeService(BaseLLMService):
    def __init__(self, settings: Settings, bot_id: str) -> None:
        self._settings = settings
        self._bot_id = bot_id
        self._url = f"{settings.coze_api_base.rstrip('/')}/open_api/v2/chat/completions"

    async def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> str:
        body = {
            "model": self._bot_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.coze_access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(self._url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        return self._content_from_openai_response(data)

    async def stream_generate(
        self, prompt: str, params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        body = {
            "model": self._bot_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.coze_access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", self._url, json=body, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue

    @staticmethod
    def _content_from_openai_response(data: dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return msg.get("content") or ""


class BailianService(BaseLLMService):
    def __init__(self, settings: Settings, model: str) -> None:
        self._settings = settings
        self._model = model or settings.bailian_app_id
        self._url = f"{settings.bailian_api_base.rstrip('/')}/chat/completions"

    async def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> str:
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.bailian_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(self._url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        return CozeService._content_from_openai_response(data)

    async def stream_generate(
        self, prompt: str, params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.bailian_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", self._url, json=body, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue


class LLMServiceFactory:
    @staticmethod
    def for_daily(settings: Settings) -> BaseLLMService:
        return CozeService(settings, settings.coze_bot_id_daily)

    @staticmethod
    def for_report(settings: Settings) -> BaseLLMService:
        return CozeService(settings, settings.coze_bot_id_report)

    @staticmethod
    def for_compatibility(settings: Settings) -> BaseLLMService:
        return CozeService(settings, settings.coze_bot_id_compatibility)

    @staticmethod
    def for_annual(settings: Settings) -> BaseLLMService:
        return CozeService(settings, settings.coze_bot_id_annual)

    @staticmethod
    def for_chat(settings: Settings) -> BaseLLMService:
        return CozeService(settings, settings.coze_bot_id_chat or settings.coze_bot_id_report)

    @staticmethod
    def bailian_fallback(settings: Settings) -> BaseLLMService:
        return BailianService(settings, settings.bailian_app_id)


async def generate_with_fallback(
    primary: BaseLLMService,
    fallback: BaseLLMService,
    prompt: str,
) -> str:
    try:
        return await primary.generate(prompt)
    except Exception as e:
        logger.warning("Primary LLM failed: %s", e)
        try:
            return await fallback.generate(prompt)
        except Exception as e2:
            logger.error("Fallback LLM failed: %s", e2)
            raise


async def stream_with_fallback(
    primary: BaseLLMService,
    fallback: BaseLLMService,
    prompt: str,
) -> AsyncGenerator[str, None]:
    try:
        async for chunk in primary.stream_generate(prompt):
            yield chunk
        return
    except Exception as e:
        logger.warning("Primary LLM stream failed: %s", e)
    try:
        async for chunk in fallback.stream_generate(prompt):
            yield chunk
        return
    except Exception as e2:
        logger.error("Fallback LLM stream failed: %s", e2)
        yield fallback_static_text()


def fallback_static_text() -> str:
    return (
        "抱歉，当前分析服务暂时不可用。请稍后重试。\n\n"
        "本内容基于星座文化提供性格分析参考，仅供娱乐，不构成任何决策建议。"
    )


def fallback_daily_json(sign_cn: str, fortune_date: str) -> dict:
    """Template when LLM unavailable."""
    return {
        "overall_score": 72,
        "love_score": 70,
        "career_score": 75,
        "wealth_score": 68,
        "health_score": 74,
        "lucky_color": "金色",
        "lucky_number": 3,
        "summary": f"{sign_cn}今日运势参考：保持节奏，适度社交，关注情绪与休息。",
        "love": "感情互动宜温和沟通，避免过度解读。",
        "career": "工作推进以稳定为主，适合整理与复盘。",
        "wealth": "理财以稳健为主，避免冲动消费。",
        "health": "注意作息与补水，适度运动。",
        "advice": "把目标拆小，一步一步完成。",
        "_meta": {"fallback": True, "date": fortune_date},
    }


async def generate_json_daily(
    settings: Settings,
    prompt: str,
    sign_cn: str = "星座",
    fortune_date: str = "",
) -> dict:
    primary = LLMServiceFactory.for_daily(settings)
    fallback_llm = LLMServiceFactory.bailian_fallback(settings)
    text = ""
    try:
        text = await generate_with_fallback(primary, fallback_llm, prompt)
    except Exception:
        logger.exception("Daily JSON generation failed")
        return fallback_daily_json(sign_cn, fortune_date)
    data = _extract_json_object(text) if text else None
    if not data:
        return fallback_daily_json(sign_cn, fortune_date)
    return data
