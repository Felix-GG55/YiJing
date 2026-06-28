#!/bin/bash
# ============================================================
#  易经三钱法 — 一键发布到 GitHub
#  双击或 bash publish.sh 运行,按提示输入 GitHub 用户名
# ============================================================
set -e

cd "$(dirname "$0")"

# 检查 git
if ! command -v git >/dev/null 2>&1; then
    echo "[错误] 未安装 git。请先运行: xcode-select --install"
    exit 1
fi

# 检查 git 状态
if [ ! -d .git ]; then
    echo "[初始化 git 仓库]"
    git init -b main
    git add .
    git -c user.name="codex" -c user.email="codex@local" commit -m "init: yijing windows exe builder"
fi

# 检查 remote
if git remote get-url origin >/dev/null 2>&1; then
    REMOTE=$(git remote get-url origin)
    echo "[已配置远程] $REMOTE"
else
    echo "请输入你的 GitHub 用户名:"
    read -r USERNAME
    if [ -z "$USERNAME" ]; then
        echo "[错误] 用户名不能为空"
        exit 1
    fi
    REPO_URL="https://github.com/${USERNAME}/yijing-release.git"
    echo "[设置远程] $REPO_URL"
    git remote add origin "$REPO_URL"
fi

REMOTE=$(git remote get-url origin)
USERNAME=$(echo "$REMOTE" | sed -E 's#https://github.com/([^/]+)/.*#\1#')

echo
echo "============================================"
echo " 准备 push 到: $REMOTE"
echo " GitHub 用户: $USERNAME"
echo "============================================"
echo
echo "请先在 GitHub 创建空仓库:"
echo "  https://github.com/new"
echo "  Repository name: yijing-release"
echo "  Public(勾选)"
echo "  不要勾 Add README/.gitignore/license"
echo
read -p "已创建好?回车继续 push (Ctrl+C 取消): "

echo
echo "==> git push"
git push -u origin main

echo
echo "============================================"
echo " push 成功!"
echo "============================================"
echo
echo "下一步:触发 Windows .exe 构建"
echo "  1. 打开: https://github.com/${USERNAME}/yijing-release/actions"
echo "  2. 左侧选 'build-windows-exe'"
echo "  3. 右侧 'Run workflow' → 绿色按钮"
echo "  4. 等 1-3 分钟"
echo "  5. 底部 'Artifacts' 下载 'YiJing-windows-exe.zip'"
echo "  6. 解压得 YiJing.exe,双击即跑"
echo
echo "或者直接打 tag 自动发 Release:"
echo "  git tag v1.0 && git push origin v1.0"
