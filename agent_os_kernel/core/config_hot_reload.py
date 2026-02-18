# -*- coding: utf-8 -*-
"""
Config Hot Reload Module

Configuration hot reload functionality with file watching, auto-reload,
config validation, and change notification.

Features:
- File system watching for configuration changes
- Automatic configuration reloading
- Configuration validation with schema support
- Change notification system with callbacks
"""

import os
import sys
import json
import time
import hashlib
import threading
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import jsonschema

# 逻辑风险提示：
# - 本模块依赖 watchdog/jsonschema（以及后续的 PyYAML），但它们未必在项目的基础依赖中声明。
#   如果用户仅安装最小依赖，导入该模块就可能触发 ImportError。
# - 建议：
#   1) 将其加入 requirements/pyproject optional-dependencies；或
#   2) 将 import 放入函数内部并给出明确提示，使其成为可选能力。

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigChangeType(Enum):
    """Types of configuration changes"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    VALIDATION_ERROR = "validation_error"
    RELOAD_SUCCESS = "reload_success"
    RELOAD_FAILED = "reload_failed"


@dataclass
class ConfigChange:
    """Represents a configuration change event"""
    config_path: str
    change_type: ConfigChangeType
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    file_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "config_path": self.config_path,
            "change_type": self.change_type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "file_hash": self.file_hash
        }


@dataclass
class ConfigSchema:
    """Configuration schema for validation"""
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    additional_properties: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "properties": self.properties,
            "required": self.required,
            "additionalProperties": self.additional_properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigSchema':
        """Create from dictionary"""
        return cls(
            type=data.get("type", "object"),
            properties=data.get("properties", {}),
            required=data.get("required", []),
            additional_properties=data.get("additionalProperties", True)
        )


class ConfigValidator:
    """Configuration validator with JSON schema support"""
    
    def __init__(self, schema: Optional[Union[Dict[str, Any], ConfigSchema]] = None):
        """Initialize validator with optional schema"""
        self._schema: Optional[Dict[str, Any]] = None
        self._config_schema: Optional[ConfigSchema] = None
        
        if schema:
            if isinstance(schema, ConfigSchema):
                self._config_schema = schema
                self._schema = schema.to_dict()
            else:
                self._schema = schema
                # Try to create ConfigSchema from dict
                try:
                    self._config_schema = ConfigSchema.from_dict(schema)
                except Exception:
                    self._config_schema = None
    
    def validate(self, config: Any, config_path: str = "") -> tuple[bool, Optional[str]]:
        """
        Validate configuration against schema
        
        Args:
            config: Configuration to validate
            config_path: Path to config file (for error messages)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self._schema is None:
            return True, None
        
        try:
            jsonschema.validate(instance=config, schema=self._schema)
            return True, None
        except jsonschema.ValidationError as e:
            error_path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            error_message = f"Validation error at {error_path}: {e.message}"
            logger.error(f"[ConfigValidator] {error_message}")
            return False, error_message
    
    def validate_file(self, file_path: str) -> tuple[bool, Optional[str], Optional[Any]]:
        """
        Validate a configuration file
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, error_message, parsed_config)
        """
        try:
            # Read and parse file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try JSON first
            try:
                config = json.loads(content)
            except json.JSONDecodeError:
                # Try YAML
                try:
                    import yaml
                    config = yaml.safe_load(content)
                except ImportError:
                    # 逻辑风险提示：yaml 依赖缺失时返回错误字符串，但上层可能不一定处理该错误。
                    return False, "Neither JSON nor YAML parsing available", None
                except yaml.YAMLError as e:
                    return False, f"YAML parsing error: {str(e)}", None
            
            # Validate
            is_valid, error = self.validate(config, file_path)
            
            return is_valid, error, config
            
        except FileNotFoundError:
            return False, f"Config file not found: {file_path}", None
        except Exception as e:
            return False, f"Error reading config file: {str(e)}", None
    
    def set_schema(self, schema: Union[Dict[str, Any], ConfigSchema]) -> None:
        """Set validation schema"""
        if isinstance(schema, ConfigSchema):
            self._config_schema = schema
            self._schema = schema.to_dict()
        else:
            self._schema = schema
            try:
                self._config_schema = ConfigSchema.from_dict(schema)
            except Exception:
                self._config_schema = None


class ConfigFileHandler(FileSystemEventHandler):
    """Handler for file system events on configuration files"""
    
    def __init__(self, config_hot_reload: 'ConfigHotReload'):
        """Initialize handler with reference to ConfigHotReload instance"""
        self.config_hot_reload = config_hot_reload
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events"""
        if event.is_directory:
            return
        
        if self._is_config_file(event.src_path):
            logger.info(f"[ConfigFileHandler] Config file modified: {event.src_path}")
            self.config_hot_reload._handle_file_change(event.src_path, ConfigChangeType.MODIFIED)
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events"""
        if event.is_directory:
            return
        
        if self._is_config_file(event.src_path):
            logger.info(f"[ConfigFileHandler] Config file created: {event.src_path}")
            self.config_hot_reload._handle_file_change(event.src_path, ConfigChangeType.CREATED)
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events"""
        if event.is_directory:
            return
        
        if self._is_config_file(event.src_path):
            logger.info(f"[ConfigFileHandler] Config file deleted: {event.src_path}")
            self.config_hot_reload._handle_file_change(event.src_path, ConfigChangeType.DELETED)
    
    def _is_config_file(self, file_path: str) -> bool:
        """Check if file is a configuration file"""
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf'}
        ext = Path(file_path).suffix.lower()
        return ext in config_extensions


class ConfigHotReload:
    """
    Configuration hot reload manager
    
    Features:
    - File system watching for configuration changes
    - Automatic configuration reloading
    - Configuration validation with schema support
    - Change notification system with callbacks
    """
    
    def __init__(
        self,
        config_dir: str = "config",
        watch_interval: float = 1.0,
        debounce_time: float = 0.5,
        auto_reload: bool = True,
        validation_enabled: bool = True,
        schema: Optional[Union[Dict[str, Any], ConfigSchema]] = None
    ):
        """
        Initialize configuration hot reload manager
        
        Args:
            config_dir: Directory to watch for configuration files
            watch_interval: Interval between file checks (seconds)
            debounce_time: Debounce time for rapid file changes (seconds)
            auto_reload: Whether to automatically reload configs on changes
            validation_enabled: Whether to validate configs on reload
            schema: Optional JSON schema for configuration validation
        """
        self.config_dir = config_dir
        self.watch_interval = watch_interval
        self.debounce_time = debounce_time
        self.auto_reload = auto_reload
        self.validation_enabled = validation_enabled
        
        # File tracking
        self._config_files: Dict[str, Dict[str, Any]] = {}
        self._config_cache: Dict[str, Any] = {}
        
        # Event handling
        self._callbacks: Dict[str, List[Callable]] = {}
        self._change_history: List[ConfigChange] = []
        self._lock = threading.RLock()
        
        # File watching
        self._observer: Optional[Observer] = None
        self._file_handler: Optional[ConfigFileHandler] = None
        self._watching = False
        
        # Validation
        self._validator = ConfigValidator(schema) if schema else ConfigValidator()
        
        # Debounce tracking
        self._last_change_time: Dict[str, float] = {}
        self._pending_changes: Dict[str, ConfigChange] = {}
        
        # Stats
        self._reload_count = 0
        self._error_count = 0
    
    @property
    def watching(self) -> bool:
        """Check if file watching is active"""
        return self._watching
    
    @property
    def reload_count(self) -> int:
        """Get number of successful reloads"""
        return self._reload_count
    
    @property
    def error_count(self) -> int:
        """Get number of reload errors"""
        return self._error_count
    
    @property
    def config_files(self) -> List[str]:
        """Get list of watched configuration files"""
        with self._lock:
            return list(self._config_files.keys())
    
    def start(self) -> bool:
        """
        Start watching configuration files
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Ensure config directory exists
            Path(self.config_dir).mkdir(parents=True, exist_ok=True)
            
            # Set up file handler
            self._file_handler = ConfigFileHandler(self)
            
            # Set up observer
            self._observer = Observer()
            self._observer.schedule(
                self._file_handler,
                self.config_dir,
                recursive=True
            )
            
            # Start observer
            self._observer.start()
            self._watching = True
            
            logger.info(f"[ConfigHotReload] Started watching: {self.config_dir}")
            
            # Initial load of all configs
            self._load_all_configs()
            
            return True
            
        except Exception as e:
            logger.error(f"[ConfigHotReload] Failed to start: {e}")
            return False
    
    def stop(self) -> None:
        """Stop watching configuration files"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        self._watching = False
        logger.info("[ConfigHotReload] Stopped watching")
    
    def add_config_file(self, file_path: str, watch: bool = True) -> bool:
        """
        Add a configuration file to watch
        
        Args:
            file_path: Path to configuration file
            watch: Whether to watch for changes
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            with self._lock:
                # Calculate file hash
                file_hash = self._calculate_file_hash(abs_path)
                
                # Load config if exists
                config = None
                if os.path.exists(abs_path):
                    _, _, config = self._validator.validate_file(abs_path)
                    if config is None:
                        # Try loading without validation
                        config = self._load_config_without_validation(abs_path)
                
                # Store file info
                self._config_files[abs_path] = {
                    'path': abs_path,
                    'hash': file_hash,
                    'watch': watch,
                    'last_modified': os.path.getmtime(abs_path) if os.path.exists(abs_path) else None
                }
                
                # Cache config
                if config is not None:
                    self._config_cache[abs_path] = config
            
            logger.info(f"[ConfigHotReload] Added config file: {abs_path}")
            return True
            
        except Exception as e:
            logger.error(f"[ConfigHotReload] Failed to add config file: {e}")
            return False
    
    def remove_config_file(self, file_path: str) -> bool:
        """
        Remove a configuration file from watching
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            with self._lock:
                if abs_path in self._config_files:
                    del self._config_files[abs_path]
                if abs_path in self._config_cache:
                    del self._config_cache[abs_path]
            
            logger.info(f"[ConfigHotReload] Removed config file: {abs_path}")
            return True
            
        except Exception as e:
            logger.error(f"[ConfigHotReload] Failed to remove config file: {e}")
            return False
    
    def get_config(self, file_path: str) -> Optional[Any]:
        """
        Get configuration from cache
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Configuration object or None if not found
        """
        abs_path = os.path.abspath(file_path)
        
        with self._lock:
            return self._config_cache.get(abs_path)
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        Get all cached configurations
        
        Returns:
            Dictionary of file paths to configuration objects
        """
        with self._lock:
            return dict(self._config_cache)
    
    def reload_config(self, file_path: str) -> tuple[bool, Optional[str], Optional[Any]]:
        """
        Manually reload a configuration file
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Tuple of (success, error_message, config)
        """
        abs_path = os.path.abspath(file_path)
        
        try:
            # Validate and load
            if self.validation_enabled:
                is_valid, error, config = self._validator.validate_file(abs_path)
                if not is_valid:
                    self._error_count += 1
                    return False, error, None
            else:
                config = self._load_config_without_validation(abs_path)
            
            if config is None:
                return False, "Config file not found or could not be parsed", None
            
            # Update cache
            with self._lock:
                self._config_cache[abs_path] = config
                if abs_path in self._config_files:
                    self._config_files[abs_path]['hash'] = self._calculate_file_hash(abs_path)
            
            self._reload_count += 1
            
            # Notify callbacks
            change = ConfigChange(
                config_path=abs_path,
                change_type=ConfigChangeType.RELOAD_SUCCESS,
                old_value=self._config_cache.get(abs_path),
                new_value=config
            )
            self._notify_callbacks(abs_path, change)
            
            return True, None, config
            
        except Exception as e:
            self._error_count += 1
            error_msg = f"Error reloading config: {str(e)}"
            logger.error(f"[ConfigHotReload] {error_msg}")
            
            # Notify of error
            change = ConfigChange(
                config_path=abs_path,
                change_type=ConfigChangeType.RELOAD_FAILED,
                error_message=error_msg
            )
            self._notify_callbacks(abs_path, change)
            
            return False, error_msg, None
    
    def register_callback(
        self,
        file_path: str,
        callback: Callable[[ConfigChange], None]
    ) -> None:
        """
        Register a callback for configuration changes
        
        Args:
            file_path: Path to configuration file (use "" for all files)
            callback: Callback function to call on changes
        """
        with self._lock:
            if file_path not in self._callbacks:
                self._callbacks[file_path] = []
            self._callbacks[file_path].append(callback)
        
        logger.info(f"[ConfigHotReload] Registered callback for: {file_path or 'all files'}")
    
    def unregister_callback(
        self,
        file_path: str,
        callback: Callable[[ConfigChange], None]
    ) -> bool:
        """
        Unregister a callback for configuration changes
        
        Args:
            file_path: Path to configuration file
            callback: Callback function to remove
            
        Returns:
            True if callback was removed, False otherwise
        """
        with self._lock:
            if file_path in self._callbacks:
                try:
                    self._callbacks[file_path].remove(callback)
                    logger.info(f"[ConfigHotReload] Unregistered callback for: {file_path}")
                    return True
                except ValueError:
                    pass
        return False
    
    def set_validation_schema(
        self,
        schema: Union[Dict[str, Any], ConfigSchema]
    ) -> None:
        """Set validation schema for configurations"""
        self._validator.set_schema(schema)
        logger.info("[ConfigHotReload] Validation schema updated")
    
    def get_change_history(
        self,
        file_path: Optional[str] = None,
        limit: int = 100
    ) -> List[ConfigChange]:
        """
        Get configuration change history
        
        Args:
            file_path: Optional filter by file path
            limit: Maximum number of changes to return
            
        Returns:
            List of configuration changes
        """
        with self._lock:
            changes = self._change_history
            
            if file_path:
                changes = [c for c in changes if c.config_path == file_path]
            
            return changes[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get hot reload statistics
        
        Returns:
            Dictionary of statistics
        """
        with self._lock:
            return {
                'watching': self._watching,
                'config_dir': self.config_dir,
                'config_files_count': len(self._config_files),
                'reload_count': self._reload_count,
                'error_count': self._error_count,
                'change_history_count': len(self._change_history),
                'callbacks_count': sum(len(cbs) for cbs in self._callbacks.values()),
                'auto_reload': self.auto_reload,
                'validation_enabled': self.validation_enabled
            }
    
    def _handle_file_change(
        self,
        file_path: str,
        change_type: ConfigChangeType
    ) -> None:
        """Handle a file change event"""
        abs_path = os.path.abspath(file_path)
        
        # Check debounce
        current_time = time.time()
        last_time = self._last_change_time.get(abs_path, 0)
        
        if current_time - last_time < self.debounce_time:
            # Skip rapid changes
            return
        
        self._last_change_time[abs_path] = current_time
        
        # Load config
        old_value = self._config_cache.get(abs_path)
        is_valid, error, new_value = self._validator.validate_file(abs_path)
        
        if not is_valid and self.validation_enabled:
            # Validation failed
            change = ConfigChange(
                config_path=abs_path,
                change_type=ConfigChangeType.VALIDATION_ERROR,
                old_value=old_value,
                error_message=error
            )
            self._error_count += 1
        else:
            # Load config
            if new_value is None:
                new_value = self._load_config_without_validation(abs_path)
            
            # Update cache
            with self._lock:
                self._config_cache[abs_path] = new_value
                if abs_path in self._config_files:
                    self._config_files[abs_path]['hash'] = self._calculate_file_hash(abs_path)
            
            change = ConfigChange(
                config_path=abs_path,
                change_type=change_type,
                old_value=old_value,
                new_value=new_value,
                file_hash=self._calculate_file_hash(abs_path)
            )
            
            if self.auto_reload:
                self._reload_count += 1
        
        # Store and notify
        with self._lock:
            self._change_history.append(change)
            # Keep only last 1000 changes
            if len(self._change_history) > 1000:
                self._change_history = self._change_history[-1000:]
        
        self._notify_callbacks(abs_path, change)
    
    def _notify_callbacks(self, file_path: str, change: ConfigChange) -> None:
        """Notify all registered callbacks for a file change"""
        callbacks_to_call = []
        
        with self._lock:
            # Get callbacks for specific file and all files
            callbacks_to_call.extend(self._callbacks.get(file_path, []))
            callbacks_to_call.extend(self._callbacks.get("", []))
        
        for callback in callbacks_to_call:
            try:
                callback(change)
            except Exception as e:
                # 逻辑风险提示：回调异常会被吞掉（仅日志），
                # 可能导致外部系统以为已收到变更通知，但实际上 callback 内部失败。
                logger.error(f"[ConfigHotReload] Callback error: {e}")
    
    def _load_all_configs(self) -> None:
        """Load all configuration files in the config directory"""
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf'}
        
        try:
            for root, dirs, files in os.walk(self.config_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    ext = Path(file).suffix.lower()
                    
                    if ext in config_extensions:
                        self.add_config_file(file_path)
                        
        except Exception as e:
            logger.error(f"[ConfigHotReload] Error loading configs: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def _load_config_without_validation(self, file_path: str) -> Optional[Any]:
        """Load configuration file without validation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try JSON first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
            
            # Try YAML
            try:
                import yaml
                return yaml.safe_load(content)
            except ImportError:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"[ConfigHotReload] Error loading config: {e}")
            return None


def create_config_hot_reload(
    config_dir: str = "config",
    watch_interval: float = 1.0,
    debounce_time: float = 0.5,
    auto_reload: bool = True,
    validation_enabled: bool = True,
    schema: Optional[Dict[str, Any]] = None
) -> ConfigHotReload:
    """
    Factory function to create ConfigHotReload instance
    
    Args:
        config_dir: Directory to watch for configuration files
        watch_interval: Interval between file checks (seconds)
        debounce_time: Debounce time for rapid file changes (seconds)
        auto_reload: Whether to automatically reload configs on changes
        validation_enabled: Whether to validate configs on reload
        schema: Optional JSON schema for configuration validation
        
    Returns:
        ConfigHotReload instance
    """
    return ConfigHotReload(
        config_dir=config_dir,
        watch_interval=watch_interval,
        debounce_time=debounce_time,
        auto_reload=auto_reload,
        validation_enabled=validation_enabled,
        schema=schema
    )
