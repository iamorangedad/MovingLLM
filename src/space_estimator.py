import math

from src.cargo import LOAD_FIRST, fits_door, rides_loose
from src.config import get_settings
from src.models import BoxRequirement, FurnitureItem, SpaceEstimation


class SpaceEstimator:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def estimate_space(
        self,
        furniture_items: list[FurnitureItem],
        box_requirements: list[BoxRequirement],
    ) -> SpaceEstimation:
        packing = self.settings.packing
        total_volume = sum(
            item.dimensions.volume() * item.quantity for item in furniture_items
        )
        loose_items = [
            item
            for item in furniture_items
            if rides_loose(item, self.settings.box_sizes)
        ]
        loose_volume = sum(
            item.dimensions.volume() * item.quantity * packing.loose_padding_factor
            for item in loose_items
        )
        box_volume = sum(
            req.dimensions.volume() * req.count for req in box_requirements
        )
        effective = loose_volume + box_volume * packing.stacking_factor

        truck, trips, blocked = self._select_truck(loose_items, effective)
        hired_m3 = trips * truck.capacity_m3
        effective_m3 = effective / 1_000_000
        efficiency = round(effective_m3 / hired_m3 * 100, 2) if hired_m3 else 0

        return SpaceEstimation(
            total_volume_cm3=total_volume,
            loose_volume_cm3=loose_volume,
            box_volume_cm3=box_volume,
            effective_volume_cm3=effective,
            truck_name=truck.name,
            truck_capacity_m3=truck.capacity_m3,
            trips=trips,
            packing_efficiency=efficiency,
            layout_suggestions=self._layout_suggestions(
                loose_items, trips, blocked
            ),
            items_exceed_all_doors=blocked,
        )

    def _select_truck(self, loose_items: list[FurnitureItem], effective_cm3: float):
        trucks = self.settings.trucks
        accessible = [
            truck
            for truck in trucks
            if all(fits_door(item.dimensions, truck) for item in loose_items)
        ]
        blocked: list[str] = []
        pool = accessible
        if not pool:
            pool = trucks
            blocked = [
                item.name
                for item in loose_items
                if not any(fits_door(item.dimensions, truck) for truck in trucks)
            ]

        effective_m3 = effective_cm3 / 1_000_000
        fitting = [truck for truck in pool if truck.capacity_m3 >= effective_m3]
        if fitting:
            truck = min(fitting, key=lambda item: item.capacity_m3)
            return truck, 1, blocked

        truck = max(pool, key=lambda item: item.capacity_m3)
        trips = max(1, math.ceil(effective_m3 / truck.capacity_m3))
        return truck, trips, blocked

    def loading_order(self, furniture_items: list[FurnitureItem]) -> list[str]:
        def sort_key(item: FurnitureItem):
            loose = rides_loose(item, self.settings.box_sizes)
            if loose and item.furniture_type in LOAD_FIRST:
                group = 0
            elif loose:
                group = 1
            else:
                group = 2
            return (group, -item.dimensions.volume() * item.quantity)

        ordered = sorted(furniture_items, key=sort_key)
        return [
            f"{item.name}（{item.furniture_type.value}） x{item.quantity}"
            for item in ordered
        ]

    @staticmethod
    def _layout_suggestions(
        loose_items: list[FurnitureItem], trips: int, blocked: list[str]
    ) -> list[str]:
        suggestions = []
        if any(item.furniture_type in LOAD_FIRST for item in loose_items):
            suggestions.append("衣柜、沙发、床先装入车厢后部，再用绑带固定")
        elif loose_items:
            suggestions.append("散装家具贴车厢壁放置，并用绑带固定")
        if any(item.fragile for item in loose_items):
            suggestions.append("易碎的散装物品放在上层，避免被重物压住")
        if trips > 1:
            suggestions.append(f"一车装不下，按当前车型需要 {trips} 趟")
        if blocked:
            names = "、".join(blocked)
            suggestions.append(f"{names} 超过全部车型的车厢门或最长边，需要另选车辆")
        if not suggestions:
            suggestions.append("物品均可装箱，纸箱重的在下、轻的在上")
        return suggestions
