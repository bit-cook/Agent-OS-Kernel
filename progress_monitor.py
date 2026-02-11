#!/usr/bin/env python3
"""进度监控器 - 每5分钟检查并汇报"""

import subprocess
import time
from datetime import datetime

last_commits = 0

while True:
    try:
        # 获取提交数
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True, text=True, cwd='/root/.openclaw/workspace/Agent-OS-Kernel'
        )
        current_commits = int(result.stdout.strip())
        
        # 获取今日提交
        today = datetime.now().strftime('%Y-%m-%d')
        result = subprocess.run(
            ['git', 'log', '--since', f'{today} 00:00:00', '--oneline'],
            capture_output=True, text=True, cwd='/root/.openclaw/workspace/Agent-OS-Kernel'
        )
        today_commits = len(result.stdout.strip().split('\n')) - 1 if result.stdout.strip() else 0
        
        # 检查是否有新提交
        if current_commits > last_commits:
            new_work = current_commits - last_commits
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 新提交: +{new_work}")
            last_commits = current_commits
        
        status = f"📊 进度: 总提交 {current_commits}, 今日 +{today_commits}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status}")
        
        # 写状态文件
        with open('/root/.openclaw/workspace/PROGRESS_STATUS.txt', 'w') as f:
            f.write(f"{datetime.now().isoformat()}\n")
            f.write(f"总提交: {current_commits}\n")
            f.write(f"今日提交: {today_commits}\n")
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {e}")
    
    time.sleep(300)  # 5分钟
