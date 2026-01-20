from typing import List
from src.models import FurnitureItem, BoxRequirement, BoxSize, Dimensions
from src.config import settings


class BoxCalculator:
    def __init__(self):
        self.box_sizes = {
            BoxSize.SMALL: {
                "dimensions": Dimensions(30, 30, 30),
                "weight_capacity": 10,
            },
            BoxSize.MEDIUM: {
                "dimensions": Dimensions(45, 45, 45),
                "weight_capacity": 20,
            },
            BoxSize.LARGE: {
                "dimensions": Dimensions(60, 60, 60),
                "weight_capacity": 30,
            },
            BoxSize.XLARGE: {
                "dimensions": Dimensions(75, 75, 75),
                "weight_capacity": 40,
            },
        }

    def calculate_box_requirements(
        self, furniture_items: List[FurnitureItem]
    ) -> List[BoxRequirement]:
        requirements = {}

        for item in furniture_items:
            if not item.disassemble and item.dimensions.volume() > 300000:
                continue

            boxes_needed = self._estimate_boxes_for_item(item)

            for size, count in boxes_needed.items():
                if size not in requirements:
                    requirements[size] = BoxRequirement(
                        size=size,
                        dimensions=self.box_sizes[size]["dimensions"],
                        count=0,
                        weight_capacity=self.box_sizes[size]["weight_capacity"],
                        suggested_contents=[],
                    )
                requirements[size].count += count
                requirements[size].suggested_contents.append(f"{item.name} x{count}")

        return list(requirements.values())

    def _estimate_boxes_for_item(self, item: FurnitureItem) -> dict:
        boxes = {size: 0 for size in BoxSize}

        if item.furniture_type.name in ["SOFA", "BED", "WARDROBE", "DESK"]:
            return self._estimate_large_furniture_boxes(item)
        elif item.furniture_type.name in ["CHAIR", "TABLE", "TV_STAND"]:
            return self._estimate_medium_furniture_boxes(item)
        else:
            return self._estimate_small_furniture_boxes(item)

    def _estimate_large_furniture_boxes(self, item: FurnitureItem) -> dict:
        boxes = {size: 0 for size in BoxSize}

        if item.disassemble:
            volume = item.dimensions.volume()

            xlarge_boxes = int(
                volume // self.box_sizes[BoxSize.XLARGE]["dimensions"].volume()
            )
            remaining_volume = (
                volume % self.box_sizes[BoxSize.XLARGE]["dimensions"].volume()
            )

            if (
                remaining_volume
                > self.box_sizes[BoxSize.LARGE]["dimensions"].volume() * 0.5
            ):
                boxes[BoxSize.XLARGE] = xlarge_boxes + 1
            elif remaining_volume > 0:
                boxes[BoxSize.XLARGE] = xlarge_boxes
                boxes[BoxSize.LARGE] = 1
            else:
                boxes[BoxSize.XLARGE] = xlarge_boxes
        else:
            boxes[BoxSize.XLARGE] = 0

        return boxes

    def _estimate_medium_furniture_boxes(self, item: FurnitureItem) -> dict:
        boxes = {size: 0 for size in BoxSize}

        if item.disassemble:
            volume = item.dimensions.volume()

            large_boxes = int(
                volume // self.box_sizes[BoxSize.LARGE]["dimensions"].volume()
            )
            remaining_volume = (
                volume % self.box_sizes[BoxSize.LARGE]["dimensions"].volume()
            )

            if (
                remaining_volume
                > self.box_sizes[BoxSize.MEDIUM]["dimensions"].volume() * 0.5
            ):
                boxes[BoxSize.LARGE] = large_boxes + 1
            elif remaining_volume > 0:
                boxes[BoxSize.LARGE] = large_boxes
                boxes[BoxSize.MEDIUM] = 1
            else:
                boxes[BoxSize.LARGE] = large_boxes
        else:
            boxes[BoxSize.LARGE] = 0

        return boxes

    def _estimate_small_furniture_boxes(self, item: FurnitureItem) -> dict:
        boxes = {size: 0 for size in BoxSize}

        volume = item.dimensions.volume() * item.quantity

        medium_boxes = int(
            volume // self.box_sizes[BoxSize.MEDIUM]["dimensions"].volume()
        )
        remaining_volume = (
            volume % self.box_sizes[BoxSize.MEDIUM]["dimensions"].volume()
        )

        if (
            remaining_volume
            > self.box_sizes[BoxSize.SMALL]["dimensions"].volume() * 0.5
        ):
            boxes[BoxSize.MEDIUM] = medium_boxes + 1
        elif remaining_volume > 0:
            boxes[BoxSize.MEDIUM] = medium_boxes
            boxes[BoxSize.SMALL] = 1
        else:
            boxes[BoxSize.MEDIUM] = medium_boxes

        return boxes

    def calculate_additional_boxes(
        self, furniture_count: int, total_volume: float
    ) -> dict:
        additional = {size: 0 for size in BoxSize}

        small_boxes = min(furniture_count // 3, 5)
        medium_boxes = min(furniture_count // 5, 3)

        additional[BoxSize.SMALL] = small_boxes
        additional[BoxSize.MEDIUM] = medium_boxes

        volume_m3 = total_volume / 1000000
        if volume_m3 > 5:
            additional[BoxSize.LARGE] = min(int(volume_m3 / 3), 5)

        return additional

    def generate_packing_tips(self, furniture_items: List[FurnitureItem]) -> List[str]:
        tips = []

        fragile_count = sum(1 for item in furniture_items if item.fragile)
        if fragile_count > 0:
            tips.append(f"有 {fragile_count} 件易碎物品，建议使用防震包装材料")

        disassemble_count = sum(1 for item in furniture_items if item.disassemble)
        if disassemble_count > 0:
            tips.append(f"可以拆卸 {disassemble_count} 件家具以节省空间")

        heavy_items = [
            item for item in furniture_items if item.weight and item.weight > 20
        ]
        if heavy_items:
            tips.append("重物应使用加固纸箱，并分散放置")

        tips.append("每箱重量建议不超过25kg")
        tips.append("物品间应填充缓冲材料防止碰撞")
        tips.append("在纸箱外标注内容物和房间位置")

        return tips
