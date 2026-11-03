from src.errors import LayoutEditError
from src.layout import pose_note
from src.models import CargoLayout, CargoPlacement, PoseMove


def apply_cargo_move(layout: CargoLayout, move: PoseMove) -> CargoLayout:
    item, source = _take(layout, move.id)
    others = [piece for piece in layout.placements if piece.id != item.id]
    yaw = move.yaw_quarters % 4
    base_width = item.rest_width_cm or item.width_cm
    base_depth = item.rest_depth_cm or item.depth_cm
    width, depth = (base_depth, base_width) if yaw % 2 else (base_width, base_depth)
    landed = _lowest_y(move.x_cm, move.z_cm, width, item.height_cm, depth, others, layout)
    if landed is None:
        raise LayoutEditError("这个位置超出车厢，或没有足够的支撑")

    side, level, note = pose_note(
        item.trip,
        move.x_cm,
        landed,
        move.z_cm,
        width,
        layout.width_cm,
        layout.height_cm,
        item.fragile,
        item.kind,
    )
    updated = item.model_copy(
        update={
            "x_cm": round(move.x_cm, 2),
            "y_cm": round(landed, 2),
            "z_cm": round(move.z_cm, 2),
            "width_cm": round(width, 2),
            "depth_cm": round(depth, 2),
            "rest_width_cm": base_width,
            "rest_depth_cm": base_depth,
            "yaw_quarters": yaw,
            "side": side,
            "level": level,
            "note": note,
        }
    )
    if source == "held":
        placements = [*layout.placements, updated]
        held = [piece for piece in layout.held if piece.id != item.id]
        unplaced = _drop_name(layout.unplaced, item.name)
    else:
        placements = [
            updated if piece.id == item.id else piece for piece in layout.placements
        ]
        held = layout.held
        unplaced = layout.unplaced
    return layout.model_copy(
        update={"placements": placements, "held": held, "unplaced": unplaced}
    )


def _take(layout: CargoLayout, placement_id: str) -> tuple[CargoPlacement, str]:
    for item in layout.placements:
        if item.id == placement_id:
            return item, "placed"
    for item in layout.held:
        if item.id == placement_id:
            return item, "held"
    raise LayoutEditError("没有这件物品")


def _drop_name(names: list[str], name: str) -> list[str]:
    pending = list(names)
    if name in pending:
        pending.remove(name)
    return pending


def _lowest_y(x, z, width, height, depth, others, layout):
    if (
        x < -1e-6
        or z < -1e-6
        or x + width > layout.width_cm + 1e-6
        or z + depth > layout.length_cm + 1e-6
    ):
        return None
    candidates = [0.0]
    for other in others:
        if _xz_overlap(x, z, width, depth, other) > 0:
            candidates.append(other.y_cm + other.height_cm)
    for y in sorted({round(value, 4) for value in candidates}):
        if y < -1e-6 or y + height > layout.height_cm + 1e-6:
            continue
        if any(
            not _separated(x, y, z, width, height, depth, other) for other in others
        ):
            continue
        if _supported(x, y, z, width, depth, others):
            return y
    return None


def _xz_overlap(x, z, width, depth, other: CargoPlacement) -> float:
    overlap_x = _overlap(x, x + width, other.x_cm, other.x_cm + other.width_cm)
    overlap_z = _overlap(z, z + depth, other.z_cm, other.z_cm + other.depth_cm)
    if overlap_x <= 0 or overlap_z <= 0:
        return 0
    return overlap_x * overlap_z


def _separated(x, y, z, width, height, depth, other: CargoPlacement) -> bool:
    return (
        x + width <= other.x_cm + 1e-6
        or other.x_cm + other.width_cm <= x + 1e-6
        or y + height <= other.y_cm + 1e-6
        or other.y_cm + other.height_cm <= y + 1e-6
        or z + depth <= other.z_cm + 1e-6
        or other.z_cm + other.depth_cm <= z + 1e-6
    )


def _supported(x, y, z, width, depth, others) -> bool:
    if y <= 1e-6:
        return True
    covered = 0.0
    for other in others:
        if abs((other.y_cm + other.height_cm) - y) > 0.05:
            continue
        overlap_x = _overlap(x, x + width, other.x_cm, other.x_cm + other.width_cm)
        overlap_z = _overlap(z, z + depth, other.z_cm, other.z_cm + other.depth_cm)
        if overlap_x > 0 and overlap_z > 0:
            covered += overlap_x * overlap_z
    return covered + 1e-6 >= width * depth * 0.5


def _overlap(start_a, end_a, start_b, end_b) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
