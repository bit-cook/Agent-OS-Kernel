#!/bin/bash

# 持续运行的项目进度监控脚本
# 每5分钟发送一次报告，直到24:00 UTC

CHANNEL="telegram"
TARGET="telegram:223969284"
PROJECT_DIR="/root/.openclaw/workspace/Agent-OS-Kernel"

while true; do
    # 获取当前时间
    CURRENT_HOUR=$(date -u +%H)
    CURRENT_MINUTE=$(date -u +%M)
    CURRENT_TIME_SECONDS=$((CURRENT_HOUR * 3600 + CURRENT_MINUTE * 60))
    END_TIME_SECONDS=86400  # 24:00 UTC
    
    # 如果已经超过24:00，退出
    if [ $CURRENT_TIME_SECONDS -ge $END_TIME_SECONDS ]; then
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] 已到达24:00 UTC，任务结束。"
        break
    fi
    
    # 进入项目目录
    cd "$PROJECT_DIR" 2>/dev/null || {
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] 无法进入目录: $PROJECT_DIR"
        sleep 300
        continue
    }
    
    # 获取git状态
    GIT_STATUS=$(git status --short 2>/dev/null)
    
    # 获取最新提交
    LATEST_COMMIT=$(git log --oneline -1 2>/dev/null)
    
    # 统计新增文件
    NEW_FILES=$(echo "$GIT_STATUS" | grep "^??" | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')
    if [ -z "$NEW_FILES" ]; then
        NEW_FILES="无"
    fi
    
    # 统计文件总数
    FILE_COUNT=$(find . -type f 2>/dev/null | wc -l)
    
    # 生成时间戳
    TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
    
    # 构建报告
    REPORT="=== 项目进度 ===
时间: $TIMESTAMP
最新提交: $LATEST_COMMIT
新增文件: $NEW_FILES
文件统计: $FILE_COUNT
继续工作中..."
    
    echo "发送报告: $REPORT"
    
    # 发送消息
    python3 << PYSCRIPT
import subprocess
import json

message = """$REPORT"""

result = subprocess.run([
    'openclaw', 'message', 'send',
    '--channel', '$CHANNEL',
    '--target', '$TARGET',
    '--message', message
], capture_output=True, text=True)

if result.returncode == 0:
    print("✓ 消息发送成功")
else:
    print(f"✗ 消息发送失败: {result.stderr}")
PYSCRIPT
    
    echo "---"
    
    # 等待5分钟（300秒）
    sleep 300
done
