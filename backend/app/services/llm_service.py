"""LLM: Coze + 百炼智能体 Application API (dashscope SDK)."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

# 百炼流式：总时长与单次等待（避免无限挂起）
BAILIAN_STREAM_OVERALL_SEC = 180.0
BAILIAN_STREAM_IDLE_SEC = 60.0


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


def get_bailian_app_id(settings: Settings, scene: str) -> str:
    key = {
        "daily": settings.bailian_app_id_daily,
        "personality": settings.bailian_app_id_personality,
        "compatibility": settings.bailian_app_id_compatibility,
        "annual": settings.bailian_app_id_annual,
        "chat": settings.bailian_app_id_chat,
        "planner": settings.bailian_app_id_planner,
        "profile_extractor": settings.bailian_app_id_profile_extractor,
    }.get(scene, "")
    return (key or "").strip() or (settings.bailian_app_id or "").strip()


class BailianApplicationService(BaseLLMService):
    """
    百炼「智能体应用」：dashscope.Application.call（与 HiFate-bazi 一致）。
    系统提示词在百炼控制台配置；此处仅传用户侧 prompt。
    """

    def __init__(self, settings: Settings, app_id: str) -> None:
        self._settings = settings
        self._app_id = app_id

    def _setup_dashscope(self) -> None:
        import dashscope

        logging.getLogger("dashscope").setLevel(logging.WARNING)
        if not self._settings.bailian_api_key:
            raise ValueError("BAILIAN_API_KEY 未配置")
        dashscope.api_key = self._settings.bailian_api_key

    async def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> str:
        parts: list[str] = []
        async for chunk in self.stream_generate(prompt, params):
            parts.append(chunk)
        return "".join(parts)

    async def stream_generate(
        self, prompt: str, params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        if not self._app_id:
            raise ValueError("百炼应用 app_id 为空")

        self._setup_dashscope()
        from dashscope import Application

        params = params or {}
        custom_headers: Dict[str, str] = dict(params.get("headers") or params.get("extra_headers") or {})

        queue: asyncio.Queue = asyncio.Queue()
        DONE_SENTINEL = object()
        loop = asyncio.get_running_loop()

        call_params: Dict[str, Any] = {
            "app_id": self._app_id,
            "prompt": prompt,
            "stream": True,
            "incremental_output": True,
        }
        if custom_headers:
            call_params["headers"] = custom_headers

        def sync_iterate() -> None:
            buffer = ""
            has_content = False
            try:
                responses = Application.call(**call_params)
                for response in responses:
                    if response.status_code != 200:
                        err = f"百炼 API 错误: {response.code} - {response.message}"
                        logger.error("%s", err)
                        asyncio.run_coroutine_threadsafe(
                            queue.put({"_kind": "error", "text": err}), loop
                        ).result(timeout=30)
                        return
                    output = response.output
                    if output:
                        text = output.get("text", "") or ""
                        if text:
                            new_content = text[len(buffer) :] if text.startswith(buffer) else text
                            if new_content:
                                has_content = True
                                buffer = text
                                asyncio.run_coroutine_threadsafe(
                                    queue.put({"_kind": "delta", "text": new_content}), loop
                                ).result(timeout=30)
                if not has_content:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"_kind": "error", "text": "百炼 API 返回空内容"}), loop
                    ).result(timeout=30)
            except Exception as e:
                err = f"百炼 API 调用异常: {e}"
                logger.exception(err)
                try:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"_kind": "error", "text": err}), loop
                    ).result(timeout=30)
                except Exception:
                    pass
            finally:
                try:
                    asyncio.run_coroutine_threadsafe(queue.put(DONE_SENTINEL), loop).result(timeout=30)
                except Exception:
                    pass

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(sync_iterate)
        stream_started = time.monotonic()
        try:
            while True:
                if time.monotonic() - stream_started > BAILIAN_STREAM_OVERALL_SEC:
                    raise RuntimeError(
                        f"百炼流式输出总时长超过 {int(BAILIAN_STREAM_OVERALL_SEC)} 秒，请稍后重试"
                    )
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=BAILIAN_STREAM_IDLE_SEC)
                except asyncio.TimeoutError:
                    raise RuntimeError(
                        f"百炼流式输出超过 {int(BAILIAN_STREAM_IDLE_SEC)} 秒无新数据，请检查网络或稍后重试"
                    ) from None
                if item is DONE_SENTINEL:
                    break
                kind = item.get("_kind")
                if kind == "delta":
                    yield item["text"]
                elif kind == "error":
                    raise RuntimeError(item.get("text", "百炼错误"))
        finally:
            executor.shutdown(wait=False)


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


class LLMServiceFactory:
    @staticmethod
    def for_daily(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "daily")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_daily)

    @staticmethod
    def for_report(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "personality")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_report)

    @staticmethod
    def for_compatibility(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "compatibility")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_compatibility)

    @staticmethod
    def for_annual(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "annual")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_annual)

    @staticmethod
    def for_chat(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "chat")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_chat or settings.coze_bot_id_report)

    @staticmethod
    def bailian_for_scene(settings: Settings, scene: str) -> BaseLLMService:
        app_id = get_bailian_app_id(settings, scene)
        return BailianApplicationService(settings, app_id)

    @staticmethod
    def for_planner(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "planner")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_report)

    @staticmethod
    def for_profile_extractor(settings: Settings) -> BaseLLMService:
        if settings.llm_platform.lower() == "bailian":
            app_id = get_bailian_app_id(settings, "profile_extractor")
            return BailianApplicationService(settings, app_id)
        return CozeService(settings, settings.coze_bot_id_report)


async def generate_with_fallback(
    primary: BaseLLMService,
    fallback: Optional[BaseLLMService],
    prompt: str,
) -> str:
    try:
        return await primary.generate(prompt)
    except Exception as e:
        logger.warning("Primary LLM failed: %s", e)
    if fallback is not None:
        try:
            return await fallback.generate(prompt)
        except Exception as e2:
            logger.error("Fallback LLM failed: %s", e2)
            raise
    raise RuntimeError("LLM generate failed")


async def stream_with_fallback(
    primary: BaseLLMService,
    fallback: Optional[BaseLLMService],
    prompt: str,
    stream_params: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    stream_params = stream_params or {}
    try:
        async for chunk in primary.stream_generate(prompt, stream_params):
            yield chunk
        return
    except Exception as e:
        logger.warning("Primary LLM stream failed: %s", e)
    if fallback is not None:
        try:
            async for chunk in fallback.stream_generate(prompt, stream_params):
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
    fallback_llm: Optional[BaseLLMService] = None
    if settings.llm_platform.lower() != "bailian":
        fallback_llm = LLMServiceFactory.bailian_for_scene(settings, "daily")
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
