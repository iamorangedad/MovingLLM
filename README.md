# MovingLLM - 智能搬家空间估算助手

基于LLM的家具照片分析系统，可以估算搬家时需要占用的空间和放置方案，并给出需要购买纸箱的数量和大小。

## 功能特点

- 🖼️ **图像识别**: 通过家具照片自动识别家具类型、尺寸和重量
- 📦 **空间估算**: 计算搬家所需的空间和车辆类型
- 📋 **纸箱计算**: 自动计算所需纸箱的数量和大小
- 🤖 **AI建议**: 基于LLM提供专业的搬家建议和注意事项
- 🚚 **装载优化**: 优化家具装载顺序和布局
- 💰 **成本估算**: 预估搬家费用和所需时间

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd MovingLLM
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的OpenAI API密钥：

```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-vision-preview
```

## 使用方法

### 命令行使用

#### 基本分析

```bash
python main.py path/to/furniture.jpg
```

#### 分析多张图片

```bash
python main.py image1.jpg image2.jpg image3.jpg
```

#### 获取AI详细建议

```bash
python main.py path/to/furniture.jpg --recommend
```

#### 批量处理

```bash
python main.py *.jpg
```

### API服务

#### 启动API服务器

```bash
python api_server.py
```

API将在 `http://localhost:8000` 运行

#### API文档

访问 `http://localhost:8000/docs` 查看交互式API文档

#### 分析端点

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "files=@furniture1.jpg" \
  -F "files=@furniture2.jpg"
```

#### 建议端点

```bash
curl -X POST "http://localhost:8000/recommend" \
  -F "files=@furniture.jpg"
```

### Python代码使用

```python
from src.agent import MovingLLMAgent

agent = MovingLLMAgent()

plan = agent.analyze_moving_plan(["furniture.jpg"])

print(f"识别到的家具: {len(plan.furniture_items)}件")
print(f"所需纸箱: {sum(req.count for req in plan.box_requirements)}个")
print(f"建议车辆: {plan.space_estimation.truck_size_required}")
print(f"预计费用: ¥{plan.total_cost_estimate}")

# 获取AI建议
recommendations = agent.get_recommendations(plan)
print(recommendations)
```

## 项目结构

```
MovingLLM/
├── src/
│   ├── __init__.py
│   ├── agent.py              # 主Agent类
│   ├── image_analyzer.py     # 图像分析模块
│   ├── space_estimator.py    # 空间估算模块
│   ├── box_calculator.py     # 纸箱计算模块
│   ├── models.py             # 数据模型
│   └── config.py             # 配置管理
├── config/
│   └── config.yaml           # 配置文件
├── examples/
│   ├── example_usage.py      # 使用示例
│   └── sample_furniture.jpg  # 示例图片
├── main.py                   # 命令行入口
├── api_server.py             # API服务器
├── requirements.txt          # 依赖列表
├── .env.example             # 环境变量示例
└── README.md                 # 项目文档
```

## 支持的家具类型

- 沙发 (sofa)
- 椅子 (chair)
- 桌子 (table)
- 床 (bed)
- 衣柜 (wardrobe)
- 书桌 (desk)
- 书架 (bookshelf)
- 抽屉柜 (drawer)
- 电视柜 (tv_stand)
- 其他 (other)

## 纸箱规格

| 尺寸   | 规格 (cm)  | 承重 (kg) |
|--------|------------|-----------|
| 小型   | 30x30x30   | 10        |
| 中型   | 45x45x45   | 20        |
| 大型   | 60x60x60   | 30        |
| 超大型 | 75x75x75   | 40        |

## 输出示例

```
============================================================
搬家计划报告
============================================================

家具清单:
1. 沙发 (SOFA)
   尺寸: 200x90x85 cm
   重量: 35 kg
   可拆卸: 否

2. 书桌 (DESK)
   尺寸: 120x60x75 cm
   重量: 25 kg
   可拆卸: 是

...

------------------------------------------------------------
空间估算:
总体积: 1,234,567 cm³
预计装载体积: 1,456,789 cm³
建议车辆: 大型厢式车 (约10-15m³)
装载效率: 76.92%

------------------------------------------------------------
纸箱需求:
LARGE: 2个
  尺寸: 60x60x60 cm
  承重: 30 kg

MEDIUM: 3个
  尺寸: 45x45x45 cm
  承重: 20 kg

------------------------------------------------------------
预计费用: ¥850.00
预计时间: 约 3 小时 15 分钟

------------------------------------------------------------
建议:
• 有 2 件易碎物品，建议使用防震包装材料
• 可以拆卸 3 件家具以节省空间
• 重物应使用加固纸箱，并分散放置
• 每箱重量建议不超过25kg
• 先将大型家具（床、沙发、衣柜等）放置在车辆后部
...

============================================================
```

## 注意事项

1. **API密钥**: 需要有效的OpenAI API密钥
2. **图片质量**: 建议使用清晰、光线充足的家具照片
3. **尺寸估算**: 尺寸基于AI估算，可能存在误差
4. **成本估算**: 费用为估算值，实际费用可能因地区和服务商而异

## 技术栈

- **AI模型**: OpenAI GPT-4 Vision
- **图像处理**: Pillow, OpenCV
- **Web框架**: FastAPI
- **配置管理**: python-dotenv
- **类型提示**: Python typing

## 开发

### 运行测试

```bash
python examples/example_usage.py
```

### 添加新功能

1. 在 `src/` 目录下添加新模块
2. 更新 `src/agent.py` 集成新功能
3. 添加相应的测试和文档

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！