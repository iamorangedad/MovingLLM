#!/usr/bin/env python3
"""
示例：如何使用MovingLLM Agent
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import MovingLLMAgent


def example_usage():
    """
    基本使用示例
    """
    print("MovingLLM Agent 使用示例\n")

    agent = MovingLLMAgent()

    print("示例 1: 分析单个家具图片")
    print("-" * 50)

    image_path = "examples/sample_furniture.jpg"

    try:
        plan = agent.analyze_moving_plan([image_path])

        print(f"识别到的家具数量: {len(plan.furniture_items)}")
        print(f"所需纸箱总数: {sum(req.count for req in plan.box_requirements)}")
        print(f"建议车辆: {plan.space_estimation.truck_name}")
        print(f"尺寸已确认: {plan.dimensions_confirmed}")
        print(f"预计费用: ¥{plan.total_cost_estimate}")

        print(
            "\n详细报告请使用: python main.py examples/sample_furniture.jpg --recommend"
        )

    except Exception as e:
        print(f"执行错误: {e}")
        print("\n提示:")
        print("1. 确保 .env 文件中配置了 OPENAI_API_KEY")
        print("2. 确保图片文件存在")
        print("3. 安装所有依赖: pip install -r requirements.txt")


def example_api():
    """
    API使用示例
    """
    print("\n示例 2: 使用FastAPI服务器")
    print("-" * 50)

    print("启动API服务器:")
    print("  python api_server.py")
    print("\n访问API文档:")
    print("  http://localhost:8000/docs")
    print("\n分析端点:")
    print("  POST http://localhost:8000/analyze")
    print("  Content-Type: multipart/form-data")
    print("  files: 图片文件")
    print("\n建议端点:")
    print("  POST http://localhost:8000/recommend")
    print("  Content-Type: multipart/form-data")
    print("  files: 图片文件")


def example_batch():
    """
    批量处理示例
    """
    print("\n示例 3: 批量处理多张图片")
    print("-" * 50)

    print("命令行用法:")
    print("  python main.py image1.jpg image2.jpg image3.jpg")
    print("\n带AI建议:")
    print("  python main.py *.jpg --recommend")


if __name__ == "__main__":
    example_usage()
    example_api()
    example_batch()

    print("\n" + "=" * 50)
    print("更多帮助:")
    print("  python main.py --help")
    print("=" * 50)
