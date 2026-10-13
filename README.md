# MovingLLM

用家具照片生成搬家计划：识别清单、车厢体积、纸箱、车辆和费用。视觉模型只负责识别，体积和报价由规划代码计算。

尺寸来自图像估算，结果里的 `dimensions_confirmed` 为 `false`。核对后再调用重算接口。

架构、公式和研发流程：

- [架构](docs/architecture.md)
- [设计说明](docs/design.md)
- [研发流程](docs/development.md)

## 安装

```bash
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中填写 `OPENAI_API_KEY`。模型名可选，默认使用 `config/config.yaml` 里的 `model`。纸箱、车型和单价也在这个配置文件里。

## 命令行

```bash
python main.py furniture.jpg
python main.py a.jpg b.jpg --distance-km 15 --origin-floor 6 --no-origin-elevator
python main.py furniture.jpg --recommend
```

`--recommend` 会再调用一次模型，根据已经算好的计划写保护与装车建议。

## HTTP

```bash
python api_server.py
```

- `POST /analyze`：上传图片，返回 `MovingPlan`
- `POST /recommend`：上传图片，返回计划和文字建议
- `POST /recalculate`：提交确认后的家具清单和行程，不调用模型

交互文档在 `http://localhost:8000/docs`。

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "files=@furniture.jpg" \
  -F "distance_km=15"
```

确认尺寸后重算：

```bash
curl -X POST "http://localhost:8000/recalculate" \
  -H "Content-Type: application/json" \
  -d '{"furniture_items":[],"context":{"distance_km":15}}'
```

把 `furniture_items` 换成 `/analyze` 返回并修改过的清单。

## 代码

```python
from src.agent import MovingLLMAgent
from src.models import MoveContext

agent = MovingLLMAgent()
plan = agent.analyze_moving_plan(
    ["furniture.jpg"],
    MoveContext(distance_km=15, origin_floor=6, origin_has_elevator=False),
)
print(plan.space_estimation.truck_name, plan.total_cost_estimate)

confirmed = agent.plan_from_items(plan.furniture_items, plan.context, confirmed=True)
```

## 测试

```bash
pytest
```

规划测试不访问网络。图像分析需要可用的 API 密钥。

## 说明

车辆和纸箱按 `docs/design.md` 的规则计算：大件默认散装，纸箱同时受外形和承重约束，装载效率是有效体积占所选车厢的比例。费用使用配置中的单价，并随距离、楼层和电梯变化。
