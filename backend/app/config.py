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

    llm_platform: str = "coze"
    coze_api_base: str = "https://api.coze.cn"
    coze_access_token: str = ""
    coze_bot_id_daily: str = ""
    coze_bot_id_report: str = ""
    coze_bot_id_compatibility: str = ""
    coze_bot_id_annual: str = ""
    coze_bot_id_chat: str = ""

    bailian_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_app_id: str = ""
    bailian_api_key: str = ""

    xorpay_app_id: str = ""
    xorpay_app_secret: str = ""
    xorpay_notify_url: str = ""
    xorpay_api_base: str = "https://xorpay.com"

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
