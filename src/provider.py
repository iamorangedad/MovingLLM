import base64
import io
import json
import re
from typing import Protocol

from openai import BadRequestError, OpenAI
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from src.config import Settings, get_settings
from src.errors import ConfigurationError, VisionParseError
from src.models import Dimensions, FurnitureItem, FurnitureType, MovingPlan

TYPE_ALIASES = {
    "sofa": FurnitureType.SOFA,
    "沙发": FurnitureType.SOFA,
    "chair": FurnitureType.CHAIR,
    "椅子": FurnitureType.CHAIR,
    "table": FurnitureType.TABLE,
    "桌子": FurnitureType.TABLE,
    "bed": FurnitureType.BED,
    "床": FurnitureType.BED,
    "wardrobe": FurnitureType.WARDROBE,
    "衣柜": FurnitureType.WARDROBE,
    "desk": FurnitureType.DESK,
    "书桌": FurnitureType.DESK,
    "bookshelf": FurnitureType.BOOKSHELF,
    "书架": FurnitureType.BOOKSHELF,
    "drawer": FurnitureType.DRAWER,
    "抽屉柜": FurnitureType.DRAWER,
    "tv_stand": FurnitureType.TV_STAND,
    "电视柜": FurnitureType.TV_STAND,
    "other": FurnitureType.OTHER,
    "其他": FurnitureType.OTHER,
}


class _DetectedItem(BaseModel):
    name: str
    type: str
    dimensions: Dimensions
    weight: float | None = Field(default=None, gt=0)
    disassemble: bool = False
    fragile: bool = False
    quantity: int = Field(default=1, ge=1)
    description: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class _DetectionPayload(BaseModel):
    furniture: list[_DetectedItem] = Field(default_factory=list)


class MovingLLMProvider(Protocol):
    def analyze_image(self, image_path: str) -> list[FurnitureItem]:
        ...

    def recommend(self, plan: MovingPlan) -> str:
        ...


def coerce_furniture_type(value: str) -> FurnitureType:
    key = value.strip().lower()
    if key in TYPE_ALIASES:
        return TYPE_ALIASES[key]
    return FurnitureType.OTHER


def parse_detection(
    text: str, *, confidence_threshold: float, max_detections: int
) -> list[FurnitureItem]:
    try:
        payload = _DetectionPayload.model_validate(_load_json_object(text))
    except (VisionParseError, ValidationError) as exc:
        raise VisionParseError(f"无法解析家具清单: {exc}") from exc

    items: list[FurnitureItem] = []
    for raw in payload.furniture:
        if raw.confidence is not None and raw.confidence < confidence_threshold:
            continue
        items.append(
            FurnitureItem(
                name=raw.name,
                furniture_type=coerce_furniture_type(raw.type),
                dimensions=raw.dimensions,
                weight=raw.weight,
                disassemble=raw.disassemble,
                fragile=raw.fragile,
                quantity=raw.quantity,
                description=raw.description,
                dimensions_confirmed=False,
            )
        )
    return items[:max_detections]


def _load_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise VisionParseError("模型响应里没有 JSON 对象")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VisionParseError("模型响应不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise VisionParseError("模型响应的 JSON 顶层必须是对象")
    return data


DETECTION_INSTRUCTIONS = """你是家具识别助手。只根据图片输出 JSON 对象，不要输出其他文字。
格式：
{"furniture":[{"name":"中文名","type":"sofa|chair|table|bed|wardrobe|desk|bookshelf|drawer|tv_stand|other","dimensions":{"length":厘米,"width":厘米,"height":厘米},"weight":千克或null,"disassemble":false,"fragile":false,"quantity":1,"description":"简短描述","confidence":0到1}]}
尺寸和重量是估算。看不清的物品不要编造。没有家具时返回 {"furniture":[]}。"""


class OpenAIProvider:
    def __init__(self, client: OpenAI | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or OpenAI(api_key=self.settings.openai_api_key)

    def analyze_image(self, image_path: str) -> list[FurnitureItem]:
        self._require_key()
        encoded = self._encode_image(image_path)
        first = self._detect(encoded, None)
        try:
            return self._parse(first)
        except VisionParseError as first_error:
            second = self._detect(encoded, str(first_error))
            try:
                return self._parse(second)
            except VisionParseError as second_error:
                raise VisionParseError(
                    "模型两次都没有返回可解析的家具清单"
                ) from second_error

    def recommend(self, plan: MovingPlan) -> str:
        self._require_key()
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是搬家规划助手。只根据给定计划写保护和装车建议。"
                        "尺寸未确认时，明确提醒先核对，不要把估算说成实测。"
                    ),
                },
                {"role": "user", "content": _format_plan(plan)},
            ],
            max_tokens=1500,
            temperature=0.4,
        )
        return response.choices[0].message.content or ""

    def _require_key(self) -> None:
        if not self.settings.openai_api_key:
            raise ConfigurationError("缺少 OPENAI_API_KEY。在 .env 中配置后再调用模型。")

    def _parse(self, text: str) -> list[FurnitureItem]:
        image = self.settings.image
        return parse_detection(
            text,
            confidence_threshold=image.confidence_threshold,
            max_detections=image.max_detections,
        )

    def _detect(self, encoded: str, correction: str | None) -> str:
        user_text = "请分析这张图片中的家具。"
        if correction:
            user_text += f"\n上次响应无法解析：{correction}。请只返回符合格式的 JSON。"
        messages = [
            {"role": "system", "content": DETECTION_INSTRUCTIONS},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    },
                ],
            },
        ]
        request = {
            "model": self.settings.openai_model,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.2,
        }
        try:
            response = self.client.chat.completions.create(
                **request, response_format={"type": "json_object"}
            )
        except BadRequestError:
            response = self.client.chat.completions.create(**request)
        return response.choices[0].message.content or ""

    def _encode_image(self, image_path: str) -> str:
        image = Image.open(image_path)
        if image.mode != "RGB":
            image = image.convert("RGB")
        edge = self.settings.image.max_edge_px
        if max(image.size) > edge:
            ratio = edge / max(image.size)
            resized = tuple(int(side * ratio) for side in image.size)
            image = image.resize(resized, Image.Resampling.LANCZOS)

        quality = self.settings.image.jpeg_quality
        payload = b""
        while quality >= 30:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality)
            payload = buffer.getvalue()
            if len(payload) <= self.settings.image.max_bytes:
                break
            quality -= 10
        if len(payload) > self.settings.image.max_bytes:
            raise ConfigurationError("图片压缩后仍超过大小限制")
        return base64.b64encode(payload).decode("utf-8")


def _format_plan(plan: MovingPlan) -> str:
    furniture = "\n".join(
        f"- {item.name} ({item.furniture_type.value}) "
        f"{item.dimensions.length}x{item.dimensions.width}x{item.dimensions.height}cm "
        f"x{item.quantity} 已确认={item.dimensions_confirmed}"
        for item in plan.furniture_items
    )
    boxes = "\n".join(
        f"- {req.size.value}: {req.count}个" for req in plan.box_requirements
    ) or "- 无"
    space = plan.space_estimation
    return f"""家具清单:
{furniture}

空间:
- 有效体积: {space.effective_volume_cm3:.0f} cm³
- 车辆: {space.truck_name}，{space.trips} 趟
- 装载效率: {space.packing_efficiency}%

纸箱:
{boxes}

装载顺序:
{chr(10).join(plan.loading_order) or "- 无"}

三维摆放（{plan.cargo_layout.axis_note}）:
{chr(10).join(f"- {item.note}：{item.name}" for item in plan.cargo_layout.placements[:40]) or "- 无"}
{("放不下: " + "、".join(plan.cargo_layout.unplaced)) if plan.cargo_layout.unplaced else ""}

行程: {plan.context.distance_km} km，楼梯层数 {plan.context.stair_floors()}
费用: ¥{plan.total_cost_estimate}
工时: {plan.estimated_time}
尺寸是否已全部确认: {plan.dimensions_confirmed}
"""
