from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = Field(default="dev-secret-change-me")
    frontend_url: str = "http://localhost:5173"
    jwt_expire_days: int = 7

    db_host: str = "localhost"
    db_port: int = 3307
    db_name: str = "starloom"
    db_user: str = "root"
    db_password: str = "123456"

    redis_host: str = "localhost"
    redis_port: int = 6380
    redis_db: int = 0

    # Public daily fortune: prefetch all 12 signs at Beijing local time (cron in app lifespan)
    daily_prefetch_enabled: bool = True
    daily_prefetch_hour_beijing: int = 0
    daily_prefetch_minute_beijing: int = 5

    llm_platform: str = "coze"
    coze_api_base: str = "https://api.coze.cn"
    coze_access_token: str = ""
    coze_bot_id_daily: str = ""
    coze_bot_id_report: str = ""
    coze_bot_id_compatibility: str = ""
    coze_bot_id_annual: str = ""
    coze_bot_id_chat: str = ""

    # Bailian: OpenAI-compatible base (legacy HTTP path, unused when using Application API)
    bailian_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # Legacy single app id (Coze-fallback path only)
    bailian_app_id: str = ""
    bailian_api_key: str = ""

    # Per-scene 百炼智能体应用 ID（DashScope Application）
    bailian_app_id_daily: str = ""
    bailian_app_id_personality: str = ""
    bailian_app_id_compatibility: str = ""
    bailian_app_id_annual: str = ""
    bailian_app_id_chat: str = ""
    bailian_app_id_planner: str = ""
    bailian_app_id_profile_extractor: str = ""

    # 虎皮椒 xunhupay：微信 / 支付宝各一对 APPID + SECRET
    xunhupay_appid_wechat: str = ""
    xunhupay_appsecret_wechat: str = ""
    xunhupay_appid_alipay: str = ""
    xunhupay_appsecret_alipay: str = ""
    xunhupay_notify_url: str = ""
    xunhupay_api_base: str = "https://api.xunhupay.com"

    # 每日星运深析 (daily guide)
    guide_generation_enabled: bool = True
    guide_generation_hour_beijing: int = 0
    guide_generation_minute_beijing: int = 30
    guide_llm_model: str = "qwen-plus"

    # 首页轮播：热点聚合 + 抓取摘要/封面 + 百炼改写（写入 articles.tags=carousel）
    carousel_generation_enabled: bool = True
    carousel_max_articles: int = Field(default=5, ge=1, le=12)
    carousel_generation_hour_beijing: int = 0
    carousel_generation_minute_beijing: int = 20
    newsnow_api_base: str = "https://newsnow.busiyi.world/api/s"
    carousel_newsnow_source_ids: str = "weibo,zhihu,toutiao,douyin,thepaper"
    carousel_rss_fallback_urls: str = "https://36kr.com/feed,https://www.ifanr.com/feed"
    carousel_page_fetch_max_bytes: int = Field(default=800_000, ge=10_000, le=5_000_000)

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 首页轮播 GET /articles?carousel=1：无「北京当日」发文时的回退窗口（自然日）
    article_carousel_fallback_days: int = Field(default=7, ge=1, le=90)

    # Redis 全局限流（RateLimitMiddleware），窗口内计数；可用环境变量调大自助排障
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    rate_limit_free_per_minute: int = Field(default=60, ge=1, le=600)
    rate_limit_daily_personal_per_minute: int = Field(default=3, ge=1, le=120)
    rate_limit_quicktest_per_minute: int = Field(default=20, ge=1, le=200)
    rate_limit_paid_report_chat_per_minute: int = Field(default=20, ge=1, le=200)
    rate_limit_payment_create_per_minute: int = Field(default=12, ge=1, le=120)

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
