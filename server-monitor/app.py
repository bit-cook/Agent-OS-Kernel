#!/usr/bin/env python3
"""
Server Monitor - Real-time hardware monitoring web interface
"""

import psutil
import time
import platform
from flask import Flask, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

def get_system_info():
    """Gather all system monitoring data"""
    uptime_seconds = time.time() - psutil.boot_time()
    uptime_days = uptime_seconds / 86400
    
    return {
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=None),
            "cores": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "temperature": get_cpu_temperature()
        },
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "usage_percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
            "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
            "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
            "usage_percent": psutil.disk_usage('/').percent
        },
        "network": get_network_stats(),
        "uptime": {
            "seconds": int(uptime_seconds),
            "formatted": format_uptime(uptime_seconds)
        },
        "system": {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version()
        }
    }

def get_cpu_temperature():
    """Get CPU temperature if available"""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current:
                        return round(entry.current, 1)
    except:
        pass
    return None

def get_network_stats():
    """Get network I/O statistics"""
    net_io = psutil.net_io_counters()
    return {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv,
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv
    }

def format_uptime(seconds):
    """Format uptime in human-readable format"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>服务器监控</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .system-info {
            text-align: center;
            color: #888;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }
        .refresh-info {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 0.8rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .card-title {
            font-size: 1.1rem;
            color: #00d9ff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-title::before {
            content: '';
            width: 4px;
            height: 20px;
            background: linear-gradient(180deg, #00d9ff, #00ff88);
            border-radius: 2px;
        }
        .stat {
            margin-bottom: 15px;
        }
        .stat-label {
            color: #888;
            font-size: 0.85rem;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
        }
        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        .cpu-bar { background: linear-gradient(90deg, #ff6b6b, #ffa500); }
        .memory-bar { background: linear-gradient(90deg, #4ecdc4, #44a08d); }
        .disk-bar { background: linear-gradient(90deg, #667eea, #764ba2); }
        
        .network-stats {
            font-size: 0.9rem;
        }
        .network-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .network-row:last-child {
            border-bottom: none;
        }
        .uptime-display {
            font-size: 2rem;
            font-weight: 700;
            text-align: center;
            margin: 20px 0;
            background: linear-gradient(90deg, #00ff88, #00d9ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .last-updated {
            text-align: center;
            color: #666;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🖥️ 服务器监控</h1>
            <div class="system-info" id="systemInfo">加载中...</div>
            <div class="refresh-info">每 2 秒自动刷新</div>
        </header>
        
        <div class="grid">
            <!-- CPU 卡片 -->
            <div class="card">
                <h2 class="card-title">CPU 处理器</h2>
                <div class="stat">
                    <div class="stat-label">使用率</div>
                    <div class="stat-value" id="cpuUsage">--%</div>
                    <div class="progress-bar">
                        <div class="progress-fill cpu-bar" id="cpuBar" style="width: 0%"></div>
                    </div>
                </div>
                <div class="stat">
                    <div class="stat-label">核心数</div>
                    <div class="stat-value" id="cpuCores">--</div>
                </div>
                <div class="stat">
                    <div class="stat-label">频率</div>
                    <div class="stat-value" id="cpuFreq">-- MHz</div>
                </div>
                <div class="stat" id="tempStat" style="display: none;">
                    <div class="stat-label">温度</div>
                    <div class="stat-value" id="cpuTemp">--°C</div>
                </div>
            </div>
            
            <!-- 内存 卡片 -->
            <div class="card">
                <h2 class="card-title">💾 内存</h2>
                <div class="stat">
                    <div class="stat-label">使用率</div>
                    <div class="stat-value" id="memUsage">--%</div>
                    <div class="progress-bar">
                        <div class="progress-fill memory-bar" id="memBar" style="width: 0%"></div>
                    </div>
                </div>
                <div class="stat">
                    <div class="stat-label">已用 / 总计</div>
                    <div class="stat-value" id="memUsed">-- / -- GB</div>
                </div>
                <div class="stat">
                    <div class="stat-label">可用</div>
                    <div class="stat-value" id="memAvail">-- GB</div>
                </div>
            </div>
            
            <!-- 磁盘 卡片 -->
            <div class="card">
                <h2 class="card-title">💿 磁盘</h2>
                <div class="stat">
                    <div class="stat-label">使用率</div>
                    <div class="stat-value" id="diskUsage">--%</div>
                    <div class="progress-bar">
                        <div class="progress-fill disk-bar" id="diskBar" style="width: 0%"></div>
                    </div>
                </div>
                <div class="stat">
                    <div class="stat-label">已用 / 总计</div>
                    <div class="stat-value" id="diskUsed">-- / -- GB</div>
                </div>
                <div class="stat">
                    <div class="stat-label">可用空间</div>
                    <div class="stat-value" id="diskFree">-- GB</div>
                </div>
            </div>
            
            <!-- 网络 卡片 -->
            <div class="card">
                <h2 class="card-title">🌐 网络</h2>
                <div class="network-stats">
                    <div class="network-row">
                        <span>发送流量</span>
                        <span id="netSent">--</span>
                    </div>
                    <div class="network-row">
                        <span>接收流量</span>
                        <span id="netRecv">--</span>
                    </div>
                    <div class="network-row">
                        <span>发送包数</span>
                        <span id="packetsSent">--</span>
                    </div>
                    <div class="network-row">
                        <span>接收包数</span>
                        <span id="packetsRecv">--</span>
                    </div>
                </div>
            </div>
            
            <!-- 运行时间 卡片 -->
            <div class="card">
                <h2 class="card-title">⏱️ 运行时间</h2>
                <div class="uptime-display" id="uptimeDisplay">--</div>
                <div class="stat">
                    <div class="stat-label">秒数</div>
                    <div class="stat-value" id="uptimeSeconds">--</div>
                </div>
            </div>
        </div>
        
        <div class="last-updated" id="lastUpdated">最后更新: --</div>
    </div>

    <script>
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function formatNumber(num) {
            return new Intl.NumberFormat().format(num);
        }

        function updateDisplay(data) {
            // CPU
            document.getElementById('cpuUsage').textContent = data.cpu.usage_percent + '%';
            document.getElementById('cpuBar').style.width = data.cpu.usage_percent + '%';
            document.getElementById('cpuCores').textContent = data.cpu.cores;
            document.getElementById('cpuFreq').textContent = Math.round(data.cpu.frequency) + ' MHz';
            
            if (data.cpu.temperature !== null) {
                document.getElementById('tempStat').style.display = 'block';
                document.getElementById('cpuTemp').textContent = data.cpu.temperature + '°C';
            }
            
            // Memory
            document.getElementById('memUsage').textContent = data.memory.usage_percent + '%';
            document.getElementById('memBar').style.width = data.memory.usage_percent + '%';
            document.getElementById('memUsed').textContent = data.memory.used_gb + ' / ' + data.memory.total_gb + ' GB';
            document.getElementById('memAvail').textContent = data.memory.available_gb + ' GB';
            
            // Disk
            document.getElementById('diskUsage').textContent = data.disk.usage_percent + '%';
            document.getElementById('diskBar').style.width = data.disk.usage_percent + '%';
            document.getElementById('diskUsed').textContent = data.disk.used_gb + ' / ' + data.disk.total_gb + ' GB';
            document.getElementById('diskFree').textContent = data.disk.free_gb + ' GB';
            
            // Network
            document.getElementById('netSent').textContent = formatBytes(data.network.bytes_sent);
            document.getElementById('netRecv').textContent = formatBytes(data.network.bytes_recv);
            document.getElementById('packetsSent').textContent = formatNumber(data.network.packets_sent);
            document.getElementById('packetsRecv').textContent = formatNumber(data.network.packets_recv);
            
            // Uptime
            document.getElementById('uptimeDisplay').textContent = data.uptime.formatted;
            document.getElementById('uptimeSeconds').textContent = formatNumber(data.uptime.seconds);
            
            // 系统信息
            document.getElementById('systemInfo').textContent = data.system.hostname + ' • ' + data.system.os;
            
            // 最后更新时间
            document.getElementById('lastUpdated').textContent = '最后更新: ' + new Date().toLocaleTimeString();
        }

        async function fetchData() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                updateDisplay(data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        // Initial load
        fetchData();
        
        // Auto-refresh every 2 seconds
        setInterval(fetchData, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Render the main monitoring page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    """Return JSON API with current stats"""
    return jsonify(get_system_info())

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)
