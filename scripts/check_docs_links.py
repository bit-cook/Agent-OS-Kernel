#!/usr/bin/env python3
"""Docs link check - 文档内链完整性检查

CI docs job 使用：校验 docs/ 与 README 中引用的相对路径链接全部存在，
防止文档超前于代码（审计 P1-03 / P2-03）。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 匹配 markdown 内链 [text](path)，忽略 http(s)/mailto/锚点
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#][^)]*)\)")

SCAN_DIRS = ["docs", "."]
SCAN_FILES = ["README.md", "README_EN.md", "CHANGELOG.md"]


def check_file(path: str) -> list:
    problems = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return problems

    base_dir = os.path.dirname(os.path.abspath(path))
    for match in LINK_RE.finditer(content):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # 去掉锚点
        target_path = target.split("#")[0]
        if not target_path:
            continue
        resolved = os.path.normpath(os.path.join(base_dir, target_path))
        if not os.path.exists(resolved):
            problems.append(f"{os.path.relpath(path, ROOT)}: broken link -> {target}")
    return problems


def main() -> int:
    files = []
    for d in SCAN_DIRS:
        full = os.path.join(ROOT, d)
        if not os.path.isdir(full):
            continue
        for name in os.listdir(full):
            if name.endswith(".md"):
                files.append(os.path.join(full, name))
    for name in SCAN_FILES:
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            files.append(p)

    all_problems = []
    for f in sorted(set(files)):
        all_problems.extend(check_file(f))

    if all_problems:
        print(f"docs link check FAILED ({len(all_problems)} broken links):")
        for p in all_problems:
            print(f"  {p}")
        return 1
    print(f"docs link check OK ({len(set(files))} markdown files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
