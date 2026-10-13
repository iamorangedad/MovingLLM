# 项目状态

当前行为以 [docs/design.md](docs/design.md) 为准，模块边界以 [docs/architecture.md](docs/architecture.md) 为准。

照片先解析成家具清单，再由规划代码计算纸箱、车厢、装载顺序和费用。图像尺寸默认未确认，确认后通过 `plan_from_items` 或 `POST /recalculate` 重算，不再请求模型。

业务系数在 `config/config.yaml`。密钥只放在环境变量。
