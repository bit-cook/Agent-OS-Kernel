# -*- coding: utf-8 -*-
"""存储管理器

支持多种存储后端：
- Memory (内存)
- File (文件系统)
- PostgreSQL (关系数据库)
- Vector (向量数据库)

五重角色：
1. 记忆存储 (Episodic Memory)
2. 状态持久化 (State Persistence)
3. 向量索引 (Vector Index)
4. 审计日志 (Audit Log)
5. 检查点存储 (Checkpoint Storage)
"""

import json
import pickle
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

from .types import StorageBackend


T = TypeVar('T')


@dataclass
class StorageStats:
    """存储统计信息"""
    backend: str = ""
    total_keys: int = 0
    total_size_bytes: int = 0
    last_access: Optional[datetime] = None
    last_modify: Optional[datetime] = None
    hit_count: int = 0
    miss_count: int = 0


class StorageInterface(ABC):
    """存储接口"""
    
    @abstractmethod
    def save(self, key: str, value: Any) -> bool:
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        pass


class MemoryStorage(StorageInterface):
    """内存存储后端"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._stats = StorageStats(backend="memory")
    
    def save(self, key: str, value: Any) -> bool:
        with self._lock:
            try:
                size = len(pickle.dumps(value))
                self._data[key] = value
                self._metadata[key] = {
                    'size': size,
                    'created': time.time(),
                    'modified': time.time(),
                    'access': time.time()
                }
                self._stats.last_modify = datetime.utcnow()
                self._stats.total_keys = len(self._data)
                self._stats.total_size_bytes += size
                return True
            except Exception:
                return False
    
    def retrieve(self, key: str) -> Optional[Any]:
        with self._lock:
            self._stats.last_access = datetime.utcnow()
            if key in self._data:
                self._stats.hit_count += 1
                self._metadata[key]['access'] = time.time()
                return self._data[key]
            self._stats.miss_count += 1
            return None
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                size = self._metadata[key]['size']
                del self._data[key]
                del self._metadata[key]
                self._stats.total_keys = len(self._data)
                self._stats.total_size_bytes -= size
                return True
            return False
    
    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._data
    
    def list_keys(self, prefix: str = "") -> List[str]:
        with self._lock:
            if not prefix:
                return list(self._data.keys())
            return [k for k in self._data.keys() if k.startswith(prefix)]
    
    def clear(self) -> bool:
        with self._lock:
            self._data.clear()
            self._metadata.clear()
            self._stats = StorageStats(backend="memory")
            return True
    
    def get_stats(self) -> StorageStats:
        with self._lock:
            return StorageStats(
                backend="memory",
                total_keys=len(self._data),
                total_size_bytes=sum(m['size'] for m in self._metadata.values()),
                last_access=datetime.fromtimestamp(
                    max(m['access'] for m in self._metadata.values())
                ) if self._metadata else None,
                last_modify=self._stats.last_modify,
                hit_count=self._stats.hit_count,
                miss_count=self._stats.miss_count
            )


class FileStorage(StorageInterface):
    """文件存储后端"""
    
    def __init__(self, base_path: str = "./data"):
        import os
        self._base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._lock = threading.RLock()
        self._stats = StorageStats(backend="file")
    
    def _get_path(self, key: str) -> str:
        import os
        # 使用 hash 防止目录过深
        key_hash = hashlib.md5(key.encode()).hexdigest()
        subdir = key_hash[:2]
        filename = key_hash[2:] + ".json"
        path = os.path.join(self._base_path, subdir)
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, filename)
    
    def save(self, key: str, value: Any) -> bool:
        with self._lock:
            try:
                path = self._get_path(key)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(value, f, ensure_ascii=False, indent=2)
                self._stats.last_modify = datetime.utcnow()
                self._stats.total_keys += 1
                return True
            except Exception:
                return False
    
    def retrieve(self, key: str) -> Optional[Any]:
        with self._lock:
            try:
                path = self._get_path(key)
                if os.path.exists(path):
                    self._stats.last_access = datetime.utcnow()
                    self._stats.hit_count += 1
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                self._stats.miss_count += 1
                return None
            except Exception:
                return None
    
    def delete(self, key: str) -> bool:
        with self._lock:
            try:
                path = self._get_path(key)
                if os.path.exists(path):
                    os.remove(path)
                    self._stats.total_keys -= 1
                    return True
                return False
            except Exception:
                return False
    
    def exists(self, key: str) -> bool:
        import os
        with self._lock:
            return os.path.exists(self._get_path(key))
    
    def list_keys(self, prefix: str = "") -> List[str]:
        import os
        with self._lock:
            keys = []
            for root, dirs, files in os.walk(self._base_path):
                for f in files:
                    if f.endswith('.json'):
                        # 恢复原始 key
                        key_hash = f.replace('.json', '')
                        full_hash = os.path.basename(root) + key_hash
                        try:
                            # 这里简化处理，实际应该维护映射
                            keys.append(full_hash)
                        except Exception:
                            pass
            return keys
    
    def clear(self) -> bool:
        import shutil
        with self._lock:
            try:
                shutil.rmtree(self._base_path)
                os.makedirs(self._base_path, exist_ok=True)
                self._stats = StorageStats(backend="file")
                return True
            except Exception:
                return False


class PostgreSQLStorage(StorageInterface):
    """PostgreSQL 存储后端"""
    
    def __init__(self,
                 host: str = "localhost",
                 port: int = 5432,
                 database: str = "aosk",
                 user: str = "aosk",
                 password: str = "secret",
                 table_prefix: str = "aosk_"):
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._table_prefix = table_prefix
        self._pool = None
        self._lock = threading.RLock()
        self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        try:
            import psycopg2
            from psycopg2 import pool
            self._pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password
            )
            self._init_schema()
        except ImportError:
            self._pool = None
    
    def _init_schema(self):
        """初始化数据库 schema"""
        if self._pool is None:
            return
        
        conn = self._pool.getconn()
        try:
            cur = conn.cursor()
            # 主数据表
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_prefix}data (
                    key VARCHAR(512) PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    modified_at TIMESTAMP DEFAULT NOW(),
                    access_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # 检查点表
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_prefix}checkpoints (
                    checkpoint_id VARCHAR(64) PRIMARY KEY,
                    agent_pid VARCHAR(128) NOT NULL,
                    agent_name VARCHAR(256),
                    description TEXT,
                    state TEXT NOT NULL,
                    context TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # 审计日志表
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_prefix}audit (
                    id SERIAL PRIMARY KEY,
                    agent_pid VARCHAR(128),
                    action VARCHAR(128),
                    resource VARCHAR(512),
                    details TEXT,
                    result VARCHAR(64),
                    duration_ms REAL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # 向量索引表
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_prefix}vectors (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(512),
                    content TEXT NOT NULL,
                    embedding BYTEA,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
        finally:
            self._pool.putconn(conn)
    
    def save(self, key: str, value: Any) -> bool:
        if self._pool is None:
            return False
        with self._lock:
            try:
                conn = self._pool.getconn()
                cur = conn.cursor()
                value_json = json.dumps(value, ensure_ascii=False)
                cur.execute(f"""
                    INSERT INTO {self._table_prefix}data (key, value, modified_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE SET value = %s, modified_at = NOW()
                """, (key, value_json, value_json))
                conn.commit()
                self._pool.putconn(conn)
                return True
            except Exception:
                return False
    
    def retrieve(self, key: str) -> Optional[Any]:
        if self._pool is None:
            return None
        with self._lock:
            try:
                conn = self._pool.getconn()
                cur = conn.cursor()
                cur.execute(f"""
                    UPDATE {self._table_prefix}data SET access_at = NOW() WHERE key = %s
                """, (key,))
                cur.execute(f"SELECT value FROM {self._table_prefix}data WHERE key = %s", (key,))
                row = cur.fetchone()
                self._pool.putconn(conn)
                if row:
                    return json.loads(row[0])
                return None
            except Exception:
                return None
    
    def delete(self, key: str) -> bool:
        if self._pool is None:
            return False
        with self._lock:
            try:
                conn = self._pool.getconn()
                cur = conn.cursor()
                cur.execute(f"DELETE FROM {self._table_prefix}data WHERE key = %s", (key,))
                deleted = cur.rowcount > 0
                conn.commit()
                self._pool.putconn(conn)
                return deleted
            except Exception:
                return False
    
    def exists(self, key: str) -> bool:
        if self._pool is None:
            return False
        with self._lock:
            try:
                conn = self._pool.getconn()
                cur = conn.cursor()
                cur.execute(f"SELECT 1 FROM {self._table_prefix}data WHERE key = %s", (key,))
                exists = cur.fetchone() is not None
                self._pool.putconn(conn)
                return exists
            except Exception:
                return False
    
    def list_keys(self, prefix: str = "") -> List[str]:
        if self._pool is None:
            return []
        with self._lock:
            try:
                conn = self._pool.getconn()
                cur = conn.cursor()
                if prefix:
                    cur.execute(f"SELECT key FROM {self._table_prefix}data WHERE key LIKE %s", 
                               (f"{prefix}%",))
                else:
                    cur.execute(f"SELECT key FROM {self._table_prefix}data")
                keys = [row[0] for row in cur.fetchall()]
                self._pool.putconn(conn)
                return keys
            except Exception:
                return []
    
    def clear(self) -> bool:
        if self._pool is None:
            return False
        with self._lock:
            try:
                conn = self._pool.getconn()
                cur = conn.cursor()
                cur.execute(f"TRUNCATE {self._table_prefix}data CASCADE")
                conn.commit()
                self._pool.putconn(conn)
                return True
            except Exception:
                return False
    
    def save_checkpoint(self, checkpoint_data: dict) -> bool:
        """保存检查点"""
        if self._pool is None:
            return False
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO {self._table_prefix}checkpoints 
                (checkpoint_id, agent_pid, agent_name, description, state, context, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (checkpoint_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    context = EXCLUDED.context,
                    metadata = EXCLUDED.metadata
            """, (
                checkpoint_data['checkpoint_id'],
                checkpoint_data.get('agent_pid', ''),
                checkpoint_data.get('agent_name', ''),
                checkpoint_data.get('description', ''),
                json.dumps(checkpoint_data.get('state', {})),
                json.dumps(checkpoint_data.get('context_pages', [])),
                json.dumps(checkpoint_data.get('metadata', {}))
            ))
            conn.commit()
            self._pool.putconn(conn)
            return True
        except Exception:
            return False
    
    def save_audit_log(self, log_data: dict) -> bool:
        """保存审计日志"""
        if self._pool is None:
            return False
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO {self._table_prefix}audit 
                (agent_pid, action, resource, details, result, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                log_data.get('agent_pid', ''),
                log_data.get('action', ''),
                log_data.get('resource', ''),
                json.dumps(log_data.get('details', {})),
                log_data.get('result', ''),
                log_data.get('duration_ms', 0)
            ))
            conn.commit()
            self._pool.putconn(conn)
            return True
        except Exception:
            return False
    
    def save_vector(self, key: str, content: str, embedding: bytes, metadata: dict = None) -> bool:
        """保存向量"""
        if self._pool is None:
            return False
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO {self._table_prefix}vectors (key, content, embedding, metadata)
                VALUES (%s, %s, %s, %s)
            """, (key, content, embedding, json.dumps(metadata or {})))
            conn.commit()
            self._pool.putconn(conn)
            return True
        except Exception:
            return False
    
    def search_vectors(self, query_embedding: bytes, limit: int = 10) -> List[dict]:
        """搜索向量 (简化版 - 实际应使用 pgvector)"""
        if self._pool is None:
            return []
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            # 这里使用简化的相似度计算
            # 实际应该使用 pgvector 扩展的向量操作
            cur.execute(f"""
                SELECT id, key, content, metadata, 
                       (embedding <=> %s) as similarity
                FROM {self._table_prefix}vectors
                ORDER BY similarity ASC
                LIMIT %s
            """, (query_embedding, limit))
            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'key': row[1],
                    'content': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {},
                    'similarity': row[4]
                })
            self._pool.putconn(conn)
            return results
        except Exception:
            return []
    
    def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.closeall()


class VectorStorage(StorageInterface):
    """向量存储后端 (简化实现)"""
    
    def __init__(self, embedding_dim: int = 384):
        self._embedding_dim = embedding_dim
        self._vectors: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict] = {}
        self._content: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def save(self, key: str, embedding: bytes) -> bool:
        with self._lock:
            self._vectors[key] = embedding
            return True
    
    def retrieve(self, key: str) -> Optional[bytes]:
        with self._lock:
            return self._vectors.get(key)
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._vectors:
                del self._vectors[key]
                if key in self._metadata:
                    del self._metadata[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._vectors
    
    def list_keys(self, prefix: str = "") -> List[str]:
        with self._lock:
            if not prefix:
                return list(self._vectors.keys())
            return [k for k in self._vectors.keys() if k.startswith(prefix)]
    
    def clear(self) -> bool:
        with self._lock:
            self._vectors.clear()
            self._metadata.clear()
            return True
    
    def add(self, key: str, content: str, embedding: bytes, metadata: Dict = None) -> bool:
        """添加向量和内容"""
        with self._lock:
            self._vectors[key] = embedding
            self._content[key] = content
            self._metadata[key] = metadata or {}
            return True
    
    def search(self, query_embedding: bytes, top_k: int = 10) -> List[dict]:
        """搜索相似向量 (暴力计算 - 生产环境应使用索引)"""
        import math
        with self._lock:
            results = []
            for key, emb in self._vectors.items():
                # 计算余弦相似度
                similarity = self._cosine_similarity(query_embedding, emb)
                results.append({
                    'key': key,
                    'content': self._content.get(key, ''),
                    'metadata': self._metadata.get(key, {}),
                    'similarity': similarity
                })
            # 排序并返回 top_k
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:top_k]
    
    def _cosine_similarity(self, a: bytes, b: bytes) -> float:
        """计算余弦相似度"""
        import struct
        if len(a) != len(b):
            return 0.0
        # 将 bytes 转换为浮点数列表
        try:
            vec_a = struct.unpack(f'{len(a)//8}f', a)
            vec_b = struct.unpack(f'{len(b)//8}f', b)
            dot = sum(x * y for x, y in zip(vec_a, vec_b))
            norm_a = math.sqrt(sum(x * x for x in vec_a))
            norm_b = math.sqrt(sum(x * x for x in vec_b))
            if norm_a * norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        except Exception:
            return 0.0


class StorageManager:
    """
    存储管理器
    
    支持多种存储后端，提供统一的存储接口。
    五重角色：
    1. 记忆存储 (Episodic Memory)
    2. 状态持久化 (State Persistence)
    3. 向量索引 (Vector Index)
    4. 审计日志 (Audit Log)
    5. 检查点存储 (Checkpoint Storage)
    """
    
    def __init__(self,
                 backend: StorageBackend = StorageBackend.MEMORY,
                 **kwargs):
        self._backend = backend
        self._kwargs = kwargs
        
        # 初始化各存储后端
        self._data = self._create_storage(backend, kwargs)
        
        # 向量存储 (用于语义搜索)
        self._vector = VectorStorage()
        
        # 检查点存储
        self._checkpoint = self._create_storage(StorageBackend.MEMORY, kwargs)
        
        # 审计日志存储
        self._audit = self._create_storage(StorageBackend.MEMORY, kwargs)
    
    def _create_storage(self, backend: StorageBackend, kwargs: Dict) -> StorageInterface:
        """创建存储后端实例"""
        if backend == StorageBackend.MEMORY:
            return MemoryStorage()
        elif backend == StorageBackend.FILE:
            return FileStorage(kwargs.get('base_path', './data'))
        elif backend == StorageBackend.POSTGRESQL:
            return PostgreSQLStorage(
                host=kwargs.get('postgresql_host', 'localhost'),
                port=kwargs.get('postgresql_port', 5432),
                database=kwargs.get('postgresql_database', 'aosk'),
                user=kwargs.get('postgresql_user', 'aosk'),
                password=kwargs.get('postgresql_password', 'secret'),
                table_prefix=kwargs.get('table_prefix', 'aosk_')
            )
        else:
            return MemoryStorage()
    
    # ========== 通用存储接口 ==========
    
    def save(self, key: str, value: Any) -> bool:
        """保存数据"""
        return self._data.save(key, value)
    
    def retrieve(self, key: str) -> Optional[Any]:
        """检索数据"""
        return self._data.retrieve(key)
    
    def delete(self, key: str) -> bool:
        """删除数据"""
        result = self._data.delete(key)
        self._vector.delete(key)
        return result
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self._data.exists(key)
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        return self._data.list_keys(prefix)
    
    def clear(self) -> bool:
        """清空存储"""
        return self._data.clear()
    
    # ========== 检查点管理 ==========
    
    def save_checkpoint(self, checkpoint_data: dict) -> bool:
        """保存检查点"""
        checkpoint_id = checkpoint_data.get('checkpoint_id', '')
        if self._backend == StorageBackend.POSTGRESQL:
            if isinstance(self._data, PostgreSQLStorage):
                return self._data.save_checkpoint(checkpoint_data)
        return self._checkpoint.save(checkpoint_id, checkpoint_data)
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[dict]:
        """获取检查点"""
        if self._backend == StorageBackend.POSTGRESQL:
            if isinstance(self._data, PostgreSQLStorage):
                # 查询 PostgreSQL
                pass
        return self._checkpoint.retrieve(checkpoint_id)
    
    def list_checkpoints(self, agent_pid: str = None) -> List[dict]:
        """列出检查点"""
        keys = self._checkpoint.list_keys()
        checkpoints = []
        for key in keys:
            cp = self._checkpoint.retrieve(key)
            if cp and (agent_pid is None or cp.get('agent_pid') == agent_pid):
                checkpoints.append(cp)
        return checkpoints
    
    # ========== 审计日志 ==========
    
    def log_audit(self, log_data: dict) -> bool:
        """记录审计日志"""
        if self._backend == StorageBackend.POSTGRESQL:
            if isinstance(self._data, PostgreSQLStorage):
                return self._data.save_audit_log(log_data)
        return self._audit.save(
            f"{log_data.get('action', 'unknown')}_{log_data.get('agent_pid', 'unknown')}_{time.time()}",
            log_data
        )
    
    def get_audit_logs(self, agent_pid: str = None, limit: int = 100) -> List[dict]:
        """获取审计日志"""
        keys = self._audit.list_keys()
        logs = []
        for key in keys[-limit:]:
            log = self._audit.retrieve(key)
            if log and (agent_pid is None or log.get('agent_pid') == agent_pid):
                logs.append(log)
        return logs
    
    # ========== 向量存储 ==========
    
    def save_vector(self, key: str, content: str, embedding: bytes, metadata: Dict = None) -> bool:
        """保存向量"""
        self._data.save(key, {'content': content, 'metadata': metadata or {}})
        return self._vector.add(key, content, embedding, metadata)
    
    def search_vectors(self, query_embedding: bytes, top_k: int = 10) -> List[dict]:
        """搜索向量"""
        return self._vector.search(query_embedding, top_k)
    
    def semantic_search(self, query: str, embedding: bytes, top_k: int = 10) -> List[dict]:
        """语义搜索"""
        return self._vector.search(embedding, top_k)
    
    # ========== 统计信息 ==========
    
    def get_stats(self) -> Dict[str, StorageStats]:
        """获取存储统计"""
        return {
            'data': self._data.get_stats() if hasattr(self._data, 'get_stats') else None,
            'checkpoint': self._checkpoint.get_stats() if hasattr(self._checkpoint, 'get_stats') else None,
            'audit': self._audit.get_stats() if hasattr(self._audit, 'get_stats') else None,
        }
    
    def close(self):
        """关闭存储"""
        if hasattr(self._data, 'close'):
            self._data.close()
        if hasattr(self._checkpoint, 'close'):
            self._checkpoint.close()
        if hasattr(self._audit, 'close'):
            self._audit.close()
