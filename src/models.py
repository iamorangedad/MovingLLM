from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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


class Dimensions(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    unit: str = "cm"

    def volume(self) -> float:
        return self.length * self.width * self.height


class FurnitureItem(BaseModel):
    name: str
    furniture_type: FurnitureType
    dimensions: Dimensions
    weight: Optional[float] = Field(default=None, gt=0)
    disassemble: bool = False
    fragile: bool = False
    quantity: int = Field(default=1, ge=1)
    description: Optional[str] = None
    dimensions_confirmed: bool = False


class BoxRequirement(BaseModel):
    size: BoxSize
    dimensions: Dimensions
    count: int = Field(ge=0)
    weight_capacity: float
    suggested_contents: list[str] = Field(default_factory=list)


class SpaceEstimation(BaseModel):
    total_volume_cm3: float
    loose_volume_cm3: float
    box_volume_cm3: float
    effective_volume_cm3: float
    truck_name: str
    truck_capacity_m3: float
    trips: int = Field(ge=1)
    packing_efficiency: float
    layout_suggestions: list[str]
    items_exceed_all_doors: list[str] = Field(default_factory=list)


class MoveContext(BaseModel):
    distance_km: float = Field(default=10, ge=0)
    origin_floor: int = Field(default=1, ge=1)
    destination_floor: int = Field(default=1, ge=1)
    origin_has_elevator: bool = True
    destination_has_elevator: bool = True

    def stair_floors(self) -> int:
        stairs = 0
        if not self.origin_has_elevator:
            stairs += self.origin_floor - 1
        if not self.destination_has_elevator:
            stairs += self.destination_floor - 1
        return stairs


class CostBreakdown(BaseModel):
    transport: float
    boxes: float
    labor: float
    total: float


class MovingPlan(BaseModel):
    furniture_items: list[FurnitureItem]
    space_estimation: SpaceEstimation
    box_requirements: list[BoxRequirement]
    loading_order: list[str]
    total_cost_estimate: float
    cost_breakdown: CostBreakdown
    estimated_time: str
    tips: list[str]
    context: MoveContext
    dimensions_confirmed: bool


class RecommendResponse(BaseModel):
    plan: MovingPlan
    recommendations: str


class RecalculateRequest(BaseModel):
    furniture_items: list[FurnitureItem]
    context: MoveContext = Field(default_factory=MoveContext)
