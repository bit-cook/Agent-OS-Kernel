# GitHub 账户配置指南

## 📝 步骤 1: 创建 GitHub 账户

1. 打开 https://github.com/signup
2. 使用你的邮箱注册账户
3. 完成邮箱验证

---

## 🔧 步骤 2: 配置 Git (在服务器/本地运行)

```bash
cd Agent-OS-Kernel

# 设置你的 GitHub 邮箱 (必须与 GitHub 账户邮箱一致)
git config user.email "your-email@example.com"

# 设置你的 GitHub 用户名
git config user.name "your-github-username"

# 确认配置
git config --list | grep user
```

---

## 🔑 步骤 3: 创建 Personal Access Token

1. 打开 GitHub Settings
   👉 https://github.com/settings/tokens

2. 点击 "Generate new token" (Classic)

3. 设置:
   - **Note**: "Agent-OS-Kernel Push"
   - **Expiration**: 选择 "No expiration" 或 30天
   - **Scopes**: ✅ 勾选 `repo` (完整仓库权限)

4. 点击 "Generate token"

5. **⚠️ 重要**: 复制并保存好 Token!
   ```
   ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

---

## 🚀 步骤 4: 推送代码

### 方式 A: 首次推送 (需要输入 Token)

```bash
cd Agent-OS-Kernel

# 推送到 GitHub
git push origin main

# 当提示输入密码时:
# Username: 你的 GitHub 用户名
# Password: 粘贴你的 Personal Access Token (不是密码!)
```

### 方式 B: 保存 Token (避免每次输入)

```bash
# Linux/Mac
git config --global credential.helper store

# 第一次推送时输入 Token，之后会自动保存
```

### 方式 C: 使用环境变量 (推荐)

```bash
# 设置 Token 环境变量
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 配置 URL
git remote set-url origin https://${GITHUB_TOKEN}@github.com/bit-cook/Agent-OS-Kernel.git

# 推送
git push origin main
```

---

## ✅ 验证推送成功

```bash
# 查看仓库
open https://github.com/bit-cook/Agent-OS-Kernel

# 查看提交历史
open https://github.com/bit-cook/Agent-OS-Kernel/commits/main
```

---

## 💡 常见问题

### Q: 提示 "Permission denied"
A: 检查 Token 是否正确创建，是否有 `repo` 权限

### Q: 提示 "Authentication failed"
A: 用户名或 Token 错误，重新输入 Token

### Q: Token 忘记了
A: 重新生成一个新的 Token

---

## 📦 当前 Git 状态

```
Remote: https://github.com/bit-cook/Agent-OS-Kernel
Branch: main
Commit: fefe725 - feat: 中国模型支持 + AIOS 参考架构 + MCP 协议

待推送文件: 64 个文件, 11725 行新增
```

---

## 🎯 快速命令

```bash
# 1. 进入项目目录
cd Agent-OS-Kernel

# 2. 配置 Git (替换为你的信息)
git config user.email "your-email@example.com"
git config user.name "your-username"

# 3. 推送
git push origin main

# 4. 输入:
# Username: 你的 GitHub 用户名
# Password: 粘贴 Personal Access Token
```

---

创建好 GitHub 账户和 Token 后，告诉我，我来帮你执行推送！ 🚀
