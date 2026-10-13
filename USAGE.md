# 使用说明

公式和字段以 [设计说明](docs/design.md) 为准，模块边界以 [架构](docs/architecture.md) 为准。

## 命令行

```bash
python main.py sofa.jpg desk.jpg
python main.py sofa.jpg --distance-km 12 --origin-floor 5 --destination-floor 2 --no-origin-elevator
python main.py sofa.jpg --recommend
```

报告会标明尺寸是否已确认，并给出散装体积、纸箱外体积、有效体积、车型、趟数、装载顺序和费用明细。

## HTTP

```bash
python api_server.py
```

`POST /analyze` 和 `POST /recommend` 使用 `multipart/form-data`，文件字段名为 `files`。可选表单字段：`distance_km`、`origin_floor`、`destination_floor`、`origin_has_elevator`、`destination_has_elevator`。

`POST /recalculate` 接收 JSON：

```json
{
  "furniture_items": [],
  "context": {
    "distance_km": 12,
    "origin_floor": 5,
    "destination_floor": 1,
    "origin_has_elevator": false,
    "destination_has_elevator": true
  }
}
```

`furniture_items` 使用 `/analyze` 返回的结构，改完长宽高或重量后再提交。

## Python

```python
from src.agent import MovingLLMAgent
from src.models import MoveContext

agent = MovingLLMAgent()
plan = agent.analyze_moving_plan(["sofa.jpg"], MoveContext(distance_km=12))
print(plan.model_dump())
```

不调用模型、只用已有清单：

```python
agent.plan_from_items(plan.furniture_items, confirmed=True)
```

## 结果里要看的字段

- `dimensions_confirmed`：是否已经人工确认尺寸
- `space_estimation.effective_volume_cm3`：实际占用的车厢体积
- `space_estimation.packing_efficiency`：有效体积 /（趟数 × 车厢容积）
- `space_estimation.items_exceed_all_doors`：现有车型门洞装不下的散装家具
- `loading_order`：先装后部的顺序
- `cost_breakdown`：运输、纸箱、人工
