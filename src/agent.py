from src.box_calculator import BoxCalculator
from src.config import default_context, get_settings
from src.models import (
    CostBreakdown,
    FurnitureItem,
    MoveContext,
    MovingPlan,
)
from src.provider import MovingLLMProvider, OpenAIProvider
from src.space_estimator import SpaceEstimator


class MovingLLMAgent:
    def __init__(self, provider: MovingLLMProvider | None = None, settings=None):
        self.settings = settings or get_settings()
        self._provider = provider
        self.space_estimator = SpaceEstimator(self.settings)
        self.box_calculator = BoxCalculator(self.settings)

    def analyze_moving_plan(
        self,
        image_paths: list[str],
        context: MoveContext | None = None,
    ) -> MovingPlan:
        furniture_items: list[FurnitureItem] = []
        for image_path in image_paths:
            furniture_items.extend(self.provider.analyze_image(image_path))
        return self.plan_from_items(furniture_items, context, confirmed=False)

    def plan_from_items(
        self,
        furniture_items: list[FurnitureItem],
        context: MoveContext | None = None,
        confirmed: bool | None = None,
    ) -> MovingPlan:
        context = context or default_context()
        if confirmed is True:
            furniture_items = [
                item.model_copy(update={"dimensions_confirmed": True})
                for item in furniture_items
            ]

        box_requirements = self.box_calculator.calculate_box_requirements(
            furniture_items
        )
        space_estimation = self.space_estimator.estimate_space(
            furniture_items, box_requirements
        )
        loading_order = self.space_estimator.loading_order(furniture_items)
        tips = self.box_calculator.generate_packing_tips(furniture_items)
        tips.extend(space_estimation.layout_suggestions)
        if furniture_items and not all(
            item.dimensions_confirmed for item in furniture_items
        ):
            tips.insert(0, "尺寸和重量来自图像估算，确认前不要据此下单")

        cost = self._estimate_cost(
            space_estimation.effective_volume_cm3,
            space_estimation.trips,
            box_requirements,
            context,
            furniture_items,
        )
        estimated_time = self._estimate_moving_time(
            furniture_items, space_estimation.effective_volume_cm3, context
        )
        dimensions_confirmed = bool(furniture_items) and all(
            item.dimensions_confirmed for item in furniture_items
        )
        return MovingPlan(
            furniture_items=furniture_items,
            space_estimation=space_estimation,
            box_requirements=box_requirements,
            loading_order=loading_order,
            total_cost_estimate=cost.total,
            cost_breakdown=cost,
            estimated_time=estimated_time,
            tips=tips,
            context=context,
            dimensions_confirmed=dimensions_confirmed,
        )

    def get_recommendations(self, plan: MovingPlan) -> str:
        return self.provider.recommend(plan)

    @property
    def provider(self) -> MovingLLMProvider:
        if self._provider is None:
            self._provider = OpenAIProvider(settings=self.settings)
        return self._provider

    def _estimate_cost(
        self, effective_cm3, trips, box_requirements, context, furniture_items
    ) -> CostBreakdown:
        rates = self.settings.cost
        volume_m3 = effective_cm3 / 1_000_000
        piece_count = sum(item.quantity for item in furniture_items)
        transport = round(
            volume_m3 * rates.transport_per_m3
            + context.distance_km * rates.transport_per_km * trips,
            2,
        )
        boxes = 0.0
        for requirement in box_requirements:
            boxes += self.settings.box_sizes[requirement.size].price * requirement.count
        boxes = round(boxes, 2)
        labor = round(
            max(rates.labor_minimum, volume_m3 * rates.labor_per_m3)
            + context.stair_floors() * rates.floor_surcharge * piece_count,
            2,
        )
        return CostBreakdown(
            transport=transport,
            boxes=boxes,
            labor=labor,
            total=round(transport + boxes + labor, 2),
        )

    def _estimate_moving_time(self, furniture_items, effective_cm3, context) -> str:
        rates = self.settings.time
        piece_count = sum(item.quantity for item in furniture_items)
        volume_m3 = effective_cm3 / 1_000_000
        minutes = int(
            round(
                piece_count * rates.minutes_per_item
                + volume_m3 * rates.minutes_per_m3
                + context.stair_floors()
                * rates.minutes_per_floor_without_elevator
                * piece_count
            )
        )
        hours, remainder = divmod(minutes, 60)
        if hours == 0:
            return f"约 {remainder} 分钟"
        text = f"约 {hours} 小时 {remainder} 分钟"
        if hours >= 8:
            text += "（建议分天进行）"
        return text
