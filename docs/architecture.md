# 架构

MovingLLM 把家具照片变成一份可复核的搬家计划，再分成装车和新家两套可编辑空间。视觉模型只负责识别，体积、纸箱、车辆和费用由规划代码计算。

## 分层

```
命令行 / HTTP
    ↓
MovingLLMAgent          编排，不含供应商 SDK
    ↓
MovingLLMProvider       图像识别、文字建议（可替换）
SpaceEstimator          车厢体积、车型、装载顺序
BoxCalculator           纸箱数量
CargoLayoutPlanner      车厢内左右、上下、前后的初始位置
CargoEdit               装车时的一次拖拽落点
HomeLayoutPlanner       平面图挤压和新家地板落点
    ↓
MovingPlan / CargoLayout / HomeLayout
```

配置从 `config/config.yaml` 读取。`OPENAI_API_KEY` 和可选的 `OPENAI_MODEL` 只来自环境变量。

## 模块边界

| 模块 | 允许做的事 | 不允许做的事 |
|------|------------|--------------|
| `src/provider.py` | 调模型、把响应解析成 `FurnitureItem` | 算体积、选车、报价 |
| `src/cargo.py` | 判断一件家具是散装还是装箱 | 调模型、读环境变量 |
| `src/box_calculator.py` | 按外包络、容积和承重算箱数 | 调模型 |
| `src/space_estimator.py` | 把散装体积和纸箱外体积合成车厢需求 | 再把同一件家具的体积加第二次 |
| `src/layout.py` | 按装载顺序把散装外形和纸箱放进车厢内尺寸，或放进用户给定的一节车厢 | 调模型、改体积、改车型或报价 |
| `src/cargo_edit.py` | 按支撑和车厢边界接受或拒绝一次移动 | 重新计算纸箱、车型或费用 |
| `src/home.py` | 把矩形房间挤成墙和地板，并接受地板上的一次移动 | 把家具换成纸箱，或把它们叠起来 |
| `src/agent.py` | 按顺序调用上面的模块，套用配置里的费用和工时 | 直接构造 OpenAI 客户端 |
| `main.py`、`api_server.py`、`web/*.html`、`web/space.js` | 参数、上传、序列化、绘制和提交鼠标落点 | 复制一套支撑、越界或墙体公式 |

新增模型供应商时实现 `MovingLLMProvider`，不要在 Agent 里写分支。

## 数据流

1. 照片进入 `analyze_image`，得到家具清单。图像估算的 `dimensions_confirmed` 一律为 `false`。
2. `rides_loose` 把每件家具分成散装或装箱。
3. 装箱家具只贡献纸箱的外体积。散装家具只贡献自身外包络乘以松散填充系数。
4. 用有效体积和车厢门尺寸选择车型，装载效率 = 有效体积 /（趟数 × 车厢容积）。
5. `CargoLayoutPlanner` 只使用已经算好的车型和纸箱，写入左右、上下、前后坐标。
6. 费用和工时读取配置，并使用本次的距离、楼层、电梯。
7. 用户改完尺寸后调用 `plan_from_items` 或 `POST /recalculate`。这条路径不再访问模型，并把 `dimensions_confirmed` 设为 `true`。自动三维页面用这份结果重画。
8. 装车页面调用 `arrange_cargo` 和 `move_cargo`。新家页面调用 `build_home` 和 `move_home`。这四条路径都不访问模型。

## 结果对象

`MovingPlan` 是报价和自动摆放的结构，包含家具、空间、纸箱、装载顺序、三维摆放、费用明细、工时、提示和本次 `MoveContext`。手动装车返回 `CargoLayout`，新家返回 `HomeLayout`。接口层不要再用 `dataclass.__dict__` 手工拼 JSON。页面只读取这些对象里的坐标。
