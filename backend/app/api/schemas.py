"""Pydantic request/response models."""

from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PersonInput(BaseModel):
    birth_date: str
    gender: Optional[str] = None
    name: Optional[str] = None
    birth_time: Optional[str] = Field(default=None, description="HH:MM")
    birth_place_name: Optional[str] = Field(default=None, description="城市名，如 北京")
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = Field(default=None, description="IANA，如 Asia/Shanghai")


class PersonalityReportBody(BaseModel):
    birth_date: str
    birth_time: Optional[str] = None
    gender: Optional[str] = None
    birth_place_name: Optional[str] = None
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = None
    order_id: Optional[str] = None


class CompatibilityReportBody(BaseModel):
    person1: PersonInput
    person2: PersonInput
    order_id: Optional[str] = None


class AnnualReportBody(BaseModel):
    birth_date: str
    birth_time: Optional[str] = None
    birth_place_name: Optional[str] = None
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = None
    order_id: Optional[str] = None
    year: Optional[int] = None


class PaymentCreateBody(BaseModel):
    product_type: str = Field(
        ...,
        description="personality|compatibility|annual|chat|personality_career|personality_love|personality_growth|astro_event|season_pass|daily_guide",
    )
    amount: Decimal
    pay_method: str = Field(default="wechat", description="wechat|alipay")
    extra_data: Optional[dict[str, Any]] = Field(default=None, description="业务参数，支付成功后生成报告用")


class UserLoginBody(BaseModel):
    device_id: str = Field(..., min_length=8, max_length=64)
    referral_code: Optional[str] = Field(default=None, description="邀请码（可选，仅新用户绑定）")


class PersonalityDlcBody(BaseModel):
    pack: str = Field(..., description="career|love|growth")
    birth_date: str
    birth_time: Optional[str] = None
    gender: Optional[str] = None
    birth_place_name: Optional[str] = None
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = None
    order_id: Optional[str] = None


class AstroEventBody(BaseModel):
    event_key: str = Field(default="mercury_retrograde", description="mercury_retrograde|eclipse|solstice")
    birth_date: str
    birth_time: Optional[str] = None
    birth_place_name: Optional[str] = None
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = None
    order_id: Optional[str] = None


class GroupBuyCreateBody(BaseModel):
    product_type: str = Field(default="compatibility")
    target_count: int = Field(default=2, ge=2, le=3)


class AssistCreateBody(BaseModel):
    report_id: Optional[str] = None


class CompatShareCreateBody(BaseModel):
    person1_name: Optional[str] = None
    person2_name: Optional[str] = None
    preview_score: Optional[int] = Field(default=87, ge=60, le=99)


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    order_id: Optional[str] = None


class QuickTestBody(BaseModel):
    birth_date: str = Field(..., description="YYYY-MM-DD")
    gender: Optional[str] = Field(default=None, description="male|female")
    birth_time: Optional[str] = Field(default=None, description="HH:MM")
    birth_place_name: Optional[str] = None
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = None


class UserProfilePatch(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=50)
    birth_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    birth_time: Optional[str] = Field(default=None, description="HH:MM")
    gender: Optional[str] = Field(default=None, description="male|female|unknown")
    birth_place_name: Optional[str] = None
    birth_place_lat: Optional[float] = None
    birth_place_lon: Optional[float] = None
    birth_tz: Optional[str] = None
