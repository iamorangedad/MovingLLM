from typing import List
from openai import OpenAI

from src.config import settings
from src.models import MovingPlan, FurnitureItem
from src.image_analyzer import ImageAnalyzer
from src.space_estimator import SpaceEstimator
from src.box_calculator import BoxCalculator


class MovingLLMAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.image_analyzer = ImageAnalyzer()
        self.space_estimator = SpaceEstimator()
        self.box_calculator = BoxCalculator()

    def analyze_moving_plan(self, image_paths: List[str]) -> MovingPlan:
        furniture_items = []

        for image_path in image_paths:
            items = self.image_analyzer.analyze_furniture_from_image(image_path)
            furniture_items.extend(items)

        space_estimation = self.space_estimator.estimate_space(furniture_items)

        box_requirements = self.box_calculator.calculate_box_requirements(
            furniture_items
        )

        loading_order = self.space_estimator.calculate_loading_order(furniture_items)

        tips = self.box_calculator.generate_packing_tips(furniture_items)
        tips.extend(space_estimation.layout_suggestions)

        estimated_time = self._estimate_moving_time(
            len(furniture_items), space_estimation.total_volume
        )

        cost_estimate = self._estimate_cost(
            space_estimation.packed_volume, box_requirements
        )

        plan = MovingPlan(
            furniture_items=furniture_items,
            space_estimation=space_estimation,
            box_requirements=box_requirements,
            total_cost_estimate=cost_estimate,
            estimated_time=estimated_time,
            tips=tips,
        )

        return plan

    def _estimate_moving_time(self, furniture_count: int, volume: float) -> str:
        base_time = furniture_count * 15  # 每件15分钟
        volume_factor = volume / 1000000  # m^3
        time_addition = int(volume_factor * 30)  # 每立方米30分钟
        total_minutes = base_time + time_addition

        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours == 0:
            return f"约 {minutes} 分钟"
        elif hours < 4:
            return f"约 {hours} 小时 {minutes} 分钟"
        else:
            return f"约 {hours} 小时（建议分天进行）"

    def _estimate_cost(self, volume: float, box_requirements: List) -> float:
        volume_m3 = volume / 1000000

        transport_cost = volume_m3 * 150  # 每立方米150元

        box_cost = 0
        for req in box_requirements:
            prices = {"small": 8, "medium": 15, "large": 25, "xlarge": 40}
            box_cost += prices[req.size] * req.count

        labor_cost = max(200, volume_m3 * 80)  # 最低200元

        total_cost = transport_cost + box_cost + labor_cost

        return round(total_cost, 2)

    def get_recommendations(self, plan: MovingPlan) -> str:
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个搬家规划专家。根据提供的家具清单和空间估算，给出专业的搬家建议和注意事项。",
                },
                {"role": "user", "content": self._format_plan_for_llm(plan)},
            ],
            max_tokens=1500,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        return content if content else ""

    def _format_plan_for_llm(self, plan: MovingPlan) -> str:
        furniture_list = "\n".join(
            [
                f"- {item.name} ({item.furniture_type.name}): {item.dimensions.length}x{item.dimensions.width}x{item.dimensions.height}cm"
                for item in plan.furniture_items
            ]
        )

        box_list = "\n".join(
            [
                f"- {req.size}: {req.count}个 ({req.dimensions.length}x{req.dimensions.width}x{req.dimensions.height}cm)"
                for req in plan.box_requirements
            ]
        )

        prompt = f"""家具清单:
{furniture_list}

空间估算:
- 总体积: {plan.space_estimation.total_volume} cm³
- 所需车辆: {plan.space_estimation.truck_size_required}
- 装载效率: {plan.space_estimation.packing_efficiency}%

纸箱需求:
{box_list}

预计费用: ¥{plan.total_cost_estimate}
预计时间: {plan.estimated_time}

请提供详细的搬家建议，包括物品保护、装载顺序、注意事项等。"""

        return prompt
