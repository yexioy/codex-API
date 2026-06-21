#!/bin/bash
# ============================================================
#  Codex 自定义 API 一键配置 —— Mac 双击启动器
#  和 codex-setup.py 放同一文件夹。首次使用如双击无反应，
#  先在终端执行一次：chmod +x "配置Codex-Mac.command"
# ============================================================
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    python3 codex-setup.py "$@"
else
    echo "[x] 没检测到 python3。请先安装：https://www.python.org/downloads/"
fi

echo
read -n 1 -s -r -p "按任意键关闭窗口..."
echo
