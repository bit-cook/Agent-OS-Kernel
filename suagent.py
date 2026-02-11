#!/usr/bin/env python3
"""
SuAgent - 项目监工

监督项目完成进度，每5分钟汇报
"""

import os
import sys
import time
import subprocess
import re
from datetime import datetime, timezone

# 配置
PROJECTS = {
    "Agent-OS-Kernel": "/root/.openclaw/workspace/Agent-OS-Kernel",
    "OmniMind": "/root/.openclaw/workspace/OmniMind"
}

REPORT_INTERVAL = 300  # 5分钟

# 项目目标
PROJECT_GOALS = {
    "Agent-OS-Kernel": {
        "commits": 150,
        "test_files": 50,
        "examples": 40,
        "docs": 5
    },
    "OmniMind": {
        "commits": 20,
        "test_files": 10,
        "examples": 10,
        "docs": 5
    }
}


class SuAgent:
    """项目监工"""
    
    def __init__(self):
        self.name = "SuAgent"
        self.last_report = None
        
    def get_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M UTC")
    
    def run_command(self, cmd: list, cwd: str = None) -> tuple:
        try:
            result = subprocess.run(
                cmd, cwd=cwd,
                capture_output=True, text=True, timeout=60
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except:
            return -1, "", "Error"
    
    def check_git_status(self, project_path: str) -> dict:
        status = {
            "branch": "unknown",
            "commits": 0,
            "last_commit": "unknown",
            "changes": False
        }
        
        code, stdout, _ = self.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path)
        if code == 0:
            status["branch"] = stdout
        
        code, stdout, _ = self.run_command(["git", "rev-list", "--count", "HEAD"], cwd=project_path)
        if code == 0:
            status["commits"] = int(stdout)
        
        code, stdout, _ = self.run_command(["git", "log", "-1", "--format=%H %s", "--no-merges"], cwd=project_path)
        if code == 0:
            parts = stdout.split(" ", 1)
            status["last_commit"] = parts[1] if len(parts) > 1 else stdout[:12]
        
        code, stdout, _ = self.run_command(["git", "status", "--porcelain"], cwd=project_path)
        status["changes"] = len(stdout) > 0
        
        return status
    
    def check_tests(self, project_path: str) -> dict:
        status = {"test_files": 0, "passed": 0, "failed": 0}
        
        tests_dir = os.path.join(project_path, "tests")
        if os.path.exists(tests_dir):
            status["test_files"] = len([f for f in os.listdir(tests_dir) if f.startswith("test_")])
        
        venv_python = os.path.join(project_path, "venv", "bin", "python3")
        if not os.path.exists(venv_python):
            venv_python = "python3"
        
        has_venv = os.path.exists(os.path.join(project_path, "venv"))
        
        if has_venv:
            code, stdout, stderr = self.run_command(
                [venv_python, "-m", "pytest", "tests/", "--tb=no", "-q"],
                cwd=project_path
            )
            
            match = re.search(r'(\d+)\s+passed', stdout)
            if match:
                status["passed"] = int(match.group(1))
            
            match = re.search(r'(\d+)\s+failed', stdout)
            if match:
                status["failed"] = int(match.group(1))
        
        return status
    
    def check_examples(self, project_path: str) -> dict:
        status = {"examples": 0}
        
        # 检查 examples/basic 目录
        basic_dir = os.path.join(project_path, "examples", "basic")
        if os.path.exists(basic_dir):
            examples = len([f for f in os.listdir(basic_dir) if f.endswith(".py")])
            status["examples"] = examples
        
        # 检查 demos 目录
        demos_dir = os.path.join(project_path, "demos")
        if os.path.exists(demos_dir):
            demos = len([f for f in os.listdir(demos_dir) if f.endswith(".py")])
            if status["examples"] > 0:
                status["examples"] += demos
            else:
                status["examples"] = demos
        
        return status
    
    def check_docs(self, project_path: str) -> dict:
        status = {"md_files": 0}
        
        docs_dir = os.path.join(project_path, "docs")
        if os.path.exists(docs_dir):
            status["md_files"] = len([f for f in os.listdir(docs_dir) if f.endswith(".md")])
        
        return status
    
    def calculate_progress(self, status: dict, project_name: str) -> float:
        """计算进度百分比"""
        goals = PROJECT_GOALS.get(project_name, {})
        if not goals:
            return 0.0
        
        weights = {
            "commits": 0.30,
            "test_files": 0.30,
            "examples": 0.25,
            "docs": 0.15
        }
        
        progress = 0.0
        
        # Commits (30%)
        if "commits" in goals:
            commits = status.get("git", {}).get("commits", 0)
            goal = goals["commits"]
            ratio = min(1.0, commits / goal) if goal > 0 else 1.0
            progress += weights["commits"] * ratio * 100
        
        # Test files (30%)
        if "test_files" in goals:
            test_files = status.get("tests", {}).get("test_files", 0)
            goal = goals["test_files"]
            ratio = min(1.0, test_files / goal) if goal > 0 else 1.0
            progress += weights["test_files"] * ratio * 100
        
        # Examples (25%)
        if "examples" in goals:
            examples = status.get("examples", {}).get("examples", 0)
            goal = goals["examples"]
            ratio = min(1.0, examples / goal) if goal > 0 else 1.0
            progress += weights["examples"] * ratio * 100
        
        # Docs (15%)
        if "docs" in goals:
            docs = status.get("docs", {}).get("md_files", 0)
            goal = goals["docs"]
            ratio = min(1.0, docs / goal) if goal > 0 else 1.0
            progress += weights["docs"] * ratio * 100
        
        return round(progress, 1)
    
    def get_project_status(self, project_name: str, project_path: str) -> dict:
        if not os.path.exists(project_path):
            return {"name": project_name, "exists": False}
        
        status = {
            "name": project_name,
            "exists": True,
            "git": self.check_git_status(project_path),
            "tests": self.check_tests(project_path),
            "examples": self.check_examples(project_path),
            "docs": self.check_docs(project_path)
        }
        
        status["progress"] = self.calculate_progress(status, project_name)
        
        return status
    
    def should_report(self) -> bool:
        if self.last_report is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_report).total_seconds()
        return elapsed >= REPORT_INTERVAL
    
    def format_progress_bar(self, progress: float, width: int = 20) -> str:
        filled = int(progress / 100 * width)
        bar = "#" * filled + "-" * (width - filled)
        return f"[{bar}] {progress:.1f}%"
    
    def format_report(self, all_status: dict) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  [PERCENT] SuAgent Progress Report")
        lines.append(f"  Time: {self.get_timestamp()}")
        lines.append("=" * 70)
        
        total_commits = 0
        total_tests = 0
        total_examples = 0
        total_progress = 0.0
        
        for name, status in all_status.items():
            if not status.get("exists", False):
                lines.append(f"\nXX {name}: Project not found")
                continue
            
            progress = status.get("progress", 0.0)
            total_progress += progress
            
            lines.append(f"\n## {name}")
            lines.append("-" * 50)
            
            git = status.get("git", {})
            tests = status.get("tests", {})
            examples = status.get("examples", {})
            docs = status.get("docs", {})
            
            # 进度条
            lines.append(f"\n  Target: {self.format_progress_bar(progress)}")
            
            # 目标
            goals = PROJECT_GOALS.get(name, {})
            if goals:
                lines.append(f"\n  Goals:")
                commits = git.get("commits", 0)
                lines.append(f"     Commits: {commits}/{goals.get('commits', '?')} (30%)")
                lines.append(f"     Tests: {tests.get('test_files', 0)}/{goals.get('test_files', '?')} (30%)")
                lines.append(f"     Examples: {examples.get('examples', 0)}/{goals.get('examples', '?')} (25%)")
                lines.append(f"     Docs: {docs.get('md_files', 0)}/{goals.get('docs', '?')} (15%)")
            
            lines.append(f"\n  Stats:")
            lines.append(f"     Branch: {git.get('branch', 'unknown')}")
            lines.append(f"     Commits: {git.get('commits', 0)}")
            lines.append(f"     Latest: {git.get('last_commit', 'unknown')}")
            
            if git.get("changes"):
                lines.append(f"     !! Uncommitted changes")
            
            lines.append(f"\n  Tests:")
            lines.append(f"     Files: {tests.get('test_files', 0)}")
            lines.append(f"     Passed: {tests.get('passed', 0)} OK")
            if tests.get('failed', 0) > 0:
                lines.append(f"     Failed: {tests.get('failed', 0)} FAIL")
            
            lines.append(f"\n  Examples: {examples.get('examples', 0)}")
            lines.append(f"  Docs: {docs.get('md_files', 0)}")
            
            total_commits += git.get("commits", 0)
            total_tests += tests.get("passed", 0)
            total_examples += examples.get("examples", 0)
        
        # 汇总
        avg_progress = total_progress / max(1, len([s for s in all_status.values() if s.get("exists", False)]))
        
        lines.append("\n" + "=" * 70)
        lines.append("  SUMMARY")
        lines.append("=" * 70)
        lines.append(f"\n  Overall: {self.format_progress_bar(avg_progress)}")
        lines.append(f"\n  Total Commits: {total_commits}")
        lines.append(f"  Total Tests Passed: {total_tests}")
        lines.append(f"  Total Examples: {total_examples}")
        
        # 状态评估
        lines.append("\n" + "-" * 50)
        lines.append("  Assessment:")
        
        if avg_progress >= 80:
            lines.append("  EXCELLENT! Project on track!")
        elif avg_progress >= 50:
            lines.append("  GOOD! Keep going!")
        elif avg_progress >= 30:
            lines.append("  NEEDS WORK! More to do!")
        else:
            lines.append("  URGENT! Speed up!")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def send_message(self, message: str):
        print(message)
        with open("/root/.openclaw/workspace/suagent_report.txt", "a") as f:
            f.write(f"\n\n{self.get_timestamp()}\n")
            f.write(message)
    
    def report(self):
        if not self.should_report():
            return
        
        self.last_report = datetime.now(timezone.utc)
        
        all_status = {}
        for name, path in PROJECTS.items():
            all_status[name] = self.get_project_status(name, path)
        
        report = self.format_report(all_status)
        self.send_message(report)
        
        return report
    
    def monitor_loop(self):
        print(f"\n{'=' * 70}")
        print(f"  XX SuAgent Monitor Started")
        print(f"  Projects: {', '.join(PROJECTS.keys())}")
        print(f"  Report interval: {REPORT_INTERVAL // 60} minutes")
        print(f"{'=' * 70}\n")
        
        self.report()
        
        while True:
            try:
                time.sleep(REPORT_INTERVAL)
                self.report()
            except KeyboardInterrupt:
                print("\n\nXX SuAgent Stopped")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)


def main():
    print("\n" + "=" * 70)
    print("  XX SuAgent - Project Monitor")
    print("  Reports progress every 5 minutes")
    print("=" * 70 + "\n")
    
    suagent = SuAgent()
    suagent.monitor_loop()


if __name__ == "__main__":
    main()
