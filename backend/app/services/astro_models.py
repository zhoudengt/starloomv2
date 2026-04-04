"""Structured natal / transit / synastry data for prompts (Pydantic v2)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanetPosition(BaseModel):
    """Single celestial point in the chart."""

    name: str  # display: 太阳 / Sun
    name_en: str
    sign_cn: str
    sign_en: str  # aries, taurus, ...
    degree: float = Field(description="Degree within sign (0-30)")
    abs_degree: float = Field(description="Absolute ecliptic longitude 0-360")
    retrograde: bool = False
    house: Optional[int] = Field(default=None, description="House 1-12 if known")


class HouseCusp(BaseModel):
    house: int  # 1-12
    sign_cn: str
    sign_en: str
    degree: float


class Aspect(BaseModel):
    planet1: str
    planet2: str
    aspect_type: str  # conjunction, trine, ...
    aspect_type_cn: str  # 合、三分、...
    aspect_degree: int  # 0,60,90,120,180
    orb: float
    applying: Optional[bool] = None


class NatalChartData(BaseModel):
    birth_date: str
    birth_time: Optional[str] = None
    location_label: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    tz_str: str = "Asia/Shanghai"
    has_birth_time: bool = True
    precision_note: Optional[str] = Field(
        default=None,
        description="Human-readable note when houses omitted or moon approximate",
    )
    planets: list[PlanetPosition] = Field(default_factory=list)
    ascendant: Optional[PlanetPosition] = None
    mc: Optional[PlanetPosition] = None
    houses: Optional[list[HouseCusp]] = None
    aspects: list[Aspect] = Field(default_factory=list)
    element_distribution: dict[str, float] = Field(default_factory=dict)
    modality_distribution: dict[str, float] = Field(default_factory=dict)
    dominant_element: str = ""
    dominant_modality: str = ""
    lunar_phase_name: Optional[str] = None
    lunar_phase_emoji: Optional[str] = None


class TransitAspect(BaseModel):
    natal_planet: str
    transit_planet: str
    aspect_type: str
    aspect_type_cn: str
    aspect_degree: int
    orb: float
    movement: Optional[str] = None  # Applying / Separating


class TransitData(BaseModel):
    transit_date: str
    transit_time: str = "12:00"
    location_label: Optional[str] = None
    transit_planets: list[PlanetPosition] = Field(default_factory=list)
    natal_sun_summary: str = ""
    aspects_to_natal: list[TransitAspect] = Field(default_factory=list)
    moon_phase_name: Optional[str] = None
    moon_phase_emoji: Optional[str] = None
    mercury_retrograde: Optional[bool] = None


class SynastryData(BaseModel):
    aspects: list[Aspect] = Field(default_factory=list)
    relationship_score: Optional[int] = None
    relationship_label: Optional[str] = None  # e.g. Important
    score_highlights: list[str] = Field(default_factory=list)


class AnnualTransitSummary(BaseModel):
    """Lightweight annual outlook: major slow-planet themes for the year."""

    year: int
    highlights: list[str] = Field(default_factory=list)
    natal_chart: Optional[NatalChartData] = None
