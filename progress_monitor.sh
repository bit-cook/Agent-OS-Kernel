#!/bin/bash

END_TIME="24:00"
TARGET="telegram:223969284"
PROJECT_DIR="/root/.openclaw/workspace/Agent-OS-Kernel"
REPORT_FILE="/root/.openclaw/workspace/last_progress_report.txt"

# 计算距离24:00的秒数
get_seconds_until_midnight() {
    local current_hour=$(date -u +%H)
    local current_minute=$(date -u +%M)
    local current_seconds=$(date -u +%S)
    
    local current_total_seconds=$((current_hour * 3600 + current_minute * 60 + current_seconds))
    local end_seconds=$((24 * 3600))  # 24:00 UTC = 86400秒
    
    if [ $current_total_seconds -ge $end_seconds ]; then
        echo 0
    else
        echo $((end_seconds - current_total_seconds))
    fi
}

# 获取项目状态
get_project_status() {
    cd "$PROJECT_DIR" || return 1
    
    local timestamp=$(date -u +"%Y-%m-%d %H:%M UTC")
    local git_status=$(git status --short 2>/dev/null)
    local latest_commit=$(git log --oneline -1 2>/dev/null)
    local new_files=$(echo "$git_status" | grep "^??" | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')
    local file_count=$(find . -type f 2>/dev/null | wc -l)
    
    # 如果没有新增文件
    if [ -z "$new_files" ]; then
        new_files="无"
    fi
    
    cat > "$REPORT_FILE" << REPORT
=== 项目进度 ===
时间: $timestamp
最新提交: $latest_commit
新增文件: $new_files
文件统计: $file_count
继续工作中...
REPORT
    
    cat "$REPORT_FILE"
}

# 发送报告
send_report() {
    if [ -f "$REPORT_FILE" ]; then
        local content=$(cat "$REPORT_FILE")
        # 使用message工具发送
        python3 << PYSCRIPT
import sys
import json

# 这里需要通过外部方式发送消息
# 由于我们在bash中，我们将内容保存供主进程发送
with open('/root/.openclaw/workspace/pending_report.json', 'w') as f:
    json.dump({
        'channel': 'telegram',
        'target': '$TARGET',
        'message': '''$content'''
    }, f)
PYSCRIPT
    fi
}

# 主循环
echo "开始项目进度监控..."
echo "结束时间: $END_TIME UTC"

iteration=0
while true; do
    iteration=$((iteration + 1))
    echo "=== 第 $iteration 次检查 ==="
    echo "当前时间: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    
    # 获取并显示状态
    get_project_status
    echo ""
    
    # 检查是否到达24:00
    seconds_until=$(get_seconds_until_midnight)
    if [ $seconds_until -eq 0 ]; then
        echo "已到达24:00 UTC，监控结束。"
        break
    fi
    
    # 计算下一次等待时间（5分钟 = 300秒）
    wait_time=300
    
    # 如果距离结束时间不足5分钟，等待剩余时间
    if [ $seconds_until -lt 300 ]; then
        wait_time=$seconds_until
    fi
    
    echo "等待 ${wait_time} 秒后进行下一次检查..."
    echo "---"
    sleep $wait_time
done

echo "项目进度监控任务完成。"
