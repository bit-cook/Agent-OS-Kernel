#!/bin/bash
cd /root/.openclaw/workspace/Agent-OS-Kernel
echo "=== $(date '+%H:%M:%S') ===" >> /root/.openclaw/workspace/PROGRESS.md
echo "Git提交: $(git rev-list --count HEAD)" >> /root/.openclaw/workspace/PROGRESS.md
echo "今日提交: $(git log --since='today 00:00:00' --oneline | wc -l)" >> /root/.openclaw/workspace/PROGRESS.md
echo "---" >> /root/.openclaw/workspace/PROGRESS.md
