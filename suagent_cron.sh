#!/bin/bash
# SuAgent 定时汇报脚本

cd /root/.openclaw/workspace

# 运行汇报
python3 suagent.py

# 发送报告到Telegram (如果配置了)
if [ -f /root/.openclaw/workspace/suagent_report.txt ]; then
    # 这里可以添加OpenClaw消息发送命令
    cat /root/.openclaw/workspace/suagent_report.txt
fi
