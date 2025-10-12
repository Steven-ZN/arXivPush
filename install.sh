#!/bin/bash
# arXiv Push 安装脚本

echo "arXiv Push 安装向导"
echo "==================="

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "检测到 Python 版本: $python_version"

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "安装 Python 依赖..."
pip install -r requirements.txt

# 配置文件
echo ""
echo "配置文件设置:"
echo "1. 请复制 .env.template 为 .env 并填写您的 Discord Bot Token"
echo "2. 请复制 config.yaml.template 为 config.yaml 并填写配置"
echo ""

# 创建符号链接命令
echo "创建命令行工具..."
chmod +x install_commands.sh
./install_commands.sh

echo ""
echo "安装完成!"
echo "使用方法:"
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 配置 Discord 和 Ollama"
echo "3. 启动服务: python arxiv-cli.py start"
echo ""
echo "帮助: python arxiv-cli.py help"