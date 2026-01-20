from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import tempfile
import os
import shutil

from src.agent import MovingLLMAgent

app = FastAPI(title="MovingLLM API", description="家具搬家空间估算API")

agent = MovingLLMAgent()


@app.get("/")
async def root():
    return {
        "message": "MovingLLM API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "POST - 分析家具图片并生成搬家计划",
            "/recommend": "POST - 获取AI详细建议",
        },
    }


@app.post("/analyze")
async def analyze_moving(files: List[UploadFile] = File(...)):
    """
    上传家具图片，获取搬家计划
    """
    if not files:
        raise HTTPException(status_code=400, detail="至少需要上传一张图片")

    temp_files = []
    try:
        for file in files:
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400, detail=f"文件 {file.filename} 不是图片格式"
                )

            filename = file.filename if file.filename else "upload.jpg"
            suffix = os.path.splitext(filename)[1]
            temp_path = tempfile.mktemp(suffix=suffix)

        plan = agent.analyze_moving_plan(temp_files)

        result = {
            "furniture_items": [
                {
                    "name": item.name,
                    "type": item.furniture_type.name,
                    "dimensions": {
                        "length": item.dimensions.length,
                        "width": item.dimensions.width,
                        "height": item.dimensions.height,
                    },
                    "weight": item.weight,
                    "disassemble": item.disassemble,
                    "fragile": item.fragile,
                    "quantity": item.quantity,
                    "description": item.description,
                }
                for item in plan.furniture_items
            ],
            "space_estimation": {
                "total_volume": plan.space_estimation.total_volume,
                "packed_volume": plan.space_estimation.packed_volume,
                "truck_size_required": plan.space_estimation.truck_size_required,
                "packing_efficiency": plan.space_estimation.packing_efficiency,
            },
            "box_requirements": [
                {
                    "size": req.size.name,
                    "dimensions": {
                        "length": req.dimensions.length,
                        "width": req.dimensions.width,
                        "height": req.dimensions.height,
                    },
                    "count": req.count,
                    "weight_capacity": req.weight_capacity,
                }
                for req in plan.box_requirements
            ],
            "total_cost_estimate": plan.total_cost_estimate,
            "estimated_time": plan.estimated_time,
            "tips": plan.tips,
        }

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)


@app.post("/recommend")
async def get_recommendations(files: List[UploadFile] = File(...)):
    """
    上传家具图片，获取AI详细建议
    """
    if not files:
        raise HTTPException(status_code=400, detail="至少需要上传一张图片")

    temp_files = []
    try:
        for file in files:
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400, detail=f"文件 {file.filename} 不是图片格式"
                )

            filename = file.filename if file.filename else "upload.jpg"
            suffix = os.path.splitext(filename)[1]
            temp_path = tempfile.mktemp(suffix=suffix)

            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            temp_files.append(temp_path)

        plan = agent.analyze_moving_plan(temp_files)
        recommendations = agent.get_recommendations(plan)

        return JSONResponse(
            content={
                "plan": {
                    "space_estimation": plan.space_estimation.__dict__,
                    "box_requirements": [req.__dict__ for req in plan.box_requirements],
                },
                "recommendations": recommendations,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
