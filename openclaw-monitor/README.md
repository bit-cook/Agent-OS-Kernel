# OpenClaw 监控面板 v2.0

一个功能完整的 Flask Web 应用，实时监控 OpenClaw 系统。

## ✨ 新增功能 v2.0

- 📈 **性能监控** - CPU、内存、磁盘实时图表
- 📊 **历史趋势** - 滚动记录性能数据
- 🔔 **告警系统** - 可配置阈值告警
- ⚡ **快速操作** - 重启 Agent/通道/网关
- 🎨 **主题切换** - 深色/浅色模式
- 📱 **响应式设计** - 完美支持移动端
- 🤖 **会话日志** - 查看 Agent 会话

## 🚀 快速开始

```bash
cd /root/.openclaw/workspace/openclaw-monitor
pip install -r requirements.txt

# 开发模式
python app.py

# 生产模式 (推荐)
gunicorn -w 4 -b 0.0.0.0:8888 app:app
```

## 📊 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 完整状态 |
| `/api/health` | GET | 健康检查 |
| `/api/history` | GET | 历史数据 |
| `/api/alerts` | GET | 告警列表 |
| `/api/system` | GET | 系统指标 |
| `/api/actions/restart/agent/<name>` | GET | 重启 Agent |
| `/api/actions/restart/channel/<name>` | GET | 重启通道 |
| `/api/actions/restart/gateway` | GET | 重启网关 |

## 🛠️ 配置

环境变量:
- `OPENCLAW_MONITOR_PORT` - 监听端口 (默认 8888)
- `OPENCLAW_MONITOR_HOST` - 监听地址 (默认 0.0.0.0)
- `OPENCLAW_REFRESH_INTERVAL` - 刷新间隔 (默认 30s)
- `OPENCLAW_HISTORY_SIZE` - 历史记录数 (默认 100)

## 📱 访问

- **Web**: http://your-server:8888
- **API**: http://your-server:8888/api/status
