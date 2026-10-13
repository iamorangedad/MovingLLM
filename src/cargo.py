from src.config import BoxSpec, TruckSpec
from src.models import BoxSize, Dimensions, FurnitureItem, FurnitureType

LOOSE_IF_INTACT = {
    FurnitureType.SOFA,
    FurnitureType.BED,
    FurnitureType.WARDROBE,
}

DISASSEMBLED_BOX = {
    FurnitureType.SOFA: BoxSize.XLARGE,
    FurnitureType.BED: BoxSize.XLARGE,
    FurnitureType.WARDROBE: BoxSize.XLARGE,
    FurnitureType.DESK: BoxSize.LARGE,
    FurnitureType.TABLE: BoxSize.LARGE,
    FurnitureType.BOOKSHELF: BoxSize.LARGE,
    FurnitureType.TV_STAND: BoxSize.LARGE,
    FurnitureType.CHAIR: BoxSize.MEDIUM,
    FurnitureType.DRAWER: BoxSize.MEDIUM,
    FurnitureType.OTHER: BoxSize.MEDIUM,
}

LOAD_FIRST = {FurnitureType.WARDROBE, FurnitureType.SOFA, FurnitureType.BED}


def sorted_dims(dimensions: Dimensions) -> tuple[float, float, float]:
    return tuple(sorted((dimensions.length, dimensions.width, dimensions.height)))


def fits_envelope(item: Dimensions, box: Dimensions) -> bool:
    item_dims = sorted_dims(item)
    box_dims = sorted_dims(box)
    return all(side <= limit for side, limit in zip(item_dims, box_dims))


def fits_door(dimensions: Dimensions, truck: TruckSpec) -> bool:
    short_a, short_b, longest = sorted_dims(dimensions)
    door_a, door_b = sorted((truck.door_width_cm, truck.door_height_cm))
    return short_a <= door_a and short_b <= door_b and longest <= truck.max_item_length_cm


def rides_loose(item: FurnitureItem, box_sizes: dict[BoxSize, BoxSpec]) -> bool:
    if item.disassemble:
        return False
    if item.furniture_type in LOOSE_IF_INTACT:
        return True
    largest = box_sizes[BoxSize.XLARGE]
    if not fits_envelope(item.dimensions, largest.dimensions):
        return True
    if item.weight is not None and item.weight > largest.weight_capacity:
        return True
    return False
