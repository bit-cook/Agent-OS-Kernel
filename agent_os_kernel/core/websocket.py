# -*- coding: utf-8 -*-
"""
WebSocket Module for Agent-OS-Kernel

Provides WebSocket client/server functionality with automatic
reconnection, message handling, and thread-safe operations.
"""

import json
import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List, Any
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class WebSocketState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CLOSING = "closing"
    RECONNECTING = "reconnecting"


@dataclass
class WebSocketMessage:
    """WebSocket message container."""
    type: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    raw: Optional[bytes] = None


@dataclass
class WebSocketConfig:
    """WebSocket configuration."""
    uri: str
    reconnect_delay: float = 1.0
    max_reconnect_attempts: int = 5
    heartbeat_interval: Optional[float] = None
    heartbeat_message: Optional[str] = None
    connection_timeout: float = 10.0
    auto_reconnect: bool = True
    validate_ssl: bool = True


class WebSocketHandler(ABC):
    """Abstract base class for WebSocket handlers."""
    
    @abstractmethod
    def on_open(self, ws: 'WebSocketClient') -> None:
        """Called when connection is opened."""
        pass
    
    @abstractmethod
    def on_message(self, ws: 'WebSocketClient', message: WebSocketMessage) -> None:
        """Called when a message is received."""
        pass
    
    @abstractmethod
    def on_close(self, ws: 'WebSocketClient', code: int, reason: str) -> None:
        """Called when connection is closed."""
        pass
    
    @abstractmethod
    def on_error(self, ws: 'WebSocketClient', error: Exception) -> None:
        """Called when an error occurs."""
        pass


class DefaultWebSocketHandler(WebSocketHandler):
    """Default WebSocket handler with logging."""
    
    def on_open(self, ws: 'WebSocketClient') -> None:
        logger.info(f"WebSocket connected to {ws.config.uri}")
    
    def on_message(self, ws: 'WebSocketClient', message: WebSocketMessage) -> None:
        logger.debug(f"WebSocket message received: {message.type}")
    
    def on_close(self, ws: 'WebSocketClient', code: int, reason: str) -> None:
        logger.info(f"WebSocket closed: {code} - {reason}")
    
    def on_error(self, ws: 'WebSocketClient', error: Exception) -> None:
        logger.error(f"WebSocket error: {error}")


class WebSocketClient:
    """
    WebSocket Client with Auto-Reconnection
    
    Provides thread-safe WebSocket connections with automatic
    reconnection, message handling, and heartbeat support.
    """
    
    def __init__(self, config: WebSocketConfig):
        """
        Initialize the WebSocket client.
        
        Args:
            config: WebSocket configuration
        """
        self.config = config
        self.state = WebSocketState.DISCONNECTED
        self._handlers: List[WebSocketHandler] = []
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._reconnect_attempts = 0
        self._ws = None  # Placeholder for actual WebSocket connection
        self._running = False
        self._heartbeat_thread = None
        self._receive_thread = None
        self._send_queue: List[WebSocketMessage] = []
        self._send_lock = threading.Lock()
    
    def add_handler(self, handler: WebSocketHandler) -> None:
        """Add a message handler."""
        with self._lock:
            self._handlers.append(handler)
    
    def remove_handler(self, handler: WebSocketHandler) -> None:
        """Remove a message handler."""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
    
    def on(self, message_type: str) -> Callable:
        """Decorator to register message handlers."""
        def decorator(func: Callable) -> Callable:
            with self._lock:
                if message_type not in self._message_handlers:
                    self._message_handlers[message_type] = []
                self._message_handlers[message_type].append(func)
            return func
        return decorator
    
    def _notify_handlers(self, method: str, *args, **kwargs) -> None:
        """Notify all registered handlers."""
        with self._lock:
            for handler in self._handlers.copy():
                getattr(handler, method)(self, *args, **kwargs)
    
    def _handle_message(self, message: WebSocketMessage) -> None:
        """Process incoming message."""
        # Notify general handlers
        self._notify_handlers('on_message', message)
        
        # Notify type-specific handlers
        with self._lock:
            handlers = self._message_handlers.get(message.type, []).copy()
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    def connect(self, timeout: Optional[float] = None) -> bool:
        """
        Establish WebSocket connection.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully, False otherwise
        """
        timeout = timeout or self.config.connection_timeout
        
        with self._lock:
            if self.state == WebSocketState.CONNECTED:
                return True
            
            self.state = WebSocketState.CONNECTING
            self._reconnect_attempts = 0
        
        try:
            # In a real implementation, this would use websockets library
            # For now, we'll simulate the connection
            logger.debug(f"Connecting to {self.config.uri}")
            
            # Simulate connection delay
            time.sleep(0.1)
            
            with self._lock:
                self.state = WebSocketState.CONNECTED
                self._reconnect_attempts = 0
                self._running = True
            
            # Start heartbeat if configured
            if self.config.heartbeat_interval:
                self._start_heartbeat()
            
            # Start receive thread
            self._start_receive_thread()
            
            # Notify handlers
            self._notify_handlers('on_open')
            
            logger.info(f"Successfully connected to {self.config.uri}")
            return True
            
        except Exception as e:
            with self._lock:
                self.state = WebSocketState.DISCONNECTED
            
            logger.error(f"Failed to connect to {self.config.uri}: {e}")
            self._notify_handlers('on_error', e)
            
            # Try to reconnect if enabled
            if self.config.auto_reconnect:
                return self._schedule_reconnect()
            
            return False
    
    def disconnect(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """
        Close the WebSocket connection.
        
        Args:
            code: Close code
            reason: Close reason
        """
        with self._lock:
            if self.state in (WebSocketState.DISCONNECTED, WebSocketState.CLOSING):
                return
            
            self.state = WebSocketState.CLOSING
            self._running = False
        
        # Stop heartbeat
        self._stop_heartbeat()
        
        # Stop receive thread
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)
        
        try:
            # In real implementation: close the WebSocket
            logger.debug(f"Disconnecting from {self.config.uri}")
            
            with self._lock:
                self.state = WebSocketState.DISCONNECTED
            
            # Notify handlers
            self._notify_handlers('on_close', code, reason)
            
            logger.info(f"Disconnected from {self.config.uri}")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            with self._lock:
                self.state = WebSocketState.DISCONNECTED
    
    def send(self, message: WebSocketMessage) -> bool:
        """
        Send a message through WebSocket.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        with self._lock:
            if self.state != WebSocketState.CONNECTED:
                logger.warning("Cannot send message: not connected")
                return False
        
        try:
            # In real implementation: send via WebSocket
            logger.debug(f"Sending message: {message.type}")
            
            # Queue for guaranteed delivery
            with self._send_lock:
                self._send_queue.append(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def send_text(self, text: str, message_type: str = "text") -> bool:
        """
        Send a text message.
        
        Args:
            text: Text content
            message_type: Message type identifier
            
        Returns:
            True if sent successfully
        """
        message = WebSocketMessage(type=message_type, data=text)
        return self.send(message)
    
    def send_json(self, data: dict, message_type: str = "json") -> bool:
        """
        Send a JSON message.
        
        Args:
            data: Dictionary to send as JSON
            message_type: Message type identifier
            
        Returns:
            True if sent successfully
        """
        try:
            json_str = json.dumps(data)
            message = WebSocketMessage(type=message_type, data=data, raw=json_str.encode())
            return self.send(message)
        except Exception as e:
            logger.error(f"Failed to send JSON: {e}")
            return False
    
    def _schedule_reconnect(self) -> bool:
        """Schedule a reconnection attempt."""
        with self._lock:
            if self._reconnect_attempts >= self.config.max_reconnect_attempts:
                logger.error(f"Max reconnect attempts reached ({self.config.max_reconnect_attempts})")
                return False
            
            self.state = WebSocketState.RECONNECTING
            self._reconnect_attempts += 1
        
        delay = min(
            self.config.reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
            30.0  # Max 30 seconds delay
        )
        
        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts}/{self.config.max_reconnect_attempts})")
        
        # Schedule reconnect after delay
        def reconnect():
            time.sleep(delay)
            self.connect()
        
        thread = threading.Thread(target=reconnect, daemon=True)
        thread.start()
        
        return True
    
    def _start_heartbeat(self) -> None:
        """Start heartbeat thread."""
        def heartbeat_loop():
            while self._running and self.state == WebSocketState.CONNECTED:
                try:
                    if self.config.heartbeat_message:
                        self.send_text(self.config.heartbeat_message, "ping")
                    time.sleep(self.config.heartbeat_interval)
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                    break
        
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def _stop_heartbeat(self) -> None:
        """Stop heartbeat thread."""
        self._heartbeat_thread = None
    
    def _start_receive_thread(self) -> None:
        """Start message receiving thread."""
        def receive_loop():
            while self._running and self.state == WebSocketState.CONNECTED:
                try:
                    # Simulate receiving messages
                    # In real implementation: ws.recv()
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Receive error: {e}")
                    break
            
            # Connection lost
            if self._running:
                self._handle_disconnect()
        
        self._receive_thread = threading.Thread(target=receive_loop, daemon=True)
        self._receive_thread.start()
    
    def _handle_disconnect(self) -> None:
        """Handle unexpected disconnection."""
        was_connected = False
        with self._lock:
            if self.state == WebSocketState.CONNECTED:
                was_connected = True
                self.state = WebSocketState.DISCONNECTED
        
        if was_connected:
            self._notify_handlers('on_close', 1006, "Connection lost")
            
            # Attempt reconnect if enabled
            if self.config.auto_reconnect:
                self._schedule_reconnect()
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        with self._lock:
            return self.state == WebSocketState.CONNECTED
    
    @property
    def connection_state(self) -> WebSocketState:
        """Get current connection state."""
        with self._lock:
            return self.state
    
    @property
    def pending_messages(self) -> int:
        """Get number of pending messages in queue."""
        with self._send_lock:
            return len(self._send_queue)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        with self._lock:
            return {
                "state": self.state.value,
                "reconnect_attempts": self._reconnect_attempts,
                "pending_messages": self.pending_messages,
                "uri": self.config.uri,
                "handlers_count": len(self._handlers),
            }


class WebSocketServer:
    """
    WebSocket Server
    
    Provides basic WebSocket server functionality for handling
    multiple client connections.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize WebSocket server.
        
        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self._clients: Dict[str, WebSocketClient] = {}
        self._lock = threading.RLock()
        self._running = False
        self._server_thread = None
    
    def start(self) -> bool:
        """Start the WebSocket server."""
        with self._lock:
            if self._running:
                return True
            
            self._running = True
        
        def server_loop():
            logger.info(f"WebSocket server starting on {self.host}:{self.port}")
            # In real implementation: use websockets.serve()
            while self._running:
                try:
                    time.sleep(0.1)
                    # Accept connections, handle messages
                except Exception as e:
                    logger.error(f"Server error: {e}")
                    break
            logger.info("WebSocket server stopped")
        
        self._server_thread = threading.Thread(target=server_loop, daemon=True)
        self._server_thread.start()
        
        return True
    
    def stop(self) -> None:
        """Stop the WebSocket server."""
        with self._lock:
            self._running = False
        
        # Disconnect all clients
        with self._lock:
            for client in self._clients.values():
                client.disconnect()
            self._clients.clear()
        
        if self._server_thread:
            self._server_thread.join(timeout=2.0)
        
        logger.info("WebSocket server stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        with self._lock:
            return self._running
    
    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        with self._lock:
            return len(self._clients)
    
    def broadcast(self, message: WebSocketMessage) -> int:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of clients that received the message
        """
        count = 0
        with self._lock:
            clients = list(self._clients.values())
        
        for client in clients:
            if client.is_connected and client.send(message):
                count += 1
        
        return count
    
    def get_stats(self) -> dict:
        """Get server statistics."""
        with self._lock:
            return {
                "host": self.host,
                "port": self.port,
                "running": self._running,
                "clients_count": len(self._clients),
            }


def create_websocket_client(
    uri: str,
    auto_reconnect: bool = True,
    reconnect_delay: float = 1.0,
    max_reconnect_attempts: int = 5,
    heartbeat_interval: Optional[float] = None
) -> WebSocketClient:
    """
    Create a WebSocket client with common settings.
    
    Args:
        uri: WebSocket server URI
        auto_reconnect: Whether to auto-reconnect on disconnect
        reconnect_delay: Initial delay between reconnect attempts
        max_reconnect_attempts: Maximum number of reconnect attempts
        heartbeat_interval: Heartbeat interval in seconds
        
    Returns:
        Configured WebSocketClient instance
    """
    config = WebSocketConfig(
        uri=uri,
        auto_reconnect=auto_reconnect,
        reconnect_delay=reconnect_delay,
        max_reconnect_attempts=max_reconnect_attempts,
        heartbeat_interval=heartbeat_interval
    )
    return WebSocketClient(config)
