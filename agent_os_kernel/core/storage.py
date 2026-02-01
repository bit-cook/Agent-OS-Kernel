# -*- coding: utf-8 -*-
"""
Storage Layer - 存储层

PostgreSQL 在 Agent OS 中的五重角色：
1. 长期记忆存储（海马体）：对话历史、学到的知识、用户偏好
2. 状态持久化（硬盘）：Checkpoint/快照、任务状态、恢复点
3. 向量索引（页表）：语义检索、相似度匹配、Context 换入决策
4. 协调服务（IPC）：分布式锁、任务队列、事件通知
5. 审计日志（黑匣子）：所有操作的不可篡改记录、合规、可重放

核心洞察（来自冯若航《AI Agent 的操作系统时刻》）：
- 数据库是确定性最高的商业机会
- PostgreSQL 不仅是存储，更有潜力成为 Runtime
- 统一的存储层可以避免维护多套系统与胶水组件
"""

import json
import time
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from contextlib import contextmanager


logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """
    存储后端抽象基类
    
    定义 PostgreSQL 五重角色的标准接口
    """
    
    # ========== 1. 长期记忆存储 ==========
    @abstractmethod
    def save_memory(self, agent_pid: str, memory_type: str, 
                   content: str, metadata: Optional[Dict] = None) -> str:
        """保存长期记忆"""
        pass
    
    @abstractmethod
    def retrieve_memories(self, agent_pid: str, memory_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """检索长期记忆"""
        pass
    
    # ========== 2. 状态持久化 ==========
    @abstractmethod
    def save_process(self, process: Any):
        """保存进程状态"""
        pass
    
    @abstractmethod
    def load_process(self, pid: str) -> Optional[Any]:
        """加载进程状态"""
        pass
    
    @abstractmethod
    def save_checkpoint(self, agent_pid: str, process_state: Dict,
                       context_pages: List[Dict], description: str = "") -> str:
        """保存检查点"""
        pass
    
    @abstractmethod
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """加载检查点"""
        pass
    
    @abstractmethod
    def list_checkpoints(self, agent_pid: str) -> List[Dict]:
        """列出所有检查点"""
        pass
    
    # ========== 3. 向量索引 ==========
    @abstractmethod
    def save_context_page(self, page: Any) -> str:
        """保存上下文页面（用于 swap out）"""
        pass
    
    @abstractmethod
    def load_context_page(self, page_id: str) -> Optional[Any]:
        """加载上下文页面（用于 swap in）"""
        pass
    
    @abstractmethod
    def semantic_search(self, agent_pid: str, query_embedding: List[float],
                       limit: int = 10, threshold: float = 0.7) -> List[Dict]:
        """语义搜索（向量相似度）"""
        pass
    
    @abstractmethod
    def find_similar_memories(self, agent_pid: str, content: str,
                             limit: int = 5) -> List[Dict]:
        """查找相似记忆"""
        pass
    
    # ========== 4. 协调服务 ==========
    @abstractmethod
    @contextmanager
    def acquire_lock(self, lock_name: str, timeout: float = 30.0):
        """获取分布式锁"""
        pass
    
    @abstractmethod
    def enqueue_task(self, queue_name: str, task: Dict) -> str:
        """入队任务"""
        pass
    
    @abstractmethod
    def dequeue_task(self, queue_name: str) -> Optional[Dict]:
        """出队任务"""
        pass
    
    @abstractmethod
    def publish_event(self, channel: str, message: Dict):
        """发布事件"""
        pass
    
    @abstractmethod
    def subscribe_events(self, channel: str, callback: Callable):
        """订阅事件"""
        pass
    
    # ========== 5. 审计日志 ==========
    @abstractmethod
    def log_action(self, agent_pid: str, action_type: str,
                   input_data: Dict, output_data: Dict,
                   reasoning: str = "", metadata: Optional[Dict] = None):
        """记录审计日志"""
        pass
    
    @abstractmethod
    def get_audit_trail(self, agent_pid: str, limit: int = 100) -> List[Dict]:
        """获取审计追踪"""
        pass
    
    @abstractmethod
    def replay_actions(self, agent_pid: str, 
                      from_checkpoint: Optional[str] = None) -> List[Dict]:
        """回放操作（用于调试和审计）"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭存储连接"""
        pass


class PostgreSQLStorage(StorageBackend):
    """
    PostgreSQL 存储后端 - 实现五重角色
    
    使用 PostgreSQL + pgvector 扩展实现完整的 Agent 存储层。
    这是生产环境推荐的后端。
    
    数据库 Schema：
    - agent_processes: 进程状态表
    - checkpoints: 检查点表
    - context_pages: 上下文页面表（带向量）
    - long_term_memory: 长期记忆表
    - audit_logs: 审计日志表
    - task_queues: 任务队列表
    - distributed_locks: 分布式锁表
    """
    
    CREATE_TABLES_SQL = """
    -- 1. 进程状态表（状态持久化）
    CREATE TABLE IF NOT EXISTS agent_processes (
        pid UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        state VARCHAR(50) NOT NULL,
        priority INTEGER DEFAULT 50,
        token_usage BIGINT DEFAULT 0,
        api_calls INTEGER DEFAULT 0,
        execution_time FLOAT DEFAULT 0,
        cpu_time FLOAT DEFAULT 0,
        context_snapshot JSONB,
        checkpoint_id UUID,
        parent_pid UUID,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_run TIMESTAMPTZ,
        started_at TIMESTAMPTZ,
        terminated_at TIMESTAMPTZ,
        error_count INTEGER DEFAULT 0,
        last_error TEXT,
        metadata JSONB DEFAULT '{}',
        CONSTRAINT valid_state CHECK (state IN ('ready', 'running', 'waiting', 'suspended', 'terminated', 'error'))
    );
    
    -- 2. 检查点表（状态持久化）
    CREATE TABLE IF NOT EXISTS checkpoints (
        checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_pid UUID REFERENCES agent_processes(pid) ON DELETE CASCADE,
        process_state JSONB NOT NULL,
        context_pages JSONB DEFAULT '[]',
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        description TEXT,
        tags TEXT[],
        parent_checkpoint UUID,
        version INTEGER DEFAULT 1
    );
    
    -- 3. 上下文页面表（向量索引 + swap backing store）
    CREATE TABLE IF NOT EXISTS context_pages (
        page_id UUID PRIMARY KEY,
        agent_pid UUID REFERENCES agent_processes(pid) ON DELETE CASCADE,
        content TEXT NOT NULL,
        tokens INTEGER DEFAULT 0,
        importance_score FLOAT DEFAULT 0.5,
        page_type VARCHAR(50) DEFAULT 'general',
        status VARCHAR(20) DEFAULT 'swapped',
        embedding VECTOR(1536),
        access_count INTEGER DEFAULT 0,
        last_accessed TIMESTAMPTZ DEFAULT NOW(),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        metadata JSONB DEFAULT '{}'
    );
    
    -- 4. 长期记忆表（海马体）
    CREATE TABLE IF NOT EXISTS long_term_memory (
        memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_pid UUID REFERENCES agent_processes(pid) ON DELETE CASCADE,
        memory_type VARCHAR(50) NOT NULL,  -- 'fact', 'preference', 'experience', 'skill'
        content TEXT NOT NULL,
        embedding VECTOR(1536),
        importance_score FLOAT DEFAULT 0.5,
        access_count INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_accessed TIMESTAMPTZ DEFAULT NOW(),
        metadata JSONB DEFAULT '{}',
        expiration_date TIMESTAMPTZ
    );
    
    -- 5. 审计日志表（黑匣子）
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_pid UUID REFERENCES agent_processes(pid) ON DELETE SET NULL,
        action_type VARCHAR(100) NOT NULL,
        input_data JSONB,
        output_data JSONB,
        reasoning TEXT,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        duration_ms FLOAT,
        tokens_used INTEGER DEFAULT 0,
        api_calls INTEGER DEFAULT 0,
        session_id UUID,
        trace_id UUID,
        metadata JSONB DEFAULT '{}'
    );
    
    -- 6. 任务队列表（协调服务）
    CREATE TABLE IF NOT EXISTS task_queues (
        task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        queue_name VARCHAR(100) NOT NULL,
        task_data JSONB NOT NULL,
        priority INTEGER DEFAULT 50,
        status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
        agent_pid UUID,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        processed_at TIMESTAMPTZ,
        retry_count INTEGER DEFAULT 0
    );
    
    -- 7. 分布式锁表（协调服务）
    CREATE TABLE IF NOT EXISTS distributed_locks (
        lock_name VARCHAR(255) PRIMARY KEY,
        agent_pid UUID,
        acquired_at TIMESTAMPTZ DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL
    );
    
    -- 创建索引
    CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_logs(agent_pid, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id);
    CREATE INDEX IF NOT EXISTS idx_context_agent ON context_pages(agent_pid);
    CREATE INDEX IF NOT EXISTS idx_memory_agent ON long_term_memory(agent_pid, memory_type);
    CREATE INDEX IF NOT EXISTS idx_checkpoints_agent ON checkpoints(agent_pid);
    CREATE INDEX IF NOT EXISTS idx_task_queue ON task_queues(queue_name, status, priority);
    
    -- 向量索引（需要 pgvector）
    CREATE INDEX IF NOT EXISTS idx_context_embedding ON context_pages 
        USING ivfflat (embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_memory_embedding ON long_term_memory 
        USING ivfflat (embedding vector_cosine_ops);
    """
    
    def __init__(self, connection_string: str, enable_vector: bool = True):
        """
        初始化 PostgreSQL 存储
        
        Args:
            connection_string: PostgreSQL 连接字符串
            enable_vector: 是否启用向量支持（需要 pgvector 扩展）
        """
        self.connection_string = connection_string
        self.enable_vector = enable_vector
        self.conn = None
        self.cur = None
        
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self.psycopg2 = psycopg2
            self.RealDictCursor = RealDictCursor
            
            if enable_vector:
                try:
                    from pgvector.psycopg2 import register_vector
                    self.register_vector = register_vector
                except ImportError:
                    logger.warning("pgvector not installed, vector search disabled")
                    self.enable_vector = False
                    self.register_vector = None
            
            self._connect()
            self._create_tables()
            
            logger.info("PostgreSQLStorage initialized (Five Roles Ready)")
            
        except ImportError:
            logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQLStorage: {e}")
            raise
    
    def _connect(self):
        """建立数据库连接"""
        self.conn = self.psycopg2.connect(self.connection_string)
        self.cur = self.conn.cursor()
        
        if self.enable_vector and self.register_vector:
            self.register_vector(self.conn)
            
        if self.enable_vector:
            self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.conn.commit()
    
    def _create_tables(self):
        """创建数据库表"""
        self.cur.execute(self.CREATE_TABLES_SQL)
        self.conn.commit()
        logger.debug("Database tables created/verified")
    
    # ========== 1. 长期记忆存储（海马体）==========
    
    def save_memory(self, agent_pid: str, memory_type: str,
                   content: str, metadata: Optional[Dict] = None) -> str:
        """
        保存长期记忆
        
        Args:
            agent_pid: Agent PID
            memory_type: 记忆类型（fact, preference, experience, skill）
            content: 记忆内容
            metadata: 额外元数据
        
        Returns:
            记忆 ID
        """
        # 生成嵌入向量
        embedding = None
        if self.enable_vector:
            embedding = self._generate_embedding(content)
        
        self.cur.execute("""
            INSERT INTO long_term_memory 
            (agent_pid, memory_type, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING memory_id
        """, (agent_pid, memory_type, content, embedding, json.dumps(metadata or {})))
        
        memory_id = self.cur.fetchone()[0]
        self.conn.commit()
        
        logger.debug(f"Saved {memory_type} memory {memory_id[:8]} for agent {agent_pid[:8]}")
        return str(memory_id)
    
    def retrieve_memories(self, agent_pid: str, memory_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """检索长期记忆"""
        if memory_type:
            self.cur.execute("""
                SELECT * FROM long_term_memory
                WHERE agent_pid = %s AND memory_type = %s
                ORDER BY last_accessed DESC
                LIMIT %s
            """, (agent_pid, memory_type, limit))
        else:
            self.cur.execute("""
                SELECT * FROM long_term_memory
                WHERE agent_pid = %s
                ORDER BY last_accessed DESC
                LIMIT %s
            """, (agent_pid, limit))
        
        memories = []
        for row in self.cur.fetchall():
            memories.append({
                'memory_id': row[0],
                'memory_type': row[2],
                'content': row[3],
                'importance_score': row[5],
                'created_at': row[7].timestamp() if row[7] else None,
            })
        
        return memories
    
    # ========== 2. 状态持久化（硬盘）==========
    
    def save_process(self, process: Any):
        """保存进程状态"""
        data = process.to_dict() if hasattr(process, 'to_dict') else process
        
        def ts_to_datetime(ts):
            return datetime.fromtimestamp(ts) if ts else None
        
        self.cur.execute("""
            INSERT INTO agent_processes 
            (pid, name, state, priority, token_usage, api_calls,
             execution_time, cpu_time, context_snapshot, checkpoint_id,
             parent_pid, created_at, last_run, started_at, terminated_at,
             error_count, last_error, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pid) DO UPDATE SET
                state = EXCLUDED.state,
                priority = EXCLUDED.priority,
                token_usage = EXCLUDED.token_usage,
                api_calls = EXCLUDED.api_calls,
                execution_time = EXCLUDED.execution_time,
                cpu_time = EXCLUDED.cpu_time,
                context_snapshot = EXCLUDED.context_snapshot,
                checkpoint_id = EXCLUDED.checkpoint_id,
                last_run = EXCLUDED.last_run,
                terminated_at = EXCLUDED.terminated_at,
                error_count = EXCLUDED.error_count,
                last_error = EXCLUDED.last_error,
                metadata = EXCLUDED.metadata
        """, (
            data.get('pid'), data.get('name'), data.get('state'), 
            data.get('priority', 50), data.get('token_usage', 0),
            data.get('api_calls', 0), data.get('execution_time', 0),
            data.get('cpu_time', 0), json.dumps(data.get('context', {})),
            data.get('checkpoint_id'), data.get('parent_pid'),
            ts_to_datetime(data.get('created_at')),
            ts_to_datetime(data.get('last_run')),
            ts_to_datetime(data.get('started_at')),
            ts_to_datetime(data.get('terminated_at')),
            data.get('error_count', 0), data.get('last_error'),
            json.dumps(data.get('metadata', {}))
        ))
        
        self.conn.commit()
    
    def load_process(self, pid: str) -> Optional[Any]:
        """加载进程状态"""
        self.cur.execute("SELECT * FROM agent_processes WHERE pid = %s", (pid,))
        row = self.cur.fetchone()
        return row
    
    def save_checkpoint(self, agent_pid: str, process_state: Dict,
                       context_pages: List[Dict], description: str = "") -> str:
        """保存检查点"""
        checkpoint_id = str(uuid.uuid4())
        
        self.cur.execute("""
            INSERT INTO checkpoints 
            (checkpoint_id, agent_pid, process_state, context_pages, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (checkpoint_id, agent_pid, json.dumps(process_state),
              json.dumps(context_pages), description))
        
        self.conn.commit()
        logger.info(f"Saved checkpoint {checkpoint_id[:8]} for agent {agent_pid[:8]}")
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """加载检查点"""
        self.cur.execute("""
            SELECT * FROM checkpoints WHERE checkpoint_id = %s
        """, (checkpoint_id,))
        
        row = self.cur.fetchone()
        if row:
            return {
                'checkpoint_id': row[0],
                'agent_pid': row[1],
                'process_state': row[2],
                'context_pages': row[3],
                'timestamp': row[4].timestamp() if row[4] else None,
                'description': row[5],
            }
        return None
    
    def list_checkpoints(self, agent_pid: str) -> List[Dict]:
        """列出所有检查点"""
        self.cur.execute("""
            SELECT checkpoint_id, timestamp, description
            FROM checkpoints
            WHERE agent_pid = %s
            ORDER BY timestamp DESC
        """, (agent_pid,))
        
        return [{'checkpoint_id': r[0], 'timestamp': r[1], 'description': r[2]} 
                for r in self.cur.fetchall()]
    
    # ========== 3. 向量索引（页表）==========
    
    def save_context_page(self, page: Any) -> str:
        """保存上下文页面（用于 swap out）"""
        data = page.to_dict() if hasattr(page, 'to_dict') else page
        
        embedding = data.get('embedding')
        if not embedding and self.enable_vector and data.get('content'):
            embedding = self._generate_embedding(data['content'])
        
        self.cur.execute("""
            INSERT INTO context_pages 
            (page_id, agent_pid, content, tokens, importance_score, page_type,
             status, embedding, access_count, last_accessed, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (page_id) DO UPDATE SET
                content = EXCLUDED.content,
                tokens = EXCLUDED.tokens,
                importance_score = EXCLUDED.importance_score,
                status = EXCLUDED.status,
                embedding = EXCLUDED.embedding,
                access_count = EXCLUDED.access_count,
                last_accessed = EXCLUDED.last_accessed
        """, (
            data['page_id'], data['agent_pid'], data['content'],
            data['tokens'], data['importance_score'], data['page_type'],
            'swapped', embedding, data['access_count'],
            datetime.fromtimestamp(data['last_accessed']),
            json.dumps(data.get('metadata', {}))
        ))
        
        self.conn.commit()
        return data['page_id']
    
    def load_context_page(self, page_id: str) -> Optional[Any]:
        """加载上下文页面（用于 swap in）"""
        self.cur.execute("SELECT * FROM context_pages WHERE page_id = %s", (page_id,))
        row = self.cur.fetchone()
        
        if row:
            # 更新访问时间
            self.cur.execute("""
                UPDATE context_pages 
                SET access_count = access_count + 1, last_accessed = NOW()
                WHERE page_id = %s
            """, (page_id,))
            self.conn.commit()
        
        return row
    
    def semantic_search(self, agent_pid: str, query_embedding: List[float],
                       limit: int = 10, threshold: float = 0.7) -> List[Dict]:
        """语义搜索"""
        if not self.enable_vector:
            logger.warning("Vector search disabled")
            return []
        
        self.cur.execute("""
            SELECT page_id, content, metadata, importance_score,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM context_pages
            WHERE agent_pid = %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, agent_pid, query_embedding, limit))
        
        results = []
        for row in self.cur.fetchall():
            if row[4] >= threshold:  # 相似度阈值
                results.append({
                    'page_id': row[0],
                    'content': row[1],
                    'metadata': row[2],
                    'importance_score': row[3],
                    'similarity': row[4]
                })
        
        return results
    
    def find_similar_memories(self, agent_pid: str, content: str,
                             limit: int = 5) -> List[Dict]:
        """查找相似记忆"""
        if not self.enable_vector:
            return []
        
        embedding = self._generate_embedding(content)
        
        self.cur.execute("""
            SELECT memory_id, memory_type, content, importance_score,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM long_term_memory
            WHERE agent_pid = %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (embedding, agent_pid, embedding, limit))
        
        return [{
            'memory_id': r[0],
            'memory_type': r[1],
            'content': r[2],
            'importance_score': r[3],
            'similarity': r[4]
        } for r in self.cur.fetchall()]
    
    # ========== 4. 协调服务（IPC）==========
    
    @contextmanager
    def acquire_lock(self, lock_name: str, timeout: float = 30.0):
        """获取分布式锁"""
        import signal
        
        lock_acquired = False
        agent_pid = str(uuid.uuid4())  # 临时 PID
        expires_at = datetime.now() + __import__('datetime').timedelta(seconds=timeout)
        
        try:
            # 尝试获取锁
            self.cur.execute("""
                INSERT INTO distributed_locks (lock_name, agent_pid, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (lock_name) DO NOTHING
            """, (lock_name, agent_pid, expires_at))
            
            self.conn.commit()
            
            # 检查是否获取成功
            self.cur.execute("""
                SELECT agent_pid FROM distributed_locks WHERE lock_name = %s
            """, (lock_name,))
            
            row = self.cur.fetchone()
            lock_acquired = row and row[0] == agent_pid
            
            if lock_acquired:
                logger.debug(f"Acquired lock {lock_name}")
                yield True
            else:
                yield False
                
        finally:
            if lock_acquired:
                self.cur.execute("""
                    DELETE FROM distributed_locks WHERE lock_name = %s
                """, (lock_name,))
                self.conn.commit()
                logger.debug(f"Released lock {lock_name}")
    
    def enqueue_task(self, queue_name: str, task: Dict) -> str:
        """入队任务"""
        task_id = str(uuid.uuid4())
        
        self.cur.execute("""
            INSERT INTO task_queues (task_id, queue_name, task_data, priority)
            VALUES (%s, %s, %s, %s)
        """, (task_id, queue_name, json.dumps(task), task.get('priority', 50)))
        
        self.conn.commit()
        return task_id
    
    def dequeue_task(self, queue_name: str) -> Optional[Dict]:
        """出队任务"""
        # 使用 SKIP LOCKED 实现并发安全
        self.cur.execute("""
            UPDATE task_queues
            SET status = 'processing', processed_at = NOW()
            WHERE task_id = (
                SELECT task_id FROM task_queues
                WHERE queue_name = %s AND status = 'pending'
                ORDER BY priority ASC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING task_id, task_data, priority
        """, (queue_name,))
        
        row = self.cur.fetchone()
        self.conn.commit()
        
        if row:
            return {
                'task_id': row[0],
                'data': json.loads(row[1]),
                'priority': row[2]
            }
        return None
    
    def publish_event(self, channel: str, message: Dict):
        """发布事件（使用 PostgreSQL NOTIFY）"""
        payload = json.dumps(message)
        self.cur.execute("NOTIFY %s, %s", (channel, payload))
        self.conn.commit()
    
    def subscribe_events(self, channel: str, callback: Callable):
        """订阅事件"""
        # 简化实现：实际应该使用异步监听
        logger.info(f"Subscribed to channel {channel}")
    
    # ========== 5. 审计日志（黑匣子）==========
    
    def log_action(self, agent_pid: str, action_type: str,
                   input_data: Dict, output_data: Dict,
                   reasoning: str = "", metadata: Optional[Dict] = None):
        """记录审计日志"""
        self.cur.execute("""
            INSERT INTO audit_logs 
            (agent_pid, action_type, input_data, output_data, reasoning, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            agent_pid, action_type, json.dumps(input_data),
            json.dumps(output_data), reasoning, json.dumps(metadata or {})
        ))
        
        self.conn.commit()
    
    def get_audit_trail(self, agent_pid: str, limit: int = 100) -> List[Dict]:
        """获取审计追踪"""
        self.cur.execute("""
            SELECT * FROM audit_logs 
            WHERE agent_pid = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (agent_pid, limit))
        
        logs = []
        for row in self.cur.fetchall():
            logs.append({
                'log_id': row[0],
                'action_type': row[2],
                'input_data': row[3],
                'output_data': row[4],
                'reasoning': row[5],
                'timestamp': row[6].timestamp() if row[6] else None,
            })
        
        return logs
    
    def replay_actions(self, agent_pid: str,
                      from_checkpoint: Optional[str] = None) -> List[Dict]:
        """回放操作"""
        # 获取检查点时间
        start_time = None
        if from_checkpoint:
            self.cur.execute("""
                SELECT timestamp FROM checkpoints WHERE checkpoint_id = %s
            """, (from_checkpoint,))
            row = self.cur.fetchone()
            if row:
                start_time = row[0]
        
        if start_time:
            self.cur.execute("""
                SELECT * FROM audit_logs 
                WHERE agent_pid = %s AND timestamp > %s
                ORDER BY timestamp ASC
            """, (agent_pid, start_time))
        else:
            self.cur.execute("""
                SELECT * FROM audit_logs 
                WHERE agent_pid = %s
                ORDER BY timestamp ASC
            """, (agent_pid,))
        
        return [{
            'action_type': r[2],
            'input': r[3],
            'output': r[4],
            'reasoning': r[5],
            'timestamp': r[6].timestamp() if r[6] else None,
        } for r in self.cur.fetchall()]
    
    # ========== 辅助方法 ==========
    
    def _generate_embedding(self, text: str) -> List[float]:
        """生成嵌入向量（简化实现）"""
        import random
        import hashlib
        # 使用文本哈希作为随机种子，确保相同文本产生相同嵌入
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)
        return [random.random() for _ in range(1536)]
    
    def close(self):
        """关闭数据库连接"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        logger.info("PostgreSQL connection closed")


class MemoryStorage(StorageBackend):
    """
    内存存储后端（简化版，用于开发和测试）
    
    所有数据存储在内存中，进程退出后数据丢失。
    仅支持五重角色的基本功能。
    """
    
    def __init__(self):
        # 1. 长期记忆存储
        self.memories_db: Dict[str, List[Dict]] = defaultdict(list)
        
        # 2. 状态持久化
        self.processes_db: Dict[str, Dict] = {}
        self.checkpoints_db: Dict[str, Dict] = {}
        
        # 3. 向量索引
        self.context_pages_db: Dict[str, Dict] = {}
        
        # 4. 协调服务
        self.task_queues: Dict[str, List[Dict]] = defaultdict(list)
        self.distributed_locks: Dict[str, Dict] = {}
        
        # 5. 审计日志
        self.audit_logs_db: List[Dict] = []
        
        logger.info("MemoryStorage initialized (Five Roles - In-Memory Mode)")
    
    # 1. 长期记忆存储
    def save_memory(self, agent_pid: str, memory_type: str,
                   content: str, metadata: Optional[Dict] = None) -> str:
        memory_id = str(uuid.uuid4())
        self.memories_db[agent_pid].append({
            'memory_id': memory_id,
            'memory_type': memory_type,
            'content': content,
            'metadata': metadata or {},
            'created_at': time.time(),
        })
        return memory_id
    
    def retrieve_memories(self, agent_pid: str, memory_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict]:
        memories = self.memories_db.get(agent_pid, [])
        if memory_type:
            memories = [m for m in memories if m['memory_type'] == memory_type]
        return memories[-limit:]
    
    # 2. 状态持久化
    def save_process(self, process: Any):
        data = process.to_dict() if hasattr(process, 'to_dict') else process
        self.processes_db[data.get('pid')] = data
    
    def load_process(self, pid: str) -> Optional[Any]:
        return self.processes_db.get(pid)
    
    def save_checkpoint(self, agent_pid: str, process_state: Dict,
                       context_pages: List[Dict], description: str = "") -> str:
        checkpoint_id = str(uuid.uuid4())
        self.checkpoints_db[checkpoint_id] = {
            'checkpoint_id': checkpoint_id,
            'agent_pid': agent_pid,
            'process_state': process_state,
            'context_pages': context_pages,
            'description': description,
            'timestamp': time.time(),
        }
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        return self.checkpoints_db.get(checkpoint_id)
    
    def list_checkpoints(self, agent_pid: str) -> List[Dict]:
        return [cp for cp in self.checkpoints_db.values() 
                if cp.get('agent_pid') == agent_pid]
    
    # 3. 向量索引
    def save_context_page(self, page: Any) -> str:
        data = page.to_dict() if hasattr(page, 'to_dict') else page
        self.context_pages_db[data['page_id']] = data
        return data['page_id']
    
    def load_context_page(self, page_id: str) -> Optional[Any]:
        return self.context_pages_db.get(page_id)
    
    def semantic_search(self, agent_pid: str, query_embedding: List[float],
                       limit: int = 10, threshold: float = 0.7) -> List[Dict]:
        # 内存版不支持向量搜索
        return []
    
    def find_similar_memories(self, agent_pid: str, content: str,
                             limit: int = 5) -> List[Dict]:
        return []
    
    # 4. 协调服务
    @contextmanager
    def acquire_lock(self, lock_name: str, timeout: float = 30.0):
        if lock_name not in self.distributed_locks:
            self.distributed_locks[lock_name] = {
                'acquired_at': time.time(),
                'expires_at': time.time() + timeout
            }
            try:
                yield True
            finally:
                del self.distributed_locks[lock_name]
        else:
            yield False
    
    def enqueue_task(self, queue_name: str, task: Dict) -> str:
        task_id = str(uuid.uuid4())
        self.task_queues[queue_name].append({
            'task_id': task_id,
            'data': task,
            'status': 'pending',
        })
        return task_id
    
    def dequeue_task(self, queue_name: str) -> Optional[Dict]:
        queue = self.task_queues.get(queue_name, [])
        for task in queue:
            if task['status'] == 'pending':
                task['status'] = 'processing'
                return task
        return None
    
    def publish_event(self, channel: str, message: Dict):
        pass
    
    def subscribe_events(self, channel: str, callback: Callable):
        pass
    
    # 5. 审计日志
    def log_action(self, agent_pid: str, action_type: str,
                   input_data: Dict, output_data: Dict,
                   reasoning: str = "", metadata: Optional[Dict] = None):
        self.audit_logs_db.append({
            'log_id': str(uuid.uuid4()),
            'agent_pid': agent_pid,
            'action_type': action_type,
            'input_data': input_data,
            'output_data': output_data,
            'reasoning': reasoning,
            'metadata': metadata or {},
            'timestamp': time.time(),
        })
    
    def get_audit_trail(self, agent_pid: str, limit: int = 100) -> List[Dict]:
        logs = [log for log in self.audit_logs_db if log['agent_pid'] == agent_pid]
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return logs[-limit:]
    
    def replay_actions(self, agent_pid: str,
                      from_checkpoint: Optional[str] = None) -> List[Dict]:
        return self.get_audit_trail(agent_pid)
    
    def close(self):
        pass


class StorageManager:
    """
    存储管理器
    
    统一的存储接口，封装 PostgreSQL 五重角色。
    """
    
    def __init__(self, backend: Optional[StorageBackend] = None):
        self.backend = backend or MemoryStorage()
        logger.info(f"StorageManager initialized with {type(self.backend).__name__}")
    
    @classmethod
    def from_postgresql(cls, connection_string: str, **kwargs):
        """从 PostgreSQL 创建存储管理器"""
        backend = PostgreSQLStorage(connection_string, **kwargs)
        return cls(backend)
    
    # 代理所有 StorageBackend 方法
    def __getattr__(self, name):
        return getattr(self.backend, name)
