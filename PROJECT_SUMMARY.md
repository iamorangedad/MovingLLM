# MovingLLM 项目摘要

## 项目信息

**项目名称**: MovingLLM - 智能搬家空间估算助手  
**项目类型**: AI 图像识别 + 空间规划应用  
**技术栈**: Python, OpenAI GPT-4 Vision, FastAPI

## 代码统计

- **总代码行数**: 1,138 行（不含注释和空行）
- **核心模块**: 6 个
- **测试用例**: 5 个
- **API 接口**: 3 个

## 项目结构

```
MovingLLM/
├── src/                    # 核心源代码
│   ├── agent.py           # 主 Agent (135 行)
│   ├── image_analyzer.py  # 图像分析 (169 行)
│   ├── space_estimator.py # 空间估算 (115 行)
│   ├── box_calculator.py  # 纸箱计算 (181 行)
│   ├── models.py          # 数据模型 (74 行)
│   └── config.py          # 配置管理 (18 行)
├── main.py                # 命令行入口 (102 行)
├── api_server.py          # API 服务器 (152 行)
├── test_moving_llm.py     # 单元测试 (103 行)
└── examples/
    └── example_usage.py    # 使用示例 (89 行)
```

## 核心功能

### 1. 图像识别 (image_analyzer.py)
- 使用 OpenAI GPT-4 Vision API
- 自动识别家具类型（10种类型）
- 估算尺寸和重量
- 判断拆卸性和易碎性

### 2. 空间估算 (space_estimator.py)
- 计算总体积和装载体积
- 推荐 5 种车辆类型
- 生成装载布局建议
- 计算装载效率

### 3. 纸箱计算 (box_calculator.py)
- 4 种规格纸箱（小/中/大/超大）
- 智能计算所需数量
- 提供包装建议

### 4. 主 Agent (agent.py)
- 协调所有模块
- 估算搬家成本和时间
- 生成 AI 详细建议

## 接口说明

### 命令行接口
```bash
python main.py [images...] [--recommend]
```

### REST API 接口
- `GET /` - API 信息
- `POST /analyze` - 分析家具图片
- `POST /recommend` - 获取 AI 建议

### Python 接口
```python
agent = MovingLLMAgent()
plan = agent.analyze_moving_plan(images)
```

## 数据模型

### 主要模型
- `FurnitureItem` - 家具信息
- `SpaceEstimation` - 空间估算结果
- `BoxRequirement` - 纸箱需求
- `MovingPlan` - 完整搬家计划

### 枚举类型
- `FurnitureType` - 家具类型（10种）
- `BoxSize` - 纸箱规格（4种）

## 测试覆盖

✅ 家具数据模型测试  
✅ 尺寸体积计算测试  
✅ 空间估算算法测试  
✅ 纸箱计算逻辑测试  
✅ 纸箱规格测试

**测试结果**: 5/5 通过 (100%)

## 依赖项

### 核心依赖
- openai>=1.0.0
- pillow>=10.0.0
- fastapi>=0.100.0

### 可选依赖
- opencv-python>=4.8.0
- torch>=2.0.0

## 配置项

### 环境变量
- `OPENAI_API_KEY` - OpenAI API 密钥
- `OPENAI_MODEL` - 使用的模型
- `MAX_IMAGE_SIZE` - 最大图片大小

### 配置文件
- `confidence_threshold` - 置信度阈值
- `padding_factor` - 填充系数
- `stacking_factor` - 堆叠系数
- `box_sizes` - 纸箱规格

## 使用示例

### 快速开始
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API 密钥
cp .env.example .env
# 编辑 .env 文件

# 3. 运行
python main.py furniture.jpg
```

### API 服务
```bash
python api_server.py
# 访问 http://localhost:8000/docs
```

## 输出示例

```
============================================================
搬家计划报告
============================================================

家具清单:
1. 沙发 (SOFA)
   尺寸: 200x90x85 cm
   重量: 35 kg

------------------------------------------------------------
空间估算:
总体积: 1,530,000 cm³
建议车辆: 大型厢式车 (约10-15m³)
装载效率: 76.92%

------------------------------------------------------------
纸箱需求:
LARGE: 2个
MEDIUM: 3个

------------------------------------------------------------
预计费用: ¥850.00
预计时间: 约 3 小时 15 分钟

============================================================
```

## 文档

- **README.md** - 项目文档（完整说明）
- **QUICKSTART.md** - 快速开始指南
- **USAGE.md** - 详细使用说明

## 特点

✅ 智能图像识别  
✅ 精确空间估算  
✅ 自动纸箱计算  
✅ 专业搬家建议  
✅ 成本和时间预估  
✅ 多种使用方式（CLI/API/代码）  
✅ 完整测试覆盖  
✅ 详细文档

## 适用场景

- 个人搬家规划
- 搬家公司报价参考
- 物流空间估算
- 家具摆放规划

## 注意事项

⚠️ 需要 OpenAI API 密钥  
⚠️ 需要网络连接  
⚠️ 尺寸为估算值  
⚠️ 成本仅供参考

## 扩展性

- 易于添加新的家具类型
- 可自定义纸箱规格
- 可扩展估算算法
- 可集成其他 AI 模型

## 项目完成度

✅ 核心功能实现  
✅ 多种接口提供  
✅ 完整文档  
✅ 测试通过  
✅ 可直接使用

---

**创建时间**: 2026-01-19  
**状态**: ✅ 完成  
**测试**: ✅ 全部通过  
**文档**: ✅ 完整