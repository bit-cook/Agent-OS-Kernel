# ⚠️ 权限问题

## 问题
XieClaw 账户没有权限推送到 `bit-cook/Agent-OS-Kernel` 仓库。

---

## 💡 解决方案

### 方案 A: 成为仓库协作者 (推荐)

**bit-cook 需要做:**

1. 打开仓库设置
   👉 https://github.com/bit-cook/Agent-OS-Kernel/settings

2. 点击 "Collaborators"

3. 点击 "Add people"

4. 输入 `XieClaw`

5. 发送邀请

**XieClaw 需要做:**

1. 打开邀请链接 (邮件或 GitHub 通知)
2. 点击 "Accept invitation"

---

### 方案 B: Fork 到自己账户

```bash
# 1. 在 GitHub 网站上点击 "Fork" 按钮
#    https://github.com/bit-cook/Agent-OS-Kernel/fork

# 2. Fork 到 XieClaw 账户

# 3. 修改 remote
git remote set-url origin https://github.com/XieClaw/Agent-OS-Kernel.git

# 4. 推送到自己的 Fork
git push origin main

# 5. 创建 Pull Request
#    https://github.com/bit-cook/Agent-OS-Kernel/compare/main...XieClaw:main
```

---

### 方案 C: bit-cook 直接推送

如果不想添加协作者，可以让 `bit-cook` 账户直接推送更新。

---

## 📝 建议

**推荐方案 A**: 让 bit-cook 把 XieClaw 添加为协作者，这是最简单的方式。

需要我帮你生成邀请链接吗？
