from pathlib import Path

from src.agent import MovingLLMAgent
from src.box_calculator import BoxCalculator
from src.config import get_settings
from src.models import Dimensions, FurnitureItem, FurnitureType, MoveContext


def _item(
    name,
    furniture_type,
    length,
    width,
    height,
    *,
    weight=None,
    disassemble=False,
    quantity=1,
    fragile=False,
):
    return FurnitureItem(
        name=name,
        furniture_type=furniture_type,
        dimensions=Dimensions(length=length, width=width, height=height),
        weight=weight,
        disassemble=disassemble,
        fragile=fragile,
        quantity=quantity,
    )


def _plan(items, context=None):
    return MovingLLMAgent().plan_from_items(items, context)


def test_loose_item_is_counted_once():
    chair = _item("椅子", FurnitureType.CHAIR, 60, 60, 100, weight=8)
    plan = _plan([chair])
    space = plan.space_estimation
    expected = chair.dimensions.volume() * get_settings().packing.loose_padding_factor

    assert plan.box_requirements == []
    assert space.box_volume_cm3 == 0
    assert space.loose_volume_cm3 == expected
    assert space.effective_volume_cm3 == expected
    assert space.total_volume_cm3 == chair.dimensions.volume()


def test_boxed_item_occupies_box_volume_only():
    drawer = _item("抽屉", FurnitureType.DRAWER, 20, 20, 20, weight=1, quantity=10)
    plan = _plan([drawer])
    space = plan.space_estimation
    stacking = get_settings().packing.stacking_factor

    assert space.loose_volume_cm3 == 0
    assert len(plan.box_requirements) == 1
    assert plan.box_requirements[0].count == 5
    assert space.effective_volume_cm3 == space.box_volume_cm3 * stacking


def test_disassembled_furniture_is_not_also_loose():
    plan = _plan(
        [_item("沙发", FurnitureType.SOFA, 200, 90, 85, weight=35, disassemble=True)]
    )
    assert plan.space_estimation.loose_volume_cm3 == 0
    assert plan.box_requirements[0].count > 0


def test_efficiency_uses_selected_truck_capacity():
    small = _plan([_item("抽屉", FurnitureType.DRAWER, 20, 20, 20, weight=1)])
    large = _plan([_item("沙发", FurnitureType.SOFA, 200, 90, 85, weight=35)])

    for plan in (small, large):
        space = plan.space_estimation
        expected = round(
            space.effective_volume_cm3
            / 1_000_000
            / (space.trips * space.truck_capacity_m3)
            * 100,
            2,
        )
        assert space.packing_efficiency == expected
    assert small.space_estimation.packing_efficiency != (
        large.space_estimation.packing_efficiency
    )


def test_disassembled_quantity_and_weight_increase_boxes():
    calculator = BoxCalculator()

    def desk(quantity, weight, length=20):
        return _item(
            "书桌",
            FurnitureType.DESK,
            length,
            60,
            50,
            weight=weight,
            disassemble=True,
            quantity=quantity,
        )

    one = calculator.calculate_box_requirements([desk(1, 5, 120)])[0].count
    two = calculator.calculate_box_requirements([desk(2, 5, 120)])[0].count
    light = calculator.calculate_box_requirements([desk(1, 5, 20)])[0].count
    heavy = calculator.calculate_box_requirements([desk(1, 100, 20)])[0].count

    assert two > one
    assert heavy > light


def test_loading_order_puts_intact_wardrobe_first():
    plan = _plan(
        [
            _item("抽屉", FurnitureType.DRAWER, 20, 20, 20, weight=2),
            _item("衣柜", FurnitureType.WARDROBE, 180, 60, 200, weight=40),
        ]
    )
    assert plan.loading_order[0].startswith("衣柜")
    assert plan.loading_order[1].startswith("抽屉")


def test_distance_and_stairs_change_cost():
    sofa = [_item("沙发", FurnitureType.SOFA, 200, 90, 85, weight=35)]
    near = _plan(sofa, MoveContext(distance_km=1))
    far = _plan(sofa, MoveContext(distance_km=50))
    stairs = _plan(
        sofa, MoveContext(origin_floor=4, origin_has_elevator=False, distance_km=1)
    )

    assert far.cost_breakdown.transport > near.cost_breakdown.transport
    assert stairs.cost_breakdown.labor > near.cost_breakdown.labor
    assert stairs.context.stair_floors() == 3


def test_box_price_comes_from_config():
    plan = _plan([_item("抽屉", FurnitureType.DRAWER, 20, 20, 20, weight=1)])
    price = get_settings().box_sizes[plan.box_requirements[0].size].price
    assert plan.cost_breakdown.boxes == price * plan.box_requirements[0].count


def test_config_file_has_no_secret_and_deps_stay_light():
    config = Path("config/config.yaml").read_text(encoding="utf-8")
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    assert "OPENAI_API_KEY" not in config
    assert "api_key" not in config
    for package in ("torch", "opencv", "transformers"):
        assert package not in requirements


def test_item_that_fits_no_door_is_reported():
    plan = _plan([_item("大板", FurnitureType.TABLE, 300, 250, 250, weight=80)])
    assert plan.space_estimation.items_exceed_all_doors == ["大板"]
    assert any("车厢门" in tip for tip in plan.tips)
