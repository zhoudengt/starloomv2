"""Pydantic request/response models."""

from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PersonInput(BaseModel):
    birth_date: str
    gender: Optional[str] = None
    name: Optional[str] = None


class PersonalityReportBody(BaseModel):
    birth_date: str
    birth_time: Optional[str] = None
    gender: Optional[str] = None
    order_id: str


class CompatibilityReportBody(BaseModel):
    person1: PersonInput
    person2: PersonInput
    order_id: str


class AnnualReportBody(BaseModel):
    birth_date: str
    order_id: str
    year: Optional[int] = None


class PaymentCreateBody(BaseModel):
    product_type: str = Field(..., description="personality|compatibility|annual|chat")
    amount: Decimal
    pay_method: str = Field(default="wechat", description="wechat|alipay")


class UserLoginBody(BaseModel):
    device_id: str = Field(..., min_length=8, max_length=64)


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    order_id: Optional[str] = None
