# 研发流程

规格在 `docs/design.md`，边界在 `docs/architecture.md`。两份文档和代码不一致时，先改文档再改代码。

## 改动顺序

1. 在 `docs/design.md` 写清新的公式、接口或配置含义。
2. 只在负责该公式的模块里实现。Agent 负责编排，不复制估算。
3. 为规划公式和响应解析补不访问网络的测试。
4. 运行 `pytest`。涉及上传或重算时，用假的 `MovingLLMProvider`，不要在测试里调用在线模型。

## 配置

- 单价、车型、纸箱、填充系数、默认行程写在 `config/config.yaml`
- `OPENAI_API_KEY` 只放在环境变量或 `.env`。不要写进 yaml、文档或测试
- 需要更换模型时设置 `OPENAI_MODEL`。未设置则使用 yaml 里的 `model`

## 本地检查

```bash
pip install -r requirements.txt
pytest
python main.py --help
```

图像分析需要可用的 API 密钥。规划测试不需要。

## 变更记录

评审结论和由此产生的需求变更存放在 `docs/changes/`，文件名以日期开头，例如 `2026-10-12-architecture-review.md`。新的评审或较大的需求调整按同样格式新增一份，写清当时的状态、问题、改进项和落地位置。已归档的记录不再改写，后续变化另起一份。

## 提交

一个文件对应一个提交。提交信息说明这个文件为什么改。

## 接口稳定

命令行和 HTTP 都返回 `MovingPlan` 的字段。改字段名时同时改 `docs/design.md`、README 和测试。
