#!/bin/bash
# 创建 arxiv- 命令符号链接

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/arxiv-cli.py"

# 确保脚本存在
if [ ! -f "$CLI_SCRIPT" ]; then
    echo "错误: arxiv-cli.py 不存在"
    exit 1
fi

# 创建符号链接
echo "创建 arxiv- 命令符号链接..."

ln -sf "$CLI_SCRIPT" "arxiv-start"
ln -sf "$CLI_SCRIPT" "arxiv-stop"
ln -sf "$CLI_SCRIPT" "arxiv-restart"
ln -sf "$CLI_SCRIPT" "arxiv-status"
ln -sf "$CLI_SCRIPT" "arxiv-smi"
ln -sf "$CLI_SCRIPT" "arxiv-rn"
ln -sf "$CLI_SCRIPT" "arxiv-report"
ln -sf "$CLI_SCRIPT" "arxiv-config"
ln -sf "$CLI_SCRIPT" "arxiv-keywords"
ln -sf "$CLI_SCRIPT" "arxiv-logs"
ln -sf "$CLI_SCRIPT" "arxiv-help"

echo "符号链接创建完成!"
echo "现在可以使用 arxiv- 命令了"