import math
from dataclasses import dataclass, field

from src.cargo import DISASSEMBLED_BOX, fits_envelope, rides_loose
from src.config import get_settings
from src.models import BoxRequirement, BoxSize, FurnitureItem


@dataclass
class _Bin:
    size: BoxSize
    volume: float = 0
    weight: float = 0
    names: list[str] = field(default_factory=list)


class BoxCalculator:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.box_sizes = self.settings.box_sizes
        self.fill_factor = self.settings.packing.box_fill_factor

    def calculate_box_requirements(
        self, furniture_items: list[FurnitureItem]
    ) -> list[BoxRequirement]:
        counts = {size: 0 for size in BoxSize}
        preset_labels: dict[BoxSize, list[str]] = {size: [] for size in BoxSize}
        rigid_names: dict[BoxSize, list[str]] = {size: [] for size in BoxSize}
        rigid: list[FurnitureItem] = []

        for item in furniture_items:
            if rides_loose(item, self.box_sizes):
                continue
            if item.disassemble:
                size, count = self._disassembled_boxes(item)
                if count:
                    counts[size] += count
                    preset_labels[size].append(f"{item.name} x{item.quantity}")
            else:
                rigid.append(item)

        for packed in self._pack_rigid(rigid):
            counts[packed.size] += 1
            rigid_names[packed.size].extend(packed.names)

        requirements = []
        for size in BoxSize:
            if counts[size] <= 0:
                continue
            spec = self.box_sizes[size]
            requirements.append(
                BoxRequirement(
                    size=size,
                    dimensions=spec.dimensions,
                    count=counts[size],
                    weight_capacity=spec.weight_capacity,
                    suggested_contents=preset_labels[size] + self._summarize(rigid_names[size]),
                )
            )
        return requirements

    def _disassembled_boxes(self, item: FurnitureItem) -> tuple[BoxSize, int]:
        size = DISASSEMBLED_BOX[item.furniture_type]
        spec = self.box_sizes[size]
        usable = spec.dimensions.volume() * self.fill_factor
        total_volume = item.dimensions.volume() * item.quantity
        by_volume = math.ceil(total_volume / usable) if total_volume > 0 else 0
        by_weight = 0
        if item.weight is not None:
            by_weight = math.ceil((item.weight * item.quantity) / spec.weight_capacity)
        return size, max(by_volume, by_weight)

    def _smallest_box(self, item: FurnitureItem) -> BoxSize:
        for size in BoxSize:
            spec = self.box_sizes[size]
            weight_ok = item.weight is None or item.weight <= spec.weight_capacity
            if fits_envelope(item.dimensions, spec.dimensions) and weight_ok:
                return size
        raise RuntimeError(f"{item.name} 应判定为散装，不应进入装箱")

    def _pack_rigid(self, items: list[FurnitureItem]) -> list[_Bin]:
        units: list[tuple[FurnitureItem, BoxSize]] = []
        for item in items:
            size = self._smallest_box(item)
            units.extend((item, size) for _ in range(item.quantity))
        units.sort(key=lambda pair: pair[0].dimensions.volume(), reverse=True)

        bins: list[_Bin] = []
        for item, size in units:
            spec = self.box_sizes[size]
            weight = item.weight or 0
            placed = False
            for packed in bins:
                if packed.size != size or packed.volume == 0:
                    continue
                within_volume = (
                    packed.volume + item.dimensions.volume()
                    <= spec.dimensions.volume() * self.fill_factor
                )
                within_weight = packed.weight + weight <= spec.weight_capacity
                if within_volume and within_weight:
                    packed.volume += item.dimensions.volume()
                    packed.weight += weight
                    packed.names.append(item.name)
                    placed = True
                    break
            if not placed:
                bins.append(
                    _Bin(
                        size=size,
                        volume=item.dimensions.volume(),
                        weight=weight,
                        names=[item.name],
                    )
                )
        return bins

    @staticmethod
    def _summarize(names: list[str]) -> list[str]:
        counts: dict[str, int] = {}
        order: list[str] = []
        for name in names:
            if name not in counts:
                order.append(name)
                counts[name] = 0
            counts[name] += 1
        return [f"{name} x{counts[name]}" for name in order]

    def generate_packing_tips(self, furniture_items: list[FurnitureItem]) -> list[str]:
        tips = []
        fragile = sum(item.quantity for item in furniture_items if item.fragile)
        if fragile:
            tips.append(f"有 {fragile} 件易碎物品，使用防震材料，并放在上层")

        disassembled = [item for item in furniture_items if item.disassemble]
        if disassembled:
            count = sum(item.quantity for item in disassembled)
            tips.append(f"可拆卸 {count} 件，拆下的零件按纸箱承重分装")

        missing_weight = [
            item.name for item in furniture_items if item.weight is None
        ]
        if missing_weight:
            tips.append("部分物品没有重量，箱数未按承重加计，确认重量后请重算")

        if any(not rides_loose(item, self.box_sizes) for item in furniture_items):
            tips.append("单箱重量不要超过该规格承重，箱外标上内容和房间")
        return tips
