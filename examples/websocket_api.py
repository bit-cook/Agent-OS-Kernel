"""
WebSocket API 示例

展示如何使用 WebSocket 进行实时通信：
1. 实时状态推送
2. 实时 Agent 事件
3. 实时日志流
"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel import AgentOSKernel


class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.kernel = AgentOSKernel()
        self.connections = set()
        self.tasks = {}
    
    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        for ws in list(self.connections):
            try:
                await ws.send(json.dumps(message))
            except Exception:
                self.connections.discard(ws)
    
    async def handle_connection(self, websocket):
        """处理 WebSocket 连接"""
        self.connections.add(websocket)
        print(f"🔌 新连接: {len(self.connections)} 个活跃连接")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                response = await self.handle_message(data)
                await websocket.send(json.dumps(response))
        except Exception as e:
            print(f"❌ 连接错误: {e}")
        finally:
            self.connections.discard(websocket)
            print(f"🔌 断开连接: {len(self.connections)} 个活跃连接")
    
    async def handle_message(self, message: dict) -> dict:
        """处理消息"""
        action = message.get('action')
        
        if action == 'ping':
            return {'type': 'pong', 'timestamp': str(asyncio.get_event_loop().time())}
        
        elif action == 'create_agent':
            pid = self.kernel.spawn_agent(
                name=message.get('name', 'Agent'),
                task=message.get('task', 'Task'),
                priority=message.get('priority', 30)
            )
            return {'type': 'agent_created', 'pid': pid}
        
        elif action == 'list_agents':
            agents = list(self.kernel.scheduler.processes.values())
            return {
                'type': 'agent_list',
                'agents': [{'name': a.name, 'pid': a.pid, 'state': a.state.value} for a in agents]
            }
        
        elif action == 'get_status':
            status = self.kernel.get_openclaw_status()
            return {'type': 'status', 'data': status}
        
        elif action == 'execute_tool':
            result = self.kernel.tool_registry.execute(
                message.get('tool'),
                **message.get('params', {})
            )
            return {'type': 'tool_result', 'result': result}
        
        elif action == 'terminate_agent':
            pid = message.get('pid')
            self.kernel.scheduler.terminate_process(pid)
            return {'type': 'agent_terminated', 'pid': pid}
        
        return {'type': 'error', 'message': 'Unknown action'}
    
    async def start_status_stream(self, websocket):
        """启动状态流"""
        while websocket in self.connections:
            try:
                status = self.kernel.get_openclaw_status()
                await websocket.send(json.dumps({
                    'type': 'status_update',
                    'data': status,
                    'timestamp': str(asyncio.get_event_loop().time())
                }))
                await asyncio.sleep(5)  # 每5秒推送
            except Exception:
                break
    
    async def start_event_stream(self, websocket):
        """启动事件流"""
        while websocket in self.connections:
            try:
                # 检查 Agent 变化
                agents = list(self.kernel.scheduler.processes.values())
                for agent in agents:
                    if hasattr(agent, '_last_state'):
                        if agent.state != agent._last_state:
                            await websocket.send(json.dumps({
                                'type': 'agent_event',
                                'event': 'state_change',
                                'agent': agent.name,
                                'old_state': agent._last_state.value,
                                'new_state': agent.state.value
                            }))
                            agent._last_state = agent.state
                await asyncio.sleep(1)
            except Exception:
                break


async def main():
    """WebSocket 服务器主函数"""
    print("=" * 60)
    print("WebSocket API 服务器示例")
    print("=" * 60)
    print("\n使用方法:")
    print("1. 连接: ws://localhost:8765")
    print("2. 发送消息:")
    print('   {"action": "ping"}')
    print('   {"action": "create_agent", "name": "Test", "task": "Hello"}')
    print('   {"action": "list_agents"}')
    print('   {"action": "get_status"}')
    print('   {"action": "execute_tool", "tool": "calculator", "params": {"expression": "2+2"}}')
    print("\n启动服务器...")
    
    # 使用 asyncio 实现简单 WebSocket 服务器
    # 实际生产环境建议使用 websockets 库或 FastAPI + WebSocket
    
    manager = WebSocketManager()
    
    # 模拟 WebSocket 处理
    print("\n✅ WebSocket 管理器已启动")
    print("📡 监听连接中...")
    
    # 返回管理器供外部使用
    return manager


def demo_websocket_client():
    """演示 WebSocket 客户端"""
    print("\n" + "=" * 60)
    print("WebSocket 客户端示例")
    print("=" * 60)
    
    # 使用 websockets 库的示例代码
    example_code = '''
import asyncio
import json
import websockets

async def client():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as ws:
        # Ping
        await ws.send(json.dumps({"action": "ping"}))
        response = await ws.recv()
        print(f"📨 Pong: {response}")
        
        # 创建 Agent
        await ws.send(json.dumps({
            "action": "create_agent",
            "name": "DemoAgent",
            "task": "Demonstration task",
            "priority": 50
        }))
        response = await ws.recv()
        print(f"📨 Agent 创建: {response}")
        
        # 获取状态
        await ws.send(json.dumps({"action": "get_status"}))
        response = await ws.recv()
        print(f"📨 状态: {response}")

asyncio.run(client())
'''
    print(example_code)


if __name__ == "__main__":
    # 启动管理器
    manager = asyncio.run(main())
    
    # 显示客户端示例
    demo_websocket_client()
