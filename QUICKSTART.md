# 快速开始指南

## 1. 安装

### 使用安装脚本（推荐）

```bash
chmod +x setup.sh
./setup.sh
```

### 手动安装

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，填入你的 OpenAI API 密钥
nano .env
```

## 2. 配置

编辑 `.env` 文件：

```env
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_MODEL=gpt-4-vision-preview
```

## 3. 使用

### 命令行模式

```bash
# 基本分析
python main.py path/to/furniture.jpg

# 多张图片
python main.py image1.jpg image2.jpg image3.jpg

# 获取AI详细建议
python main.py path/to/furniture.jpg --recommend
```

### API模式

```bash
# 启动服务器
python api_server.py

# 在浏览器访问
open http://localhost:8000/docs
```

### Python代码

```python
from src.agent import MovingLLMAgent

agent = MovingLLMAgent()
plan = agent.analyze_moving_plan(["furniture.jpg"])
```

## 4. 运行测试

```bash
python test_moving_llm.py
```

## 5. 示例

查看使用示例：

```bash
python examples/example_usage.py
```

## 常见问题

### Q: 出现 "OpenAI API key not configured" 错误
A: 确保 `.env` 文件中正确配置了 `OPENAI_API_KEY`

### Q: API请求失败
A: 检查网络连接和API密钥是否有效

### Q: OpenCV相关的错误
A: 这是正常的，系统会在没有OpenCV的情况下使用备用功能

## 下一步

- 查看 [README.md](README.md) 了解更多详细信息
- 查看 [examples/example_usage.py](examples/example_usage.py) 查看代码示例
- 查看 [api_server.py](api_server.py) 了解API接口