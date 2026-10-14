#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pydantic import ValidationError

from src.agent import MovingLLMAgent
from src.config import default_context
from src.errors import ConfigurationError, VisionParseError
from src.models import MoveContext


def context_from_args(args) -> MoveContext:
    data = default_context().model_dump()
    if args.distance_km is not None:
        data["distance_km"] = args.distance_km
    if args.origin_floor is not None:
        data["origin_floor"] = args.origin_floor
    if args.destination_floor is not None:
        data["destination_floor"] = args.destination_floor
    if args.no_origin_elevator:
        data["origin_has_elevator"] = False
    if args.no_destination_elevator:
        data["destination_has_elevator"] = False
    return MoveContext.model_validate(data)


def print_plan(plan):
    print("\n" + "=" * 60)
    print("搬家计划报告")
    print("=" * 60 + "\n")
    if not plan.dimensions_confirmed:
        print("尺寸和重量尚未确认，下面的车辆、纸箱和费用都是估算。\n")

    print("家具清单:")
    for index, item in enumerate(plan.furniture_items, 1):
        state = "已确认" if item.dimensions_confirmed else "待确认"
        print(f"{index}. {item.name} ({item.furniture_type.value}) [{state}]")
        print(
            f"   尺寸: {item.dimensions.length}x{item.dimensions.width}x{item.dimensions.height} cm"
        )
        if item.weight:
            print(f"   重量: {item.weight} kg")
        print(f"   可拆卸: {'是' if item.disassemble else '否'}")
        if item.fragile:
            print("   易碎: 是")
        print(f"   数量: {item.quantity}")
        print()

    space = plan.space_estimation
    print("-" * 60)
    print("空间估算:")
    print(f"家具体积: {space.total_volume_cm3:,.0f} cm³")
    print(f"散装体积: {space.loose_volume_cm3:,.0f} cm³")
    print(f"纸箱外体积: {space.box_volume_cm3:,.0f} cm³")
    print(f"有效装载体积: {space.effective_volume_cm3:,.0f} cm³")
    print(f"建议车辆: {space.truck_name}（{space.truck_capacity_m3:g} m³）")
    print(f"趟数: {space.trips}")
    print(f"装载效率: {space.packing_efficiency}%")
    print()

    print("-" * 60)
    print("装载顺序:")
    for index, label in enumerate(plan.loading_order, 1):
        print(f"{index}. {label}")
    print()

    layout = plan.cargo_layout
    print("-" * 60)
    print(
        f"三维装车: {layout.truck_name} "
        f"（内尺寸 {layout.length_cm:g}×{layout.width_cm:g}×{layout.height_cm:g} cm）"
    )
    print(layout.axis_note)
    if not layout.placements:
        print("没有放入车厢的物品")
    for index, item in enumerate(layout.placements, 1):
        print(
            f"{index}. 第{item.trip}趟 {item.name} "
            f"{item.width_cm:g}×{item.height_cm:g}×{item.depth_cm:g} cm"
        )
        print(f"   {item.note}")
    if layout.unplaced:
        print("无法摆入: " + "、".join(layout.unplaced))
    print()

    print("-" * 60)
    print("纸箱需求:")
    if not plan.box_requirements:
        print("无（大型家具按散装占用车厢）")
    for requirement in plan.box_requirements:
        print(f"{requirement.size.value}: {requirement.count}个")
        dims = requirement.dimensions
        print(f"  尺寸: {dims.length}x{dims.width}x{dims.height} cm")
        print(f"  承重: {requirement.weight_capacity} kg")
        if requirement.suggested_contents:
            print(f"  内容: {', '.join(requirement.suggested_contents)}")
    print()

    print("-" * 60)
    cost = plan.cost_breakdown
    print(f"运输: ¥{cost.transport:,.2f}")
    print(f"纸箱: ¥{cost.boxes:,.2f}")
    print(f"人工: ¥{cost.labor:,.2f}")
    print(f"预计费用: ¥{plan.total_cost_estimate:,.2f}")
    print(f"预计时间: {plan.estimated_time}")
    print(
        f"行程: {plan.context.distance_km:g} km，楼梯 {plan.context.stair_floors()} 层"
    )
    print()

    print("-" * 60)
    print("建议:")
    for tip in plan.tips:
        print(f"• {tip}")
    print()
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="家具搬家空间估算")
    parser.add_argument("images", nargs="+", help="家具图片路径")
    parser.add_argument("--recommend", action="store_true", help="调用模型生成文字建议")
    parser.add_argument("--distance-km", type=float, help="搬运距离（公里）")
    parser.add_argument("--origin-floor", type=int, help="起点楼层")
    parser.add_argument("--destination-floor", type=int, help="终点楼层")
    parser.add_argument("--no-origin-elevator", action="store_true", help="起点无电梯")
    parser.add_argument(
        "--no-destination-elevator", action="store_true", help="终点无电梯"
    )
    args = parser.parse_args()

    for image_path in args.images:
        if not Path(image_path).is_file():
            print(f"错误: 图片不存在 - {image_path}")
            return 1

    try:
        context = context_from_args(args)
    except ValidationError as exc:
        print(f"错误: 行程参数不正确 - {exc.errors()[0]['msg']}")
        return 1

    print("正在分析家具图片...")
    agent = MovingLLMAgent()
    try:
        plan = agent.analyze_moving_plan(args.images, context)
        print_plan(plan)
        if args.recommend:
            print("正在获取文字建议...")
            print(agent.get_recommendations(plan))
            print()
    except (ConfigurationError, VisionParseError) as exc:
        print(f"错误: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
