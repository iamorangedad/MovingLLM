import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.models import BoxSize, Dimensions, MoveContext

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"


class BoxSpec(BaseModel):
    dimensions: Dimensions
    weight_capacity: float = Field(gt=0)
    price: float = Field(ge=0)


class TruckSpec(BaseModel):
    name: str
    capacity_m3: float = Field(gt=0)
    length_cm: float = Field(gt=0)
    width_cm: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    max_item_length_cm: float = Field(gt=0)
    door_width_cm: float = Field(gt=0)
    door_height_cm: float = Field(gt=0)


class ImageConfig(BaseModel):
    max_edge_px: int = Field(default=2048, gt=0)
    jpeg_quality: int = Field(default=85, ge=30, le=95)
    max_bytes: int = Field(default=4_194_304, gt=0)
    confidence_threshold: float = Field(default=0.7, ge=0, le=1)
    max_detections: int = Field(default=10, ge=1)


class PackingConfig(BaseModel):
    loose_padding_factor: float = Field(gt=0)
    box_fill_factor: float = Field(gt=0, le=1)
    stacking_factor: float = Field(gt=0, le=1)


class CostConfig(BaseModel):
    transport_per_m3: float = Field(ge=0)
    transport_per_km: float = Field(ge=0)
    labor_per_m3: float = Field(ge=0)
    labor_minimum: float = Field(ge=0)
    floor_surcharge: float = Field(ge=0)


class TimeConfig(BaseModel):
    minutes_per_item: float = Field(ge=0)
    minutes_per_m3: float = Field(ge=0)
    minutes_per_floor_without_elevator: float = Field(ge=0)


class Settings(BaseModel):
    openai_api_key: str = ""
    openai_model: str
    image: ImageConfig
    box_sizes: dict[BoxSize, BoxSpec]
    packing: PackingConfig
    trucks: list[TruckSpec]
    cost: CostConfig
    time: TimeConfig
    move_defaults: MoveContext


def load_settings(path: Path | None = None) -> Settings:
    load_dotenv()
    raw = yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8"))

    box_sizes: dict[BoxSize, BoxSpec] = {}
    for key, value in raw["box_sizes"].items():
        length, width, height = value["dimensions"]
        box_sizes[BoxSize(key)] = BoxSpec(
            dimensions=Dimensions(length=length, width=width, height=height),
            weight_capacity=value["weight_capacity"],
            price=value["price"],
        )

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", raw["model"]),
        image=ImageConfig.model_validate(raw["image"]),
        box_sizes=box_sizes,
        packing=PackingConfig.model_validate(raw["packing"]),
        trucks=[TruckSpec.model_validate(item) for item in raw["trucks"]],
        cost=CostConfig.model_validate(raw["cost"]),
        time=TimeConfig.model_validate(raw["time"]),
        move_defaults=MoveContext.model_validate(raw["move_defaults"]),
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def default_context() -> MoveContext:
    return get_settings().move_defaults.model_copy(deep=True)
