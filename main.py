#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent import MovingLLMAgent


def print_plan(plan):
    print("\n" + "=" * 60)
    print("搬家计划报告")
    print("=" * 60 + "\n")

    print("家具清单:")
    for i, item in enumerate(plan.furniture_items, 1):
        print(f"{i}. {item.name} ({item.furniture_type.name})")
        print(
            f"   尺寸: {item.dimensions.length}x{item.dimensions.width}x{item.dimensions.height} cm"
        )
        if item.weight:
            print(f"   重量: {item.weight} kg")
        if item.disassemble:
            print(f"   可拆卸: 是")
        if item.fragile:
            print(f"   易碎: 是")
        if item.quantity > 1:
            print(f"   数量: {item.quantity}")
        print()

    print("-" * 60)
    print("空间估算:")
    print(f"总体积: {plan.space_estimation.total_volume:,.0f} cm³")
    print(f"预计装载体积: {plan.space_estimation.packed_volume:,.0f} cm³")
    print(f"建议车辆: {plan.space_estimation.truck_size_required}")
    print(f"装载效率: {plan.space_estimation.packing_efficiency}%")
    print()

    print("-" * 60)
    print("纸箱需求:")
    for req in plan.box_requirements:
        print(f"{req.size.upper()}: {req.count}个")
        print(
            f"  尺寸: {req.dimensions.length}x{req.dimensions.width}x{req.dimensions.height} cm"
        )
        print(f"  承重: {req.weight_capacity} kg")
    print()

    if plan.total_cost_estimate:
        print("-" * 60)
        print(f"预计费用: ¥{plan.total_cost_estimate:,.2f}")
        print(f"预计时间: {plan.estimated_time}")
        print()

    print("-" * 60)
    print("建议:")
    for tip in plan.tips:
        print(f"• {tip}")
    print()

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="LLM家具搬家空间估算助手")
    parser.add_argument("images", nargs="+", help="家具图片路径（可多个）")
    parser.add_argument("--recommend", action="store_true", help="获取AI详细建议")

    args = parser.parse_args()

    for image_path in args.images:
        if not Path(image_path).exists():
            print(f"错误: 图片不存在 - {image_path}")
            return

    print("正在分析家具图片...")
    agent = MovingLLMAgent()

    try:
        plan = agent.analyze_moving_plan(args.images)
        print_plan(plan)

        if args.recommend:
            print("正在获取AI详细建议...")
            recommendations = agent.get_recommendations(plan)
            print("\n" + "=" * 60)
            print("AI详细建议")
            print("=" * 60 + "\n")
            print(recommendations)
            print()

    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
