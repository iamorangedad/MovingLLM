import pytest

from src.agent import MovingLLMAgent
from src.errors import LayoutEditError
from src.models import (
    CargoSpace,
    Dimensions,
    FloorPlan,
    FurnitureItem,
    FurnitureType,
    PoseMove,
    RoomRect,
)


def _item(name, furniture_type, length, width, height, **kwargs):
    return FurnitureItem(
        name=name,
        furniture_type=furniture_type,
        dimensions=Dimensions(length=length, width=width, height=height),
        **kwargs,
    )


def _cube(name, size=40):
    return _item(name, FurnitureType.OTHER, size, size, size, weight=50)


def test_custom_cargo_rejects_sizes_outside_config():
    with pytest.raises(LayoutEditError):
        MovingLLMAgent().arrange_cargo([], CargoSpace(length_cm=10, width_cm=100, height_cm=100))


def test_drag_stacks_onto_the_item_below():
    agent = MovingLLMAgent()
    space = CargoSpace(length_cm=200, width_cm=200, height_cm=200)
    layout = agent.arrange_cargo([_cube("甲"), _cube("乙")], space)
    lower = next(item for item in layout.placements if item.name == "甲")
    upper = next(item for item in layout.placements if item.name == "乙")

    moved = agent.move_cargo(
        layout, PoseMove(id=upper.id, x_cm=lower.x_cm, z_cm=lower.z_cm, yaw_quarters=0)
    )
    stacked = next(item for item in moved.placements if item.id == upper.id)
    assert stacked.y_cm == pytest.approx(lower.height_cm)
    assert stacked.level.value != "bottom"


def test_stack_is_rejected_when_it_exceeds_the_roof():
    agent = MovingLLMAgent()
    space = CargoSpace(length_cm=200, width_cm=200, height_cm=100)
    layout = agent.arrange_cargo([_cube("甲", 60), _cube("乙", 60)], space)
    lower = next(item for item in layout.placements if item.name == "甲")
    upper = next(item for item in layout.placements if item.name == "乙")
    with pytest.raises(LayoutEditError):
        agent.move_cargo(
            layout, PoseMove(id=upper.id, x_cm=lower.x_cm, z_cm=lower.z_cm)
        )


def test_cargo_move_outside_the_space_is_rejected():
    agent = MovingLLMAgent()
    layout = agent.arrange_cargo(
        [_cube("甲")], CargoSpace(length_cm=120, width_cm=120, height_cm=120)
    )
    with pytest.raises(LayoutEditError):
        agent.move_cargo(layout, PoseMove(id=layout.placements[0].id, x_cm=-5, z_cm=0))


def test_overlapping_rooms_and_furniture_in_the_wall_are_rejected():
    agent = MovingLLMAgent()
    with pytest.raises(LayoutEditError):
        agent.build_home(
            [],
            FloorPlan(
                rooms=[
                    RoomRect(name="甲", x_cm=0, z_cm=0, width_cm=300, depth_cm=300),
                    RoomRect(name="乙", x_cm=100, z_cm=100, width_cm=300, depth_cm=300),
                ]
            ),
        )

    home = agent.build_home(
        [_item("沙发", FurnitureType.SOFA, 180, 80, 70, weight=30)],
        FloorPlan(rooms=[RoomRect(name="客厅", x_cm=0, z_cm=0, width_cm=500, depth_cm=400)]),
    )
    sofa = home.placements[0]
    assert sofa.y_cm == 0
    assert sofa.room_name == "客厅"
    south = [solid for solid in home.shell.solids if solid.name.startswith("客厅南墙")]
    assert len(south) == 2
    with pytest.raises(LayoutEditError):
        agent.move_home(home, PoseMove(id=sofa.id, x_cm=0, z_cm=sofa.z_cm))


def test_home_move_rejects_overlapping_furniture():
    agent = MovingLLMAgent()
    home = agent.build_home(
        [
            _item("沙发", FurnitureType.SOFA, 180, 80, 70, weight=30),
            _item("床", FurnitureType.BED, 200, 140, 40, weight=40),
        ],
        FloorPlan(rooms=[RoomRect(name="客厅", x_cm=0, z_cm=0, width_cm=600, depth_cm=500)]),
    )
    bed = next(item for item in home.placements if item.name == "床")
    sofa = next(item for item in home.placements if item.name == "沙发")
    with pytest.raises(LayoutEditError):
        agent.move_home(home, PoseMove(id=bed.id, x_cm=sofa.x_cm, z_cm=sofa.z_cm))
