#!/usr/bin/env python3
"""
OpenClaw Real-Time Monitoring Dashboard v2.0

A comprehensive Flask web application for monitoring OpenClaw system.
Features:
- Real-time status monitoring
- Performance metrics (CPU, Memory, Disk, Network)
- Historical data tracking
- Alert system with configurable thresholds
- Quick actions (restart agent/channel)
- Session logs viewer
- Dark/Light theme support
- Responsive mobile-friendly UI
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from threading import Lock, Thread
from collections import deque
from flask import Flask, render_template, jsonify, request, abort

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ============== Configuration ==============
CONFIG = {
    'port': int(os.environ.get('OPENCLAW_MONITOR_PORT', 8888)),
    'host': os.environ.get('OPENCLAW_MONITOR_HOST', '0.0.0.0'),
    'cache_duration': int(os.environ.get('OPENCLAW_MONITOR_CACHE', 5)),
    'refresh_interval': int(os.environ.get('OPENCLAW_MONITOR_REFRESH', 30)),
    'history_size': int(os.environ.get('OPENCLAW_HISTORY_SIZE', 100)),
    'alert_check_interval': int(os.environ.get('OPENCLAW_ALERT_INTERVAL', 60)),
}

# ============== Data Storage ==============
# Cache for status data
status_cache = {
    'data': None,
    'timestamp': 0,
    'error': None
}
cache_lock = Lock()

# Historical data (rolling window)
history_data = {
    'cpu': deque(maxlen=CONFIG['history_size']),
    'memory': deque(maxlen=CONFIG['history_size']),
    'sessions': deque(maxlen=CONFIG['history_size']),
    'gateway_latency': deque(maxlen=CONFIG['history_size']),
    'timestamps': deque(maxlen=CONFIG['history_size'])
}

# System metrics cache
system_metrics = {
    'cpu_percent': 0,
    'memory_percent': 0,
    'disk_percent': 0,
    'load_avg': (0, 0, 0),
    'boot_time': 0,
    'uptime_seconds': 0
}

# Alerts storage
alerts = []
alert_lock = Lock()

# ============== Alert Configuration ==============
DEFAULT_ALERTS = [
    {'name': 'High CPU', 'metric': 'cpu_percent', 'threshold': 80, 'condition': '>', 'enabled': True, 'message': 'CPU usage is high'},
    {'name': 'High Memory', 'metric': 'memory_percent', 'threshold': 85, 'condition': '>', 'enabled': True, 'message': 'Memory usage is high'},
    {'name': 'Gateway Down', 'metric': 'gateway_reachable', 'threshold': 0, 'condition': '==', 'enabled': True, 'message': 'Gateway is not reachable'},
    {'name': 'Agent Error', 'metric': 'agent_error', 'threshold': 0, 'condition': '>', 'enabled': True, 'message': 'Agent has errors'},
]

alerts_config = DEFAULT_ALERTS.copy()

# ============== Helper Functions ==============
def execute_openclaw_command(args: list, timeout: int = 30) -> tuple[str, str, int]:
    """Execute openclaw command and return stdout, stderr, returncode."""
    try:
        cmd = ['openclaw'] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return '', 'Command timed out', 1
    except FileNotFoundError:
        return '', 'openclaw command not found', 1
    except Exception as e:
        return '', str(e), 1


def get_system_metrics():
    """Get system performance metrics."""
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        load_avg = psutil.getloadavg()
        
        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Boot time and uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'load_avg': load_avg,
            'boot_time': boot_time,
            'uptime_seconds': uptime_seconds,
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
        }
    except Exception as e:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'load_avg': (0, 0, 0),
            'boot_time': 0,
            'uptime_seconds': 0,
            'error': str(e)
        }


def check_alerts(metrics: dict, sys_metrics: dict):
    """Check metrics against alert thresholds."""
    new_alerts = []
    current_time = datetime.utcnow().isoformat()
    
    for alert in alerts_config:
        if not alert['enabled']:
            continue
            
        value = None
        if alert['metric'] in sys_metrics:
            value = sys_metrics[alert['metric']]
        elif alert['metric'] == 'gateway_reachable':
            value = 1 if metrics.get('gateway_reachable', False) else 0
        elif alert['metric'] == 'agent_error':
            value = len(metrics.get('errors', []))
            
        if value is None:
            continue
            
        triggered = False
        if alert['condition'] == '>' and value > alert['threshold']:
            triggered = True
        elif alert['condition'] == '<' and value < alert['threshold']:
            triggered = True
        elif alert['condition'] == '==' and value == alert['threshold']:
            triggered = True
        elif alert['condition'] == '>=' and value >= alert['threshold']:
            triggered = True
        elif alert['condition'] == '<=' and value <= alert['threshold']:
            triggered = True
            
        if triggered:
            new_alerts.append({
                'time': current_time,
                'name': alert['name'],
                'message': alert['message'],
                'value': value,
                'threshold': alert['threshold'],
                'severity': 'critical' if alert['threshold'] > 70 else 'warning'
            })
    
    with alert_lock:
        alerts.extend(new_alerts)
        # Keep only last 100 alerts
        if len(alerts) > 100:
            alerts[:] = alerts[-100:]
    
    return new_alerts


def parse_table_output(output: str) -> dict:
    """Parse OpenClaw table-style output into structured data."""
    result = {
        'raw': output,
        'overview': {},
        'channels': [],
        'agents': [],
        'diagnosis': [],
        'warnings': [],
        'errors': [],
        'gateway': {},
        'system': {}
    }
    
    if not output or not output.strip():
        return result
    
    lines = output.strip().split('\n')
    
    # Parse Overview table
    overview_match = False
    for line in lines:
        if '┌─────────────────┬' in line:
            overview_match = True
            continue
        if overview_match and '└─────────────────┴' in line:
            overview_match = False
            continue
        if overview_match and '│' in line:
            parts = [p.strip() for p in line.split('│')[1:-1]]
            if len(parts) >= 2:
                key = parts[0].strip()
                value = parts[1].strip()
                result['overview'][key] = value
    
    # Parse Channels table
    channels_match = False
    header_found = False
    for line in lines:
        if '┌──────────┬─────────┬' in line:
            channels_match = True
            continue
        if channels_match and '└──────────┴─────────┴' in line:
            channels_match = False
            continue
        if channels_match:
            if '│' in line and not header_found:
                header_found = True
                continue
            if header_found and '│' in line:
                parts = [p.strip() for p in line.split('│')[1:-1]]
                if len(parts) >= 4:
                    channel = {
                        'name': parts[0],
                        'enabled': parts[1],
                        'state': parts[2],
                        'detail': parts[3]
                    }
                    result['channels'].append(channel)
    
    # Parse Agents table
    agents_match = False
    header_found = False
    for line in lines:
        if '┌────────────┬───────────┬' in line:
            agents_match = True
            continue
        if agents_match and '└────────────┴───────────┴' in line:
            agents_match = False
            continue
        if agents_match:
            if '│' in line and not header_found:
                header_found = True
                continue
            if header_found and '│' in line:
                parts = [p.strip() for p in line.split('│')[1:-1]]
                if len(parts) >= 5:
                    agent = {
                        'name': parts[0],
                        'bootstrap': parts[1],
                        'sessions': parts[2],
                        'active': parts[3],
                        'store': parts[4]
                    }
                    result['agents'].append(agent)
    
    # Parse diagnosis sections
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('✓') or stripped.startswith('✅'):
            result['diagnosis'].append(stripped[1:].strip() if len(stripped) > 1 else 'Check passed')
        elif stripped.startswith('!') or stripped.startswith('⚠️'):
            result['warnings'].append(stripped.lstrip('!⚠️ ').strip())
        elif 'error' in stripped.lower() or stripped.startswith('❌'):
            result['errors'].append(stripped.lstrip('❌errorERROR: ').strip())
    
    return result


def extract_metrics(data: dict) -> dict:
    """Extract key metrics from parsed OpenClaw data."""
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'unknown',
        'overall_health': 'healthy',
        'version': '',
        'os': '',
        'node': '',
        'gateway_status': 'unknown',
        'gateway_reachable': False,
        'gateway_latency': None,
        'channels': [],
        'agents': [],
        'total_sessions': 0,
        'diagnosis': [],
        'warnings': [],
        'errors': [],
        'security_status': '',
    }
    
    overview = data.get('overview', {})
    metrics['version'] = overview.get('Version', '')
    metrics['os'] = overview.get('OS', '')
    metrics['node'] = overview.get('Node', '')
    
    # Parse Gateway
    gateway_str = overview.get('Gateway', '')
    if 'reachable' in gateway_str.lower():
        metrics['gateway_reachable'] = True
        latency_match = re.search(r'(\d+)ms', gateway_str)
        if latency_match:
            metrics['gateway_latency'] = int(latency_match.group(1))
    
    # Channels
    for channel in data.get('channels', []):
        metrics['channels'].append({
            'name': channel.get('name', ''),
            'enabled': channel.get('enabled', 'OFF') == 'ON',
            'state': channel.get('state', ''),
            'detail': channel.get('detail', ''),
            'status': 'ok' if channel.get('state', '') == 'OK' else 'warning'
        })
    
    # Agents
    total_sessions = 0
    for agent in data.get('agents', []):
        try:
            sessions = int(agent.get('sessions', 0))
            total_sessions += sessions
        except:
            pass
        metrics['agents'].append({
            'name': agent.get('name', ''),
            'bootstrap': agent.get('bootstrap', ''),
            'sessions': agent.get('sessions', '0'),
            'active': agent.get('active', ''),
            'store': agent.get('store', ''),
            'status': 'ok' if agent.get('bootstrap') == 'OK' else 'warning'
        })
    
    metrics['total_sessions'] = total_sessions
    metrics['diagnosis'] = data.get('diagnosis', [])
    metrics['warnings'] = data.get('warnings', [])
    metrics['errors'] = data.get('errors', [])
    
    # Overall status
    if metrics['errors']:
        metrics['status'] = 'error'
        metrics['overall_health'] = 'error'
    elif metrics['warnings']:
        metrics['status'] = 'degraded'
        metrics['overall_health'] = 'warning'
    elif metrics['gateway_reachable']:
        metrics['status'] = 'running'
        metrics['overall_health'] = 'healthy'
    
    return metrics


def update_history(metrics: dict, sys_metrics: dict):
    """Update historical data."""
    timestamp = datetime.utcnow().isoformat()
    
    with cache_lock:
        history_data['cpu'].append(sys_metrics.get('cpu_percent', 0))
        history_data['memory'].append(sys_metrics.get('memory_percent', 0))
        history_data['sessions'].append(metrics.get('total_sessions', 0))
        history_data['gateway_latency'].append(metrics.get('gateway_latency', 0))
        history_data['timestamps'].append(timestamp)


def get_openclaw_status() -> dict:
    """Get current OpenClaw status."""
    global status_cache, system_metrics
    
    current_time = time.time()
    
    with cache_lock:
        if status_cache['data'] is not None and \
           current_time - status_cache['timestamp'] < CONFIG['cache_duration']:
            return status_cache['data']
        
        stdout, stderr, returncode = execute_openclaw_command(['status', '--all'])
        
        if returncode != 0 or not stdout:
            error_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'overall_health': 'error',
                'error': stderr or 'Failed to get OpenClaw status',
                'channels': [],
                'agents': [],
                'diagnosis': [],
                'warnings': ['无法获取 OpenClaw 状态'],
                'errors': [stderr or 'Unknown error'],
                'gateway_reachable': False,
                'total_sessions': 0
            }
            status_cache['data'] = error_data
            status_cache['timestamp'] = current_time
            return error_data
        
        try:
            parsed = parse_table_output(stdout)
            metrics = extract_metrics(parsed)
            
            # Get system metrics
            sys_metrics = get_system_metrics()
            system_metrics.update(sys_metrics)
            
            # Update history
            update_history(metrics, sys_metrics)
            
            # Check alerts
            check_alerts(metrics, sys_metrics)
            
            # Add system metrics to response
            metrics['system'] = sys_metrics
            
            status_cache['data'] = metrics
            status_cache['timestamp'] = current_time
            return metrics
        except Exception as e:
            error_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'parse_error',
                'overall_health': 'error',
                'error': str(e),
                'channels': [],
                'agents': [],
                'diagnosis': [],
                'warnings': [],
                'errors': ['解析错误: ' + str(e)],
                'gateway_reachable': False,
                'total_sessions': 0
            }
            status_cache['data'] = error_data
            status_cache['timestamp'] = current_time
            return error_data


# ============== Routes ==============
@app.route('/')
def index():
    """Serve the main dashboard page."""
    theme = request.cookies.get('theme', 'dark')
    return render_template('index.html', 
                         refresh_interval=CONFIG['refresh_interval'],
                         theme=theme)


@app.route('/api/status')
def api_status():
    """API endpoint to get OpenClaw status."""
    data = get_openclaw_status()
    return jsonify(data)


@app.route('/api/health')
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'openclaw-monitor',
        'version': '2.0.0'
    })


@app.route('/api/config')
def api_config():
    """Get monitor configuration."""
    return jsonify({
        'refresh_interval': CONFIG['refresh_interval'],
        'cache_duration': CONFIG['cache_duration'],
        'version': '2.0.0'
    })


@app.route('/api/history')
def api_history():
    """Get historical data for charts."""
    return jsonify({
        'cpu': list(history_data['cpu']),
        'memory': list(history_data['memory']),
        'sessions': list(history_data['sessions']),
        'gateway_latency': list(history_data['gateway_latency']),
        'timestamps': list(history_data['timestamps'])
    })


@app.route('/api/alerts')
def api_alerts():
    """Get alerts."""
    with alert_lock:
        return jsonify({
            'alerts': alerts[-50:],  # Last 50 alerts
            'count': len(alerts)
        })


@app.route('/api/alerts/config', methods=['GET', 'POST'])
def api_alerts_config():
    """Get or update alert configuration."""
    global alerts_config
    
    if request.method == 'POST':
        data = request.json
        alerts_config = data.get('alerts', alerts_config)
        return jsonify({'status': 'ok', 'alerts': alerts_config})
    
    return jsonify({'alerts': alerts_config})


@app.route('/api/actions/restart/agent/<agent_name>')
def api_restart_agent(agent_name):
    """Restart an agent."""
    stdout, stderr, code = execute_openclaw_command(['agents', 'restart', agent_name])
    return jsonify({
        'success': code == 0,
        'stdout': stdout,
        'stderr': stderr
    })


@app.route('/api/actions/restart/channel/<channel_name>')
def api_restart_channel(channel_name):
    """Restart a channel."""
    stdout, stderr, code = execute_openclaw_command(['channels', 'restart', channel_name])
    return jsonify({
        'success': code == 0,
        'stdout': stdout,
        'stderr': stderr
    })


@app.route('/api/actions/restart/gateway')
def api_restart_gateway():
    """Restart gateway."""
    stdout, stderr, code = execute_openclaw_command(['gateway', 'restart'])
    return jsonify({
        'success': code == 0,
        'stdout': stdout,
        'stderr': stderr
    })


@app.route('/api/logs/sessions/<agent_name>')
def api_session_logs(agent_name):
    """Get session logs for an agent."""
    log_path = f"~/.openclaw/agents/{agent_name}/sessions/sessions.json"
    
    stdout, stderr, code = execute_openclaw_command(['sessions', 'list', '--json'], timeout=10)
    
    if code == 0 and stdout:
        try:
            return jsonify({
                'agent': agent_name,
                'logs': json.loads(stdout)
            })
        except json.JSONDecodeError:
            return jsonify({
                'agent': agent_name,
                'raw': stdout,
                'error': 'Failed to parse JSON'
            })
    
    return jsonify({
        'agent': agent_name,
        'error': stderr or 'Failed to get logs',
        'raw': stdout
    })


@app.route('/api/system')
def api_system():
    """Get system metrics."""
    return jsonify(system_metrics)


@app.route('/favicon.ico')
def favicon():
    """Serve favicon."""
    return '', 204


def main():
    """Main entry point."""
    print(f"🚀 Starting OpenClaw Monitor v2.0.0")
    print(f"   Listening on {CONFIG['host']}:{CONFIG['port']}")
    print(f"   Refresh interval: {CONFIG['refresh_interval']}s")
    print(f"   API: http://{CONFIG['host']}:{CONFIG['port']}/api/status")
    print(f"   Web: http://{CONFIG['host']}:{CONFIG['port']}/")
    
    app.run(host=CONFIG['host'], port=CONFIG['port'], debug=False)


if __name__ == '__main__':
    main()
