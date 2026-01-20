# MovingLLM 使用说明

## 项目概述

MovingLLM 是一个基于大语言模型的智能搬家空间估算系统。它能够：
- 通过家具照片识别家具类型、尺寸和重量
- 计算搬家所需的空间和车辆类型
- 自动计算所需纸箱的数量和大小
- 提供专业的搬家建议和装载方案

## 核心功能模块

### 1. 图像分析模块 (image_analyzer.py)
- 使用 OpenAI GPT-4 Vision API 分析家具照片
- 识别家具类型、估算尺寸和重量
- 判断是否需要拆卸和是否易碎

### 2. 空间估算模块 (space_estimator.py)
- 计算总体积和装载体积
- 推荐合适的车辆类型
- 生成装载布局建议
- 计算装载效率

### 3. 纸箱计算模块 (box_calculator.py)
- 根据家具数量和尺寸计算所需纸箱
- 提供四种规格的纸箱建议
- 生成包装提示

### 4. 主 Agent (agent.py)
- 协调所有模块工作
- 调用 LLM 获取详细建议
- 估算搬家费用和时间

## 使用流程

### 命令行使用

```bash
# 1. 基本分析
python main.py sofa.jpg desk.jpg

# 2. 获取 AI 详细建议
python main.py sofa.jpg desk.jpg --recommend

# 3. 批量处理
python main.py *.jpg
```

### API 使用

```bash
# 1. 启动服务器
python api_server.py

# 2. 访问 API 文档
# http://localhost:8000/docs

# 3. 使用 API 分析
curl -X POST "http://localhost:8000/analyze" \
  -F "files=@sofa.jpg" \
  -F "files=@desk.jpg"
```

### Python 代码使用

```python
from src.agent import MovingLLMAgent

# 创建 agent
agent = MovingLLMAgent()

# 分析家具图片
plan = agent.analyze_moving_plan([
    "path/to/sofa.jpg",
    "path/to/desk.jpg"
])

# 获取结果
print(f"家具数量: {len(plan.furniture_items)}")
print(f"所需纸箱: {sum(req.count for req in plan.box_requirements)}")
print(f"建议车辆: {plan.space_estimation.truck_size_required}")
print(f"预计费用: ¥{plan.total_cost_estimate}")

# 获取 AI 建议
recommendations = agent.get_recommendations(plan)
print(recommendations)
```

## 输出说明

### 家具清单
包含识别到的每件家具的详细信息：
- 名称和类型
- 尺寸（长×宽×高）
- 重量
- 是否可拆卸
- 是否易碎
- 数量

### 空间估算
- 总体积：所有家具的体积总和
- 装载体积：考虑堆叠和包装后的实际体积
- 车辆建议：推荐使用的搬家车辆类型
- 装载效率：空间利用率百分比

### 纸箱需求
- 每种规格的纸箱数量
- 纸箱尺寸和承重能力
- 建议装填内容

### 成本估算
- 预计搬家费用（运输+纸箱+人工）
- 预计所需时间

### 建议
- 物品保护建议
- 装载顺序建议
- 包装注意事项

## 配置说明

编辑 `.env` 文件可以配置：

```env
OPENAI_API_KEY=your_api_key        # OpenAI API 密钥
OPENAI_MODEL=gpt-4-vision-preview  # 使用的模型
MAX_IMAGE_SIZE=4194304              # 最大图片大小（字节）
```

编辑 `config/config.yaml` 可以配置：

- 纸箱规格
- 空间估算参数
- 阈值设置

## 技术架构

```
用户输入（图片）
    ↓
图像分析 (GPT-4 Vision)
    ↓
家具信息识别
    ↓
    ├─→ 空间估算 → 车辆建议、布局方案
    │
    └─→ 纸箱计算 → 纸箱数量和规格
    ↓
AI 建议 (GPT-4)
    ↓
完整搬家计划
```

## 依赖说明

- **openai**: OpenAI API 客户端
- **pillow**: 图像处理
- **opencv-python**: 计算机视觉（可选）
- **fastapi**: Web API 框架
- **pydantic**: 数据验证
- **python-dotenv**: 环境变量管理

## 测试

运行测试验证功能：

```bash
python test_moving_llm.py
```

测试覆盖：
- 家具数据模型
- 空间估算算法
- 纸箱计算逻辑

## 注意事项

1. **API 密钥**: 需要有效的 OpenAI API 密钥
2. **图片质量**: 建议使用清晰、光线充足的照片
3. **尺寸估算**: 基于 AI 估算，可能存在误差
4. **成本估算**: 仅供参考，实际费用因地区和服务商而异
5. **网络连接**: 需要稳定的网络连接访问 OpenAI API

## 常见问题

### Q: 为什么识别不到家具？
A: 检查图片清晰度和光线条件，确保图片质量良好

### Q: 尺寸估算不准确？
A: AI 基于视觉估算，可能需要手动调整

### Q: 如何提高准确性？
A: 提供多角度照片，确保参考物体（如人、门）在照片中

### Q: OpenCV 错误？
A: OpenCV 是可选依赖，不影响主要功能

## 扩展开发

### 添加新的家具类型

编辑 `src/models.py`，在 `FurnitureType` 枚举中添加新类型

### 自定义纸箱规格

编辑 `config/config.yaml` 中的 `box_sizes` 部分

### 添加新的估算算法

在 `src/space_estimator.py` 中实现新的估算方法

## 支持

如遇问题，请：
1. 查看 [QUICKSTART.md](QUICKSTART.md)
2. 查看 [README.md](README.md)
3. 检查测试用例 [test_moving_llm.py](test_moving_llm.py)
4. 查看代码注释