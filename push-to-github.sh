#!/bin/bash
# Agent-OS-Kernel Git 推送脚本
# 在本地运行此脚本推送到 GitHub

set -e

echo "========================================"
echo "🚀 Agent-OS-Kernel 推送到 GitHub"
echo "========================================"
echo ""

# 检查是否配置了 Git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 错误: 不是 Git 仓库"
    exit 1
fi

# 获取当前目录
REPO_DIR=$(pwd)
echo "📁 仓库目录: $REPO_DIR"

# 检查 remote
echo ""
echo "📡 检查 Git Remote..."
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$REMOTE" ]]; then
    echo "❌ 未配置 origin remote"
    echo "请先配置: git remote add origin https://github.com/bit-cook/Agent-OS-Kernel.git"
    exit 1
fi
echo "✅ Remote: $REMOTE"

# 检查是否有未提交的更改
echo ""
echo "📦 检查未提交更改..."
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "⚠️  有未提交的更改"
    echo ""
    echo "未提交的更改:"
    git status --short
    echo ""
    read -p "是否提交这些更改? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📝 请输入提交消息:"
        read COMMIT_MSG
        git add -A
        git commit -m "$COMMIT_MSG"
        echo "✅ 提交完成"
    fi
fi

# 切换到 SSH (如果需要)
echo ""
if [[ "$REMOTE" == https://* ]]; then
    read -p "是否切换到 SSH Remote? (推荐) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 切换到 SSH..."
        git remote set-url origin git@github.com:bit-cook/Agent-OS-Kernel.git
        echo "✅ 已切换到 SSH"
    fi
fi

# 推送到 GitHub
echo ""
echo "📤 推送到 GitHub..."
echo "提示: 如果使用 HTTPS，需要输入 GitHub username 和 personal access token"
echo ""

if git remote get-url origin 2>/dev/null | grep -q "^git@"; then
    # SSH 方式
    echo "使用 SSH 方式推送..."
    echo "请确保已将 SSH 公钥添加到 GitHub:"
    echo "  https://github.com/settings/keys"
    echo ""
fi

# 执行推送
git push origin main

echo ""
echo "========================================"
echo "✅ 推送完成!"
echo "========================================"
echo ""
echo "🔗 查看仓库:"
echo "  https://github.com/bit-cook/Agent-OS-Kernel"
echo ""
echo "📊 查看提交:"
echo "  https://github.com/bit-cook/Agent-OS-Kernel/commits/main"
