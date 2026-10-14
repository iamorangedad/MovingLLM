from src.agent import MovingLLMAgent
from src.models import Dimensions, FurnitureItem, FurnitureType, PlacementLevel, PlacementSide


def _item(name, furniture_type, length, width, height, **kwargs):
    return FurnitureItem(
        name=name,
        furniture_type=furniture_type,
        dimensions=Dimensions(length=length, width=width, height=height),
        **kwargs,
    )


def _plan(items):
    return MovingLLMAgent().plan_from_items(items)


def _by_name(plan, name):
    matches = [item for item in plan.cargo_layout.placements if item.name == name]
    assert len(matches) == 1
    return matches[0]


def _assert_inside_and_disjoint(layout):
    for item in layout.placements:
        assert item.x_cm >= -0.1
        assert item.y_cm >= -0.1
        assert item.z_cm >= -0.1
        assert item.x_cm + item.width_cm <= layout.width_cm + 0.1
        assert item.y_cm + item.height_cm <= layout.height_cm + 0.1
        assert item.z_cm + item.depth_cm <= layout.length_cm + 0.1
    placed = layout.placements
    for index, left in enumerate(placed):
        for right in placed[index + 1 :]:
            if left.trip != right.trip:
                continue
            separated = (
                left.x_cm + left.width_cm <= right.x_cm + 0.1
                or right.x_cm + right.width_cm <= left.x_cm + 0.1
                or left.y_cm + left.height_cm <= right.y_cm + 0.1
                or right.y_cm + right.height_cm <= left.y_cm + 0.1
                or left.z_cm + left.depth_cm <= right.z_cm + 0.1
                or right.z_cm + right.depth_cm <= left.z_cm + 0.1
            )
            assert separated, (left.name, right.name)


def test_side_by_side_items_are_left_and_right_on_the_floor():
    plan = _plan(
        [
            _item("茶几甲", FurnitureType.TABLE, 80, 80, 40, weight=10),
            _item("茶几乙", FurnitureType.TABLE, 80, 80, 40, weight=10),
        ]
    )
    layout = plan.cargo_layout
    left = _by_name(plan, "茶几甲")
    right = _by_name(plan, "茶几乙")

    assert layout.truck_name == "小型厢式车"
    assert left.y_cm == 0
    assert right.y_cm == 0
    assert left.z_cm == 0
    assert right.z_cm == 0
    assert left.side == PlacementSide.LEFT
    assert right.side == PlacementSide.RIGHT
    assert left.level == PlacementLevel.BOTTOM
    assert "左侧" in left.note and "底层" in left.note
    assert "右侧" in right.note
    _assert_inside_and_disjoint(layout)


def test_fragile_item_sits_above_the_floor_load():
    plan = _plan(
        [
            _item("茶几甲", FurnitureType.TABLE, 80, 80, 40, weight=10),
            _item("茶几乙", FurnitureType.TABLE, 80, 80, 40, weight=10),
            _item("花瓶", FurnitureType.OTHER, 40, 40, 40, weight=50, fragile=True),
        ]
    )
    vase = _by_name(plan, "花瓶")
    table = _by_name(plan, "茶几甲")

    assert vase.fragile is True
    assert vase.y_cm >= table.y_cm + table.height_cm - 0.1
    assert vase.level != PlacementLevel.BOTTOM
    assert "易碎" in vase.note
    _assert_inside_and_disjoint(plan.cargo_layout)


def test_wardrobe_is_at_the_back_and_boxes_are_not_drawn_as_furniture():
    plan = _plan(
        [
            _item("抽屉", FurnitureType.DRAWER, 20, 20, 20, weight=2),
            _item("衣柜", FurnitureType.WARDROBE, 180, 60, 200, weight=40),
        ]
    )
    wardrobe = _by_name(plan, "衣柜")
    boxes = [item for item in plan.cargo_layout.placements if item.kind == "box"]

    assert wardrobe.kind == "loose"
    assert wardrobe.y_cm == 0
    assert wardrobe.z_cm == 0
    assert wardrobe.height_cm == 200
    assert wardrobe.level == PlacementLevel.BOTTOM
    assert boxes
    assert all("纸箱" in item.name and "抽屉" in item.name for item in boxes)
    assert all(item.kind != "loose" or item.name != "抽屉" for item in plan.cargo_layout.placements)
    _assert_inside_and_disjoint(plan.cargo_layout)


def test_disassembled_sofa_is_only_boxes():
    plan = _plan(
        [_item("沙发", FurnitureType.SOFA, 200, 90, 85, weight=35, disassemble=True)]
    )
    assert plan.cargo_layout.placements
    assert {item.kind for item in plan.cargo_layout.placements} == {"box"}
    assert plan.cargo_layout.unplaced == []
    _assert_inside_and_disjoint(plan.cargo_layout)


def test_item_larger_than_the_cargo_is_unplaced():
    plan = _plan([_item("大板", FurnitureType.TABLE, 300, 250, 250, weight=80)])
    assert plan.cargo_layout.placements == []
    assert plan.cargo_layout.unplaced == ["大板"]
    assert any("无法摆入" in tip for tip in plan.tips)


def test_geometry_opens_another_trip_when_one_cargo_cannot_hold_the_shapes():
    plan = _plan(
        [
            _item("板甲", FurnitureType.TABLE, 200, 100, 100, weight=30),
            _item("板乙", FurnitureType.TABLE, 200, 100, 100, weight=30),
            _item("板丙", FurnitureType.TABLE, 200, 100, 100, weight=30),
        ]
    )
    trips = {item.trip for item in plan.cargo_layout.placements}
    assert plan.cargo_layout.unplaced == []
    assert len(plan.cargo_layout.placements) == 3
    assert len(trips) > 1
    assert plan.cargo_layout.trips == max(trips)
    _assert_inside_and_disjoint(plan.cargo_layout)
