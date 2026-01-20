from typing import List, Dict, Any
from src.models import FurnitureItem, SpaceEstimation, Dimensions
from src.config import settings


class SpaceEstimator:
    def __init__(self):
        self.padding_factor = settings.padding_factor
        self.stacking_factor = settings.stacking_factor

    def estimate_space(self, furniture_items: List[FurnitureItem]) -> SpaceEstimation:
        total_volume = 0
        packable_items = []

        for item in furniture_items:
            item_volume = item.dimensions.volume() * item.quantity
            total_volume += item_volume

            if item.disassemble or item.dimensions.length < 150:
                packable_items.append(item)

        packed_volume = (
            sum(item.dimensions.volume() * item.quantity for item in packable_items)
            * self.padding_factor
        )

        unpacked_volume = sum(
            item.dimensions.volume() * item.quantity
            for item in furniture_items
            if not item.disassemble
        )

        effective_volume = (packed_volume * self.stacking_factor) + unpacked_volume

        truck_size = self._determine_truck_size(effective_volume)

        layout_suggestions = self._generate_layout_suggestions(furniture_items)

        efficiency = (effective_volume / (effective_volume * 1.3)) * 100

        return SpaceEstimation(
            total_volume=total_volume,
            packed_volume=effective_volume,
            truck_size_required=truck_size,
            layout_suggestions=layout_suggestions,
            packing_efficiency=round(efficiency, 2),
        )

    def _determine_truck_size(self, volume: float) -> str:
        volume_m3 = volume / 1000000

        if volume_m3 < 2:
            return "小型厢式车 (约3m³)"
        elif volume_m3 < 5:
            return "中型厢式车 (约5-8m³)"
        elif volume_m3 < 10:
            return "大型厢式车 (约10-15m³)"
        elif volume_m3 < 20:
            return "小型货车 (约15-20m³)"
        else:
            return "大型货车 (20m³以上)"

    def _generate_layout_suggestions(
        self, furniture_items: List[FurnitureItem]
    ) -> List[str]:
        suggestions = []

        has_large_items = any(
            item.dimensions.length > 200 or item.dimensions.height > 200
            for item in furniture_items
        )

        has_furniture = any(
            item.furniture_type.name in ["SOFA", "BED", "WARDROBE"]
            for item in furniture_items
        )

        suggestions.append("先将大型家具（床、沙发、衣柜等）放置在车辆后部")

        if has_furniture:
            suggestions.append("使用家具包裹膜保护表面")

        if has_large_items:
            suggestions.append("大型物品建议垂直放置以节省空间")

        disassemblable = [item for item in furniture_items if item.disassemble]
        if disassemblable:
            suggestions.append(f"建议拆卸 {len(disassemblable)} 件可拆卸家具以节省空间")

        fragile_items = [item for item in furniture_items if item.fragile]
        if fragile_items:
            suggestions.append("易碎物品应放置在顶部并固定")

        suggestions.append("使用绑带固定家具，防止运输中滑动")
        suggestions.append("留出通道便于装卸")

        return suggestions

    def calculate_loading_order(
        self, furniture_items: List[FurnitureItem]
    ) -> List[FurnitureItem]:
        def sort_key(item):
            priority = 0
            if item.furniture_type.name in ["WARDROBE", "SOFA", "BED"]:
                priority = -1
            elif item.furniture_type.name in ["TABLE", "DESK"]:
                priority = 0
            else:
                priority = 1

            size_score = item.dimensions.volume()

            return (priority, -size_score)

        return sorted(furniture_items, key=sort_key)
