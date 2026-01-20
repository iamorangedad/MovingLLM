#!/bin/bash

echo "MovingLLM 安装脚本"
echo "==================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "检测到Python版本: $python_version"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "错误: pip3 未安装"
    exit 1
fi

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境? (y/n): " create_venv
if [ "$create_venv" = "y" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 安装依赖
echo "安装依赖包..."
pip3 install -r requirements.txt

# 检查.env文件
if [ ! -f .env ]; then
    echo "创建.env文件..."
    cp .env.example .env
    
    echo ""
    echo "重要: 请编辑 .env 文件并填入你的 OpenAI API 密钥"
    echo ""
else
    echo ".env文件已存在"
fi

# 创建必要的目录
mkdir -p models
mkdir -p examples

echo ""
echo "安装完成!"
echo ""
echo "下一步:"
echo "1. 编辑 .env 文件，填入 OPENAI_API_KEY"
echo "2. 运行示例: python3 examples/example_usage.py"
echo "3. 或者启动API服务器: python3 api_server.py"
echo ""