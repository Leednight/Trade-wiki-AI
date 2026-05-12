#!/bin/bash
set -e

echo "================================"
echo " Trade-Wiki-AI 环境安装"
echo "================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.10+"
    exit 1
fi

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "[1/4] 创建虚拟环境..."
    python3 -m venv .venv
else
    echo "[1/4] 虚拟环境已存在，跳过"
fi

# 激活虚拟环境
source .venv/bin/activate

# 升级 pip
echo "[2/4] 升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "[3/4] 安装项目依赖..."
pip install -e ".[dev]" 2>/dev/null || pip install -e .

# 创建 .env 文件
if [ ! -f ".env" ]; then
    echo "[4/4] 创建 .env 配置文件..."
    cp .env.example .env
    echo "[注意] 请编辑 .env 文件，填入 API Key 等配置"
else
    echo "[4/4] .env 已存在，跳过"
fi

# 创建数据目录
mkdir -p data/db data/chromadb data/raw/books data/raw/videos

echo ""
echo "================================"
echo " 安装完成！"
echo " 下一步："
echo "   1. 编辑 .env 填入配置"
echo "   2. 运行 scripts/pull_model.sh 拉取模型"
echo "   3. 运行 scripts/run.sh 启动服务"
echo "================================"
