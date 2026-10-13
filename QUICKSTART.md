# 快速开始

## 安装

```bash
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，填入 `OPENAI_API_KEY`。车型、纸箱和单价在 `config/config.yaml`。

## 使用

```bash
python main.py path/to/furniture.jpg
python main.py a.jpg b.jpg --distance-km 15 --no-origin-elevator --recommend
python api_server.py
```

API 文档：`http://localhost:8000/docs`。确认尺寸后调用 `POST /recalculate`，不会再次请求模型。

## 测试

```bash
pytest
```

公式和接口约定见 `docs/design.md`。
