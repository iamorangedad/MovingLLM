from dataclasses import dataclass
from itertools import permutations

from src.cargo import LOAD_FIRST, rides_loose
from src.config import TruckSpec, get_settings
from src.models import (
    BoxRequirement,
    BoxSize,
    CargoLayout,
    CargoPlacement,
    FurnitureItem,
    FurnitureType,
    PlacementLevel,
    PlacementSide,
)

SIZE_TEXT = {
    BoxSize.SMALL: "小号",
    BoxSize.MEDIUM: "中号",
    BoxSize.LARGE: "大号",
    BoxSize.XLARGE: "超大",
}

FLAT_TYPES = {
    FurnitureType.SOFA,
    FurnitureType.BED,
    FurnitureType.DESK,
    FurnitureType.TABLE,
    FurnitureType.TV_STAND,
}
UPRIGHT_TYPES = {
    FurnitureType.WARDROBE,
    FurnitureType.BOOKSHELF,
    FurnitureType.DRAWER,
}
SIDE_TEXT = {
    PlacementSide.LEFT: "左侧",
    PlacementSide.CENTER: "中间",
    PlacementSide.RIGHT: "右侧",
}
LEVEL_TEXT = {
    PlacementLevel.BOTTOM: "底层",
    PlacementLevel.MIDDLE: "中层",
    PlacementLevel.TOP: "上层",
}


@dataclass
class _Piece:
    name: str
    kind: str
    length: float
    width: float
    height: float
    fragile: bool
    prefer: str
    furniture_type: str | None
    sort_key: tuple


@dataclass
class _Placed:
    piece: _Piece
    x: float
    y: float
    z: float
    width: float
    height: float
    depth: float
    trip: int


class CargoLayoutPlanner:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def place(
        self,
        furniture_items: list[FurnitureItem],
        box_requirements: list[BoxRequirement],
        truck_name: str,
    ) -> CargoLayout:
        truck = next(
            (item for item in self.settings.trucks if item.name == truck_name),
            self.settings.trucks[-1],
        )
        pieces = _pieces(furniture_items, box_requirements, self.settings.box_sizes)
        placed, unplaced = _pack(pieces, truck)
        return CargoLayout(
            truck_name=truck.name,
            length_cm=truck.length_cm,
            width_cm=truck.width_cm,
            height_cm=truck.height_cm,
            door_width_cm=truck.door_width_cm,
            door_height_cm=truck.door_height_cm,
            trips=max((item.trip for item in placed), default=0),
            placements=[_placement(item, truck) for item in placed],
            unplaced=[item.name for item in unplaced],
        )


def _pieces(furniture_items, box_requirements, box_sizes) -> list[_Piece]:
    pieces: list[_Piece] = []
    index = 0
    for item in furniture_items:
        if not rides_loose(item, box_sizes):
            continue
        for copy in range(item.quantity):
            name = item.name if item.quantity == 1 else f"{item.name} {copy + 1}"
            group = 0 if item.furniture_type in LOAD_FIRST else 1
            pieces.append(
                _Piece(
                    name=name,
                    kind="loose",
                    length=item.dimensions.length,
                    width=item.dimensions.width,
                    height=item.dimensions.height,
                    fragile=item.fragile,
                    prefer=_prefer(item.furniture_type),
                    furniture_type=item.furniture_type.value,
                    sort_key=(
                        group,
                        1 if item.fragile else 0,
                        -item.dimensions.volume(),
                        index,
                    ),
                )
            )
            index += 1

    fragile_names = {
        item.name
        for item in furniture_items
        if item.fragile and not rides_loose(item, box_sizes)
    }
    for requirement in box_requirements:
        contents = "、".join(requirement.suggested_contents)
        fragile = any(name in contents for name in fragile_names)
        for copy in range(requirement.count):
            label = f"{SIZE_TEXT[requirement.size]}纸箱"
            if requirement.count > 1:
                label = f"{label} {copy + 1}/{requirement.count}"
            if contents:
                label = f"{label}（{contents}）"
            spec = requirement.dimensions
            pieces.append(
                _Piece(
                    name=label,
                    kind="box",
                    length=spec.length,
                    width=spec.width,
                    height=spec.height,
                    fragile=fragile,
                    prefer="flat",
                    furniture_type=None,
                    sort_key=(
                        2,
                        1 if fragile else 0,
                        -requirement.weight_capacity,
                        -spec.volume(),
                        index,
                    ),
                )
            )
            index += 1
    pieces.sort(key=lambda item: item.sort_key)
    return pieces


def _prefer(furniture_type: FurnitureType) -> str:
    if furniture_type in UPRIGHT_TYPES:
        return "upright"
    if furniture_type in FLAT_TYPES:
        return "flat"
    return "any"


def _pack(pieces: list[_Piece], truck: TruckSpec) -> tuple[list[_Placed], list[_Piece]]:
    pending = list(pieces)
    placed: list[_Placed] = []
    trip = 1
    while pending:
        fitted, pending = _pack_trip(pending, truck, trip)
        if not fitted:
            return placed, pending
        placed.extend(fitted)
        trip += 1
    return placed, []


def _pack_trip(
    pieces: list[_Piece], truck: TruckSpec, trip: int
) -> tuple[list[_Placed], list[_Piece]]:
    placed: list[_Placed] = []
    points = [(0.0, 0.0, 0.0)]
    pending = list(pieces)
    while pending:
        blocked: list[_Piece] = []
        moved = False
        for piece in pending:
            choice = _best_pose(piece, placed, points, truck)
            if choice is None:
                blocked.append(piece)
                continue
            x, y, z, width, height, depth = choice
            placed.append(
                _Placed(piece, x, y, z, width, height, depth, trip)
            )
            _add_points(points, x, y, z, width, height, depth, truck, placed)
            moved = True
        if not moved:
            return placed, blocked
        pending = blocked
    return placed, []


def _best_pose(piece, placed, points, truck):
    best = None
    for penalty, depth, across, vertical in _orientations(piece):
        for x, y, z in points:
            if not _fits(x, y, z, across, vertical, depth, placed, truck):
                continue
            if piece.fragile:
                score = (-y, z, x, penalty, depth)
            else:
                score = (y, z, x, penalty, depth)
            if best is None or score < best[0]:
                best = (score, x, y, z, across, vertical, depth)
    if best is None:
        return None
    _, x, y, z, across, vertical, depth = best
    return x, y, z, across, vertical, depth


def _orientations(piece: _Piece):
    dims = (piece.length, piece.width, piece.height)
    shortest = min(dims)
    seen = set()
    options = []
    for depth, across, vertical in permutations(dims):
        if (depth, across, vertical) in seen:
            continue
        seen.add((depth, across, vertical))
        if piece.prefer == "upright":
            penalty = 0 if vertical == piece.height else 1
        elif piece.prefer == "flat":
            penalty = 0 if vertical == shortest else 1
        else:
            penalty = 0
        options.append((penalty, depth, across, vertical))
    return options


def _fits(x, y, z, width, height, depth, placed, truck) -> bool:
    if x < -1e-6 or y < -1e-6 or z < -1e-6:
        return False
    if x + width > truck.width_cm + 1e-6:
        return False
    if y + height > truck.height_cm + 1e-6:
        return False
    if z + depth > truck.length_cm + 1e-6:
        return False
    for item in placed:
        if not _separated(x, y, z, width, height, depth, item):
            return False
    return _supported(x, y, z, width, depth, placed)


def _separated(x, y, z, width, height, depth, item: _Placed) -> bool:
    return (
        x + width <= item.x + 1e-6
        or item.x + item.width <= x + 1e-6
        or y + height <= item.y + 1e-6
        or item.y + item.height <= y + 1e-6
        or z + depth <= item.z + 1e-6
        or item.z + item.depth <= z + 1e-6
    )


def _supported(x, y, z, width, depth, placed) -> bool:
    if y <= 1e-6:
        return True
    needed = width * depth * 0.5
    covered = 0.0
    for item in placed:
        if abs((item.y + item.height) - y) > 0.05:
            continue
        overlap_x = _overlap(x, x + width, item.x, item.x + item.width)
        overlap_z = _overlap(z, z + depth, item.z, item.z + item.depth)
        if overlap_x > 0 and overlap_z > 0:
            covered += overlap_x * overlap_z
    return covered + 1e-6 >= needed


def _overlap(start_a, end_a, start_b, end_b) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _add_points(points, x, y, z, width, height, depth, truck, placed) -> None:
    for point in ((x + width, y, z), (x, y + height, z), (x, y, z + depth)):
        px, py, pz = point
        if px >= truck.width_cm - 0.01 or py >= truck.height_cm - 0.01:
            continue
        if pz >= truck.length_cm - 0.01:
            continue
        key = (round(px, 2), round(py, 2), round(pz, 2))
        if key in {(round(a, 2), round(b, 2), round(c, 2)) for a, b, c in points}:
            continue
        if _point_inside(px, py, pz, placed):
            continue
        points.append((px, py, pz))


def _point_inside(x, y, z, placed) -> bool:
    for item in placed:
        if (
            item.x + 0.01 < x < item.x + item.width - 0.01
            and item.y + 0.01 < y < item.y + item.height - 0.01
            and item.z + 0.01 < z < item.z + item.depth - 0.01
        ):
            return True
    return False


def _placement(item: _Placed, truck: TruckSpec) -> CargoPlacement:
    side = _band(
        item.x + item.width / 2,
        truck.width_cm,
        PlacementSide.LEFT,
        PlacementSide.CENTER,
        PlacementSide.RIGHT,
    )
    level = _level(item.y, truck.height_cm)
    note = (
        f"第{item.trip}趟：放在车厢{SIDE_TEXT[side]}{LEVEL_TEXT[level]}，"
        f"距后部 {item.z:.0f} cm，距左壁 {item.x:.0f} cm，距地板 {item.y:.0f} cm"
    )
    if item.piece.fragile:
        note += "；易碎，不要在上面压重物"
    if item.piece.kind == "box":
        note += "；这是纸箱"
    return CargoPlacement(
        name=item.piece.name,
        kind=item.piece.kind,
        furniture_type=item.piece.furniture_type,
        trip=item.trip,
        x_cm=round(item.x, 2),
        y_cm=round(item.y, 2),
        z_cm=round(item.z, 2),
        width_cm=round(item.width, 2),
        height_cm=round(item.height, 2),
        depth_cm=round(item.depth, 2),
        side=side,
        level=level,
        fragile=item.piece.fragile,
        note=note,
    )


def _level(bottom, height):
    if bottom <= 0.5:
        return PlacementLevel.BOTTOM
    if bottom > height / 2:
        return PlacementLevel.TOP
    return PlacementLevel.MIDDLE


def _band(center, size, low, middle, high):
    if center < size / 3:
        return low
    if center > size * 2 / 3:
        return high
    return middle
