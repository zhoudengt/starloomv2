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

    # Demo: skip paid-order checks and auto-use demo orders (never enable in production)
    demo_mode: bool = True

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

    # 虎皮椒 xunhupay：微信 / 支付宝各一对 APPID + SECRET
    xunhupay_appid_wechat: str = ""
    xunhupay_appsecret_wechat: str = ""
    xunhupay_appid_alipay: str = ""
    xunhupay_appsecret_alipay: str = ""
    xunhupay_notify_url: str = ""
    xunhupay_api_base: str = "https://api.xunhupay.com"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

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
