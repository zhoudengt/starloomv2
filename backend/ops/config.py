"""运营流水线专用配置（OPS_ 前缀），与主应用 Settings 分离。"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="OPS_",
    )

    # 可选：百炼应用 ID（运营文案/素材提示词）；不配则仅用模板
    llm_enabled: bool = Field(default=False, description="是否调用 LLM 丰富文案")
    bailian_app_id: str = Field(default="", description="百炼智能体应用 ID（运营专用）")

    # 微博开放平台（可选）
    weibo_access_token: str = Field(default="", description="微博 API access_token")

    # RSS 列表，逗号分隔 URL
    rss_feed_urls: str = Field(
        default="",
        description="权威 RSS URL，逗号分隔",
    )

    # 默认 H5 用于 UTM 拼接
    frontend_base_url: str = Field(
        default="",
        description="与 FRONTEND_URL 一致，未设时由主 Settings 读取",
    )

    top_k_angles: int = Field(default=3, ge=1, le=12)

    h5_max_articles_per_day: int = Field(
        default=5,
        ge=1,
        le=12,
        description="H5 日更文章生成条数（与首页轮播圆点数量对齐）",
    )

    # DashScope 万相（与 BAILIAN_API_KEY 同钥；可选单独覆盖）
    dashscope_api_key: str = Field(default="", description="可选，覆盖 BAILIAN_API_KEY")
    dashscope_workspace: str = Field(default="", description="可选 X-DashScope-WorkSpace")

    # 默认生成图文（文生图）；视频贵，默认关
    wan_image_enabled: bool = Field(default=True, description="是否调用万相文生图")
    wan_video_enabled: bool = Field(default=False, description="是否调用万相文生视频（贵，后期再开）")
    wan_image_model: str = Field(default="wan2.6-t2i", description="万相文生图模型")
    wan_video_model: str = Field(default="wan2.6-t2v", description="万相文生视频模型")
    wan_image_size: str = Field(default="720*1280", description="文生图尺寸（竖版）")
    wan_video_size: str = Field(default="720*1280", description="文生视频 size（依模型文档）")
    wan_video_duration_sec: int = Field(default=5, ge=2, le=15, description="视频时长秒")
    # wan2.6-t2i 走 multimodal-generation HTTP；多张图之间 sleep 减轻 429
    dashscope_http_base: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1",
        description="北京地域 API 根路径，勿与新加坡/弗吉尼亚混用",
    )
    wan_image_sleep_sec: float = Field(default=4.0, ge=0.0, description="多张图之间的间隔秒")
    wan_image_retries: int = Field(default=3, ge=1, le=8, description="单张图遇 429 等可重试次数")

    # 抖音一体化发布包：首帧项目内 webp + 万相，或全部万相
    wan_carousel_mode: str = Field(
        default="asset_first",
        description="asset_first：首帧 /zodiac/{slug}.webp + 万相；ai_only：三帧均万相",
    )
    traffic_qr_enabled: bool = Field(
        default=True,
        description="是否生成 media/traffic_qr.png（与置顶链接同源 UTM）",
    )

    @property
    def rss_urls_list(self) -> List[str]:
        return [u.strip() for u in self.rss_feed_urls.split(",") if u.strip()]


@lru_cache
def get_ops_settings() -> OpsSettings:
    return OpsSettings()


def load_calendar_yaml_path() -> str:
    from ops.paths import default_calendar_yaml

    return os.environ.get("OPS_CALENDAR_YAML", default_calendar_yaml())
