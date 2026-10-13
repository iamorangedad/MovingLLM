import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from src.agent import MovingLLMAgent
from src.config import default_context, get_settings
from src.errors import ConfigurationError, VisionParseError
from src.models import MoveContext, MovingPlan, RecalculateRequest, RecommendResponse

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def create_app(agent: MovingLLMAgent | None = None) -> FastAPI:
    resolved = agent or MovingLLMAgent()
    app = FastAPI(title="MovingLLM API", description="家具搬家空间估算 API")

    @app.get("/")
    def root():
        return {
            "message": "MovingLLM API",
            "version": "1.1.0",
            "endpoints": {
                "/analyze": "POST 上传图片并生成搬家计划",
                "/recommend": "POST 上传图片并生成文字建议",
                "/recalculate": "POST 用确认后的家具清单重算，不调用模型",
            },
        }

    @app.post("/analyze", response_model=MovingPlan)
    async def analyze_moving(
        files: list[UploadFile] = File(...),
        distance_km: float | None = Form(default=None),
        origin_floor: int | None = Form(default=None),
        destination_floor: int | None = Form(default=None),
        origin_has_elevator: bool | None = Form(default=None),
        destination_has_elevator: bool | None = Form(default=None),
    ):
        context = _context_from_form(
            distance_km,
            origin_floor,
            destination_floor,
            origin_has_elevator,
            destination_has_elevator,
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = await _save_uploads(files, directory)
            return _run_plan(lambda: resolved.analyze_moving_plan(paths, context))

    @app.post("/recommend", response_model=RecommendResponse)
    async def get_recommendations(
        files: list[UploadFile] = File(...),
        distance_km: float | None = Form(default=None),
        origin_floor: int | None = Form(default=None),
        destination_floor: int | None = Form(default=None),
        origin_has_elevator: bool | None = Form(default=None),
        destination_has_elevator: bool | None = Form(default=None),
    ):
        context = _context_from_form(
            distance_km,
            origin_floor,
            destination_floor,
            origin_has_elevator,
            destination_has_elevator,
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = await _save_uploads(files, directory)

            def run():
                plan = resolved.analyze_moving_plan(paths, context)
                return RecommendResponse(
                    plan=plan, recommendations=resolved.get_recommendations(plan)
                )

            return _run_plan(run)

    @app.post("/recalculate", response_model=MovingPlan)
    def recalculate(body: RecalculateRequest):
        return resolved.plan_from_items(
            body.furniture_items, body.context, confirmed=True
        )

    return app


def _context_from_form(
    distance_km, origin_floor, destination_floor, origin_has_elevator, destination_has_elevator
) -> MoveContext:
    data = default_context().model_dump()
    if distance_km is not None:
        data["distance_km"] = distance_km
    if origin_floor is not None:
        data["origin_floor"] = origin_floor
    if destination_floor is not None:
        data["destination_floor"] = destination_floor
    if origin_has_elevator is not None:
        data["origin_has_elevator"] = origin_has_elevator
    if destination_has_elevator is not None:
        data["destination_has_elevator"] = destination_has_elevator
    try:
        return MoveContext.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


async def _save_uploads(files: list[UploadFile], directory: str) -> list[str]:
    if not files:
        raise HTTPException(status_code=400, detail="至少需要上传一张图片")

    limit = get_settings().image.max_bytes
    paths = []
    for index, file in enumerate(files):
        filename = file.filename or "upload.jpg"
        suffix = Path(filename).suffix.lower()
        content_type = file.content_type or ""
        if not content_type.startswith("image/") and suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"文件 {filename} 不是图片格式")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"文件 {filename} 是空的")
        if len(data) > limit:
            raise HTTPException(status_code=413, detail=f"文件 {filename} 超过大小限制")
        path = os.path.join(directory, f"{index}{suffix or '.jpg'}")
        with open(path, "wb") as handle:
            handle.write(data)
        paths.append(path)
    return paths


def _run_plan(callback):
    try:
        return callback()
    except VisionParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
