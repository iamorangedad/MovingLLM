from src.errors import LayoutEditError
from src.layout import FLAT_TYPES, UPRIGHT_TYPES
from src.models import (
    FloorPlan,
    FurnitureItem,
    HomeLayout,
    HomePlacement,
    HomeShell,
    PoseMove,
    RoomRect,
    ShellSolid,
)


def arrange_home(items: list[FurnitureItem], floor_plan: FloorPlan, settings) -> HomeLayout:
    shell = build_shell(floor_plan, settings)
    placed: list[HomePlacement] = []
    held: list[HomePlacement] = []
    unplaced: list[str] = []
    for index, item in enumerate(items):
        for copy in range(item.quantity):
            name = item.name if item.quantity == 1 else f"{item.name} {copy + 1}"
            width, height, depth = _oriented_size(item)
            slot = _find_floor_slot(width, depth, shell.interiors, placed)
            piece_id = f"home-{index}-{copy}"
            if slot is None:
                held.append(
                    _placement(
                        piece_id,
                        name,
                        item.furniture_type.value,
                        0,
                        0,
                        width,
                        height,
                        depth,
                        width,
                        depth,
                        0,
                        None,
                        "尚未放入房间",
                    )
                )
                unplaced.append(name)
                continue
            x, z, span_x, span_z, yaw, room_name = slot
            held_width, held_depth = (depth, width) if yaw % 2 else (width, depth)
            placed.append(
                _placement(
                    piece_id,
                    name,
                    item.furniture_type.value,
                    x,
                    z,
                    held_width,
                    height,
                    held_depth,
                    width,
                    depth,
                    yaw,
                    room_name,
                    _room_note(room_name, x, z),
                )
            )
    return HomeLayout(shell=shell, placements=placed, held=held, unplaced=unplaced)


def apply_home_move(layout: HomeLayout, move: PoseMove) -> HomeLayout:
    item, source = _take(layout, move.id)
    others = [piece for piece in layout.placements if piece.id != item.id]
    yaw = move.yaw_quarters % 4
    width, depth = (
        (item.rest_depth_cm, item.rest_width_cm)
        if yaw % 2
        else (item.rest_width_cm, item.rest_depth_cm)
    )
    room = _containing_room(move.x_cm, move.z_cm, width, depth, layout.shell.interiors)
    if room is None:
        raise LayoutEditError("家具超出房间内墙")
    if any(
        _footprint_hits(move.x_cm, move.z_cm, width, depth, other) for other in others
    ):
        raise LayoutEditError("和另一件家具重叠")
    updated = item.model_copy(
        update={
            "x_cm": round(move.x_cm, 2),
            "y_cm": 0,
            "z_cm": round(move.z_cm, 2),
            "width_cm": round(width, 2),
            "depth_cm": round(depth, 2),
            "yaw_quarters": yaw,
            "room_name": room.name,
            "note": _room_note(room.name, move.x_cm, move.z_cm),
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


def build_shell(floor_plan: FloorPlan, settings) -> HomeShell:
    if not floor_plan.rooms:
        raise LayoutEditError("至少画一间房间")
    home = settings.home
    height = floor_plan.wall_height_cm or home.wall_height_cm
    names = [room.name for room in floor_plan.rooms]
    if len(names) != len(set(names)):
        raise LayoutEditError("房间名称不能重复")
    for room in floor_plan.rooms:
        if not home.min_room_cm <= room.width_cm <= home.max_room_cm:
            raise LayoutEditError("房间尺寸超出范围")
        if not home.min_room_cm <= room.depth_cm <= home.max_room_cm:
            raise LayoutEditError("房间尺寸超出范围")
    for index, room in enumerate(floor_plan.rooms):
        for other in floor_plan.rooms[index + 1 :]:
            if _area_overlap(room, other):
                raise LayoutEditError("房间重叠")

    interiors = []
    solids = []
    thickness = home.wall_thickness_cm
    for room in floor_plan.rooms:
        interior = RoomRect(
            name=room.name,
            x_cm=room.x_cm + thickness,
            z_cm=room.z_cm + thickness,
            width_cm=room.width_cm - 2 * thickness,
            depth_cm=room.depth_cm - 2 * thickness,
        )
        if interior.width_cm <= 0 or interior.depth_cm <= 0:
            raise LayoutEditError("房间太小，墙放不下")
        interiors.append(interior)
        solids.extend(_room_solids(room, height, thickness, home.door_width_cm))
    return HomeShell(
        wall_height_cm=height,
        wall_thickness_cm=thickness,
        rooms=floor_plan.rooms,
        interiors=interiors,
        solids=solids,
    )


def _oriented_size(item: FurnitureItem) -> tuple[float, float, float]:
    length = item.dimensions.length
    width = item.dimensions.width
    height = item.dimensions.height
    if item.furniture_type in UPRIGHT_TYPES:
        return width, height, length
    if item.furniture_type in FLAT_TYPES:
        shortest = min(length, width, height)
        others = [length, width, height]
        others.remove(shortest)
        return others[0], shortest, others[1]
    return width, height, length


def _find_floor_slot(width, depth, rooms, placed):
    for room in rooms:
        points = [(room.x_cm, room.z_cm)]
        for item in placed:
            if item.room_name != room.name:
                continue
            points.append((item.x_cm + item.width_cm, item.z_cm))
            points.append((item.x_cm, item.z_cm + item.depth_cm))
        for yaw, span_x, span_z in ((0, width, depth), (1, depth, width)):
            for x, z in points:
                if _inside(x, z, span_x, span_z, room) and not any(
                    _footprint_hits(x, z, span_x, span_z, item) for item in placed
                ):
                    return x, z, span_x, span_z, yaw, room.name
    return None


def _room_solids(room: RoomRect, height: float, thickness: float, door_width: float):
    solids = [
        _solid(
            f"{room.name}地板",
            "floor",
            room.x_cm,
            -1,
            room.z_cm,
            room.width_cm,
            1,
            room.depth_cm,
        ),
        _solid(
            f"{room.name}西墙",
            "wall",
            room.x_cm,
            0,
            room.z_cm,
            thickness,
            height,
            room.depth_cm,
        ),
        _solid(
            f"{room.name}东墙",
            "wall",
            room.x_cm + room.width_cm - thickness,
            0,
            room.z_cm,
            thickness,
            height,
            room.depth_cm,
        ),
        _solid(
            f"{room.name}北墙",
            "wall",
            room.x_cm,
            0,
            room.z_cm + room.depth_cm - thickness,
            room.width_cm,
            height,
            thickness,
        ),
    ]
    opening = min(door_width, max(0, room.width_cm - 2 * thickness))
    if opening <= 0:
        solids.append(
            _solid(
                f"{room.name}南墙",
                "wall",
                room.x_cm,
                0,
                room.z_cm,
                room.width_cm,
                height,
                thickness,
            )
        )
        return solids
    gap = room.x_cm + (room.width_cm - opening) / 2
    if gap - room.x_cm > 0.5:
        solids.append(
            _solid(
                f"{room.name}南墙左",
                "wall",
                room.x_cm,
                0,
                room.z_cm,
                gap - room.x_cm,
                height,
                thickness,
            )
        )
    right_x = gap + opening
    right_width = room.x_cm + room.width_cm - right_x
    if right_width > 0.5:
        solids.append(
            _solid(
                f"{room.name}南墙右",
                "wall",
                right_x,
                0,
                room.z_cm,
                right_width,
                height,
                thickness,
            )
        )
    return solids


def _solid(name, kind, x, y, z, width, height, depth) -> ShellSolid:
    return ShellSolid(
        name=name,
        kind=kind,
        x_cm=round(x, 2),
        y_cm=round(y, 2),
        z_cm=round(z, 2),
        width_cm=round(width, 2),
        height_cm=round(height, 2),
        depth_cm=round(depth, 2),
    )


def _placement(
    piece_id, name, furniture_type, x, z, width, height, depth, rest_width, rest_depth, yaw, room, note
) -> HomePlacement:
    return HomePlacement(
        id=piece_id,
        name=name,
        furniture_type=furniture_type,
        x_cm=round(x, 2),
        y_cm=0,
        z_cm=round(z, 2),
        width_cm=round(width, 2),
        height_cm=round(height, 2),
        depth_cm=round(depth, 2),
        rest_width_cm=round(rest_width, 2),
        rest_depth_cm=round(rest_depth, 2),
        yaw_quarters=yaw,
        room_name=room,
        note=note,
    )


def _room_note(room_name, x, z) -> str:
    return f"放在{room_name}，距西墙 {x:.0f} cm，距南墙 {z:.0f} cm"


def _take(layout: HomeLayout, placement_id: str):
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


def _containing_room(x, z, width, depth, rooms: list[RoomRect]):
    for room in rooms:
        if _inside(x, z, width, depth, room):
            return room
    return None


def _inside(x, z, width, depth, room: RoomRect) -> bool:
    return (
        x >= room.x_cm - 1e-6
        and z >= room.z_cm - 1e-6
        and x + width <= room.x_cm + room.width_cm + 1e-6
        and z + depth <= room.z_cm + room.depth_cm + 1e-6
    )


def _footprint_hits(x, z, width, depth, other: HomePlacement) -> bool:
    return not (
        x + width <= other.x_cm + 1e-6
        or other.x_cm + other.width_cm <= x + 1e-6
        or z + depth <= other.z_cm + 1e-6
        or other.z_cm + other.depth_cm <= z + 1e-6
    )


def _area_overlap(left: RoomRect, right: RoomRect) -> bool:
    return not (
        left.x_cm + left.width_cm <= right.x_cm + 1e-6
        or right.x_cm + right.width_cm <= left.x_cm + 1e-6
        or left.z_cm + left.depth_cm <= right.z_cm + 1e-6
        or right.z_cm + right.depth_cm <= left.z_cm + 1e-6
    )
