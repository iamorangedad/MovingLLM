from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class BoxSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class FurnitureType(str, Enum):
    SOFA = "sofa"
    CHAIR = "chair"
    TABLE = "table"
    BED = "bed"
    WARDROBE = "wardrobe"
    DESK = "desk"
    BOOKSHELF = "bookshelf"
    DRAWER = "drawer"
    TV_STAND = "tv_stand"
    OTHER = "other"


@dataclass
class Dimensions:
    length: float
    width: float
    height: float
    unit: str = "cm"

    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class FurnitureItem:
    name: str
    furniture_type: FurnitureType
    dimensions: Dimensions
    weight: Optional[float] = None
    disassemble: bool = False
    fragile: bool = False
    quantity: int = 1
    description: Optional[str] = None


@dataclass
class BoxRequirement:
    size: BoxSize
    dimensions: Dimensions
    count: int
    weight_capacity: float
    suggested_contents: List[str]


@dataclass
class SpaceEstimation:
    total_volume: float
    packed_volume: float
    truck_size_required: str
    layout_suggestions: List[str]
    packing_efficiency: float


@dataclass
class MovingPlan:
    furniture_items: List[FurnitureItem]
    space_estimation: SpaceEstimation
    box_requirements: List[BoxRequirement]
    total_cost_estimate: Optional[float] = None
    estimated_time: Optional[str] = None
    tips: Optional[List[str]] = None
