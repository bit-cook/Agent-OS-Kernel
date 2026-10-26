# -*- coding: utf-8 -*-
import os

for root, dirs, files in os.walk("agent_os_kernel"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "rb") as f:
                content = f.read()
            try:
                content.decode("ascii")
            except UnicodeDecodeError:
                # 包含非ASCII字符
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                if not text.startswith("# -*- coding"):
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("# -*- coding: utf-8 -*-\n" + text)
                    print("Fixed: " + path)
