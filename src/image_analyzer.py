import base64
from typing import List, Dict, Any, Optional
from PIL import Image
import io

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from openai import OpenAI
from src.config import settings
from src.models import FurnitureItem, Dimensions, FurnitureType


class ImageAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def encode_image(self, image_path: str) -> str:
        image = Image.open(image_path)

        if image.mode != "RGB":
            image = image.convert("RGB")

        max_size = 2048
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def analyze_furniture_from_image(self, image_path: str) -> List[FurnitureItem]:
        base64_image = self.encode_image(image_path)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个专业的家具分析专家。请分析图片中的家具，并提供详细信息。
对于每件家具，请提供：
1. 家具名称（中文）
2. 家具类型（sofa, chair, table, bed, wardrobe, desk, bookshelf, drawer, tv_stand, other）
3. 估算尺寸（长、宽、高，单位：cm）
4. 估算重量（kg）
5. 是否需要拆卸
6. 是否易碎
7. 数量
8. 简短描述

请以JSON格式返回，格式如下：
{
  "furniture": [
    {
      "name": "家具名称",
      "type": "类型",
      "dimensions": {"length": 数值, "width": 数值, "height": 数值},
      "weight": 数值,
      "disassemble": true/false,
      "fragile": true/false,
      "quantity": 数值,
      "description": "描述"
    }
  ]
}""",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请分析这张图片中的家具。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=2000,
            temperature=0.3,
        )

        content = response.choices[0].message.content
        if content:
            return self._parse_response(content)
        return []

    def _parse_response(self, response_text: str) -> List[FurnitureItem]:
        import json

        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                data = json.loads(json_text)

                furniture_items = []
                for item in data.get("furniture", []):
                    dimensions = Dimensions(
                        length=item["dimensions"]["length"],
                        width=item["dimensions"]["width"],
                        height=item["dimensions"]["height"],
                    )

                    try:
                        furniture_type = FurnitureType(item["type"].lower())
                    except ValueError:
                        furniture_type = FurnitureType.OTHER

                    furniture_item = FurnitureItem(
                        name=item["name"],
                        furniture_type=furniture_type,
                        dimensions=dimensions,
                        weight=item.get("weight"),
                        disassemble=item.get("disassemble", False),
                        fragile=item.get("fragile", False),
                        quantity=item.get("quantity", 1),
                        description=item.get("description"),
                    )

                    furniture_items.append(furniture_item)

                return furniture_items
        except Exception as e:
            print(f"解析响应时出错: {e}")
            print(f"原始响应: {response_text}")

        return []

    def enhance_with_cv(self, image_path: str) -> Dict[str, Any]:
        if not CV2_AVAILABLE:
            return {
                "contour_count": 0,
                "edge_density": 0,
                "image_dimensions": (0, 0),
                "note": "OpenCV not available",
            }

        import cv2
        import numpy as np

        image = cv2.imread(image_path)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray, 50, 150)

        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        large_contours = [c for c in contours if cv2.contourArea(c) > 1000]

        return {
            "contour_count": len(large_contours),
            "edge_density": np.sum(edges) / (edges.shape[0] * edges.shape[1]),
            "image_dimensions": image.shape[:2],
        }
