import pytest
from src.models import FurnitureItem, Dimensions, FurnitureType, BoxSize
from src.space_estimator import SpaceEstimator
from src.box_calculator import BoxCalculator


def test_furniture_item_creation():
    dimensions = Dimensions(100, 50, 75)
    item = FurnitureItem(
        name="测试沙发",
        furniture_type=FurnitureType.SOFA,
        dimensions=dimensions,
        weight=30,
        disassemble=False,
        fragile=False,
        quantity=1,
    )

    assert item.name == "测试沙发"
    assert item.dimensions.volume() == 100 * 50 * 75
    assert item.furniture_type == FurnitureType.SOFA


def test_dimensions_volume():
    dims = Dimensions(50, 50, 50)
    assert dims.volume() == 125000


def test_space_estimator():
    estimator = SpaceEstimator()

    items = [
        FurnitureItem(
            name="沙发",
            furniture_type=FurnitureType.SOFA,
            dimensions=Dimensions(200, 90, 85),
            weight=35,
            disassemble=False,
        ),
        FurnitureItem(
            name="书桌",
            furniture_type=FurnitureType.DESK,
            dimensions=Dimensions(120, 60, 75),
            weight=25,
            disassemble=True,
        ),
    ]

    estimation = estimator.estimate_space(items)

    assert estimation.total_volume > 0
    assert estimation.packed_volume > 0
    assert estimation.truck_size_required
    assert len(estimation.layout_suggestions) > 0
    assert estimation.packing_efficiency > 0


def test_box_calculator():
    calculator = BoxCalculator()

    items = [
        FurnitureItem(
            name="椅子",
            furniture_type=FurnitureType.CHAIR,
            dimensions=Dimensions(60, 60, 100),
            weight=15,
            disassemble=True,
            quantity=4,
        ),
        FurnitureItem(
            name="小桌子",
            furniture_type=FurnitureType.TABLE,
            dimensions=Dimensions(80, 80, 75),
            weight=20,
            disassemble=False,
            quantity=1,
        ),
    ]

    requirements = calculator.calculate_box_requirements(items)

    assert len(requirements) > 0
    total_boxes = sum(req.count for req in requirements)
    assert total_boxes >= 0

    tips = calculator.generate_packing_tips(items)
    assert len(tips) > 0


def test_box_sizes():
    calculator = BoxCalculator()

    assert BoxSize.SMALL in calculator.box_sizes
    assert BoxSize.MEDIUM in calculator.box_sizes
    assert BoxSize.LARGE in calculator.box_sizes
    assert BoxSize.XLARGE in calculator.box_sizes

    small_box = calculator.box_sizes[BoxSize.SMALL]
    assert small_box["weight_capacity"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
