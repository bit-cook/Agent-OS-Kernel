"""
Command Pattern Implementation

This module provides a generic command pattern implementation for encapsulating
requests as objects, allowing parameterization of clients with queues, requests,
and operations.

Features:
- Command creation and execution
- Command undo functionality
- Command queue for batch processing
- Macro commands for compound operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid
from collections import deque


T = TypeVar('T')


class CommandStatus(Enum):
    """Command execution status"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNDONE = "undone"


@dataclass
class CommandContext:
    """Context information for command execution"""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    priority: int = 0
    timeout_seconds: Optional[float] = None


class Command(ABC):
    """
    Abstract base class for all commands.
    
    Commands encapsulate actions and their parameters as objects,
    allowing for delayed execution, undo operations, and queuing.
    """
    
    def __init__(self, name: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.name = name or f"Command-{self.id[:8]}"
        self._status = CommandStatus.PENDING
        self._context = CommandContext()
        self._result: Optional[Any] = None
        self._error: Optional[Exception] = None
    
    @property
    def status(self) -> CommandStatus:
        """Get current command status"""
        return self._status
    
    @property
    def context(self) -> CommandContext:
        """Get command context"""
        return self._context
    
    @property
    def result(self) -> Optional[Any]:
        """Get command execution result"""
        return self._result
    
    @property
    def error(self) -> Optional[Exception]:
        """Get command error if failed"""
        return self._error
    
    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the command.
        
        Returns:
            The result of the command execution
        """
        pass
    
    @abstractmethod
    def undo(self) -> None:
        """
        Undo the command.
        
        This should reverse the effects of execute().
        """
        pass
    
    def _set_status(self, status: CommandStatus) -> None:
        """Internal method to set command status"""
        self._status = status
    
    def _set_result(self, result: Any) -> None:
        """Internal method to set command result"""
        self._result = result
    
    def _set_error(self, error: Exception) -> None:
        """Internal method to set command error"""
        self._error = error
    
    def can_undo(self) -> bool:
        """
        Check if command can be undone.
        
        Override this in subclasses if undo has conditions.
        """
        return True
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, status={self._status.value})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, name={self.name}, status={self._status.value})"


class SimpleCommand(Command):
    """
    A simple command that wraps a callable with undo support.
    
    Useful for creating commands from existing functions that support undo.
    """
    
    def __init__(
        self,
        execute_fn: callable,
        undo_fn: callable = None,
        name: Optional[str] = None
    ):
        super().__init__(name)
        self._execute_fn = execute_fn
        self._undo_fn = undo_fn
        self._executed = False
    
    def execute(self) -> Any:
        """Execute the wrapped function"""
        self._set_status(CommandStatus.EXECUTING)
        try:
            result = self._execute_fn()
            self._set_result(result)
            self._set_status(CommandStatus.COMPLETED)
            self._executed = True
            return result
        except Exception as e:
            self._set_error(e)
            self._set_status(CommandStatus.FAILED)
            raise
    
    def undo(self) -> None:
        """Execute the undo function if available"""
        if not self._executed:
            return
        
        if self._undo_fn is None:
            return
        
        try:
            self._undo_fn()
            self._set_status(CommandStatus.UNDONE)
        except Exception as e:
            self._set_error(e)
            raise
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return self._executed and self._undo_fn is not None


class ValueCommand(Command):
    """
    A command that modifies a value and supports undo.
    
    Useful for state modification operations.
    """
    
    def __init__(
        self,
        get_value_fn: callable,
        set_value_fn: callable,
        old_value: Any,
        new_value: Any,
        name: Optional[str] = None
    ):
        super().__init__(name)
        self._get_value_fn = get_value_fn
        self._set_value_fn = set_value_fn
        self._old_value = old_value
        self._new_value = new_value
    
    def execute(self) -> Any:
        """Set the value to new_value"""
        self._set_status(CommandStatus.EXECUTING)
        try:
            self._set_value_fn(self._new_value)
            self._set_result(self._new_value)
            self._set_status(CommandStatus.COMPLETED)
            return self._new_value
        except Exception as e:
            self._set_error(e)
            self._set_status(CommandStatus.FAILED)
            raise
    
    def undo(self) -> None:
        """Restore the value to old_value"""
        try:
            self._set_value_fn(self._old_value)
            self._set_status(CommandStatus.UNDONE)
        except Exception as e:
            self._set_error(e)
            raise


class MacroCommand(Command):
    """
    A command that executes a sequence of other commands.
    
    Useful for compound operations that need to be treated as a single unit.
    """
    
    def __init__(self, name: Optional[str] = None):
        super().__init__(name)
        self._commands: List[Command] = []
        self._executed_commands: List[Command] = []
    
    def add_command(self, command: Command) -> None:
        """Add a command to the macro"""
        if command.status == CommandStatus.PENDING:
            self._commands.append(command)
    
    def remove_command(self, command: Command) -> bool:
        """Remove a command from the macro"""
        if command in self._commands:
            self._commands.remove(command)
            return True
        return False
    
    def clear_commands(self) -> None:
        """Remove all commands"""
        self._commands.clear()
        self._executed_commands.clear()
    
    def execute(self) -> List[Any]:
        """Execute all commands in sequence"""
        self._set_status(CommandStatus.EXECUTING)
        results = []
        self._executed_commands.clear()
        
        try:
            for command in self._commands:
                if command.status == CommandStatus.PENDING:
                    result = command.execute()
                    results.append(result)
                    self._executed_commands.append(command)
            
            self._set_result(results)
            self._set_status(CommandStatus.COMPLETED)
            return results
        except Exception as e:
            self._set_error(e)
            self._set_status(CommandStatus.FAILED)
            # Undo already executed commands
            self._undo_executed()
            raise
    
    def _undo_executed(self) -> None:
        """Undo all executed commands in reverse order"""
        for command in reversed(self._executed_commands):
            try:
                command.undo()
            except Exception:
                pass  # Continue with other undos
    
    def undo(self) -> None:
        """Undo all executed commands in reverse order"""
        self._set_status(CommandStatus.EXECUTING)
        try:
            for command in reversed(self._executed_commands):
                command.undo()
            self._set_status(CommandStatus.UNDONE)
        except Exception as e:
            self._set_error(e)
            self._set_status(CommandStatus.FAILED)
            raise
    
    def get_commands(self) -> List[Command]:
        """Get all commands in the macro"""
        return list(self._commands)
    
    def get_executed_commands(self) -> List[Command]:
        """Get all executed commands"""
        return list(self._executed_commands)
    
    def can_undo(self) -> bool:
        """Check if any command can be undone"""
        return len(self._executed_commands) > 0 and all(c.can_undo() for c in self._executed_commands)


class CommandQueue:
    """
    A queue for managing and executing commands in order.
    
    Supports:
    - Queue management (add, remove, clear)
    - Batch execution
    - Undo of last command
    - Undo of all commands
    - Thread-safe operations
    """
    
    def __init__(self, name: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.name = name or f"CommandQueue-{self.id[:8]}"
        self._pending_commands: deque = deque()
        self._executed_commands: List[Command] = []
        self._history_limit: int = 1000
        self._lock = threading.RLock()
        self._on_execute_callbacks: List[callable] = []
        self._on_undo_callbacks: List[callable] = []
    
    def enqueue(self, command: Command) -> str:
        """
        Add a command to the queue.
        
        Args:
            command: The command to add
            
        Returns:
            Command ID
        """
        with self._lock:
            self._pending_commands.append(command)
            return command.id
    
    def enqueue_front(self, command: Command) -> str:
        """
        Add a command to the front of the queue.
        
        Args:
            command: The command to add
            
        Returns:
            Command ID
        """
        with self._lock:
            self._pending_commands.appendleft(command)
            return command.id
    
    def dequeue(self) -> Optional[Command]:
        """
        Remove and return the first command from the queue.
        
        Returns:
            The first command or None if queue is empty
        """
        with self._lock:
            if self._pending_commands:
                return self._pending_commands.popleft()
            return None
    
    def peek(self) -> Optional[Command]:
        """
        Get the first command without removing it.
        
        Returns:
            The first command or None if queue is empty
        """
        with self._lock:
            if self._pending_commands:
                return self._pending_commands[0]
            return None
    
    def execute_next(self) -> Optional[Any]:
        """
        Execute the next command in the queue.
        
        Returns:
            Command result or None if queue is empty
        """
        command = self.dequeue()
        if command is None:
            return None
        
        result = self._execute_command(command)
        return result
    
    def execute_all(self) -> List[Any]:
        """
        Execute all pending commands in the queue.
        
        Returns:
            List of command results
        """
        results = []
        with self._lock:
            while self._pending_commands:
                command = self._pending_commands.popleft()
                result = self._execute_command(command)
                results.append(result)
        return results
    
    def _execute_command(self, command: Command) -> Any:
        """Internal method to execute a command with callbacks"""
        try:
            result = command.execute()
            self._executed_commands.append(command)
            
            # Limit history
            if len(self._executed_commands) > self._history_limit:
                self._executed_commands.pop(0)
            
            # Trigger callbacks
            for callback in self._on_execute_callbacks:
                try:
                    callback(command, result)
                except Exception:
                    pass
            
            return result
        except Exception:
            raise
    
    def undo(self, count: int = 1) -> int:
        """
        Undo the last N executed commands.
        
        Args:
            count: Number of commands to undo
            
        Returns:
            Number of commands actually undone
        """
        undone = 0
        with self._lock:
            for _ in range(min(count, len(self._executed_commands))):
                command = self._executed_commands.pop()
                try:
                    command.undo()
                    undone += 1
                    
                    # Trigger undo callbacks
                    for callback in self._on_undo_callbacks:
                        try:
                            callback(command)
                        except Exception:
                            pass
                except Exception:
                    break
        return undone
    
    def undo_all(self) -> int:
        """
        Undo all executed commands.
        
        Returns:
            Number of commands undone
        """
        return self.undo(len(self._executed_commands))
    
    def clear(self) -> None:
        """Clear pending commands (not executed ones)"""
        with self._lock:
            self._pending_commands.clear()
    
    def clear_all(self) -> None:
        """Clear both pending and executed commands"""
        with self._lock:
            self._pending_commands.clear()
            self._executed_commands.clear()
    
    def get_pending_count(self) -> int:
        """Get the number of pending commands"""
        with self._lock:
            return len(self._pending_commands)
    
    def get_executed_count(self) -> int:
        """Get the number of executed commands"""
        with self._lock:
            return len(self._executed_commands)
    
    def get_total_count(self) -> int:
        """Get the total number of commands"""
        with self._lock:
            return len(self._pending_commands) + len(self._executed_commands)
    
    def get_pending_commands(self) -> List[Command]:
        """Get list of pending commands"""
        with self._lock:
            return list(self._pending_commands)
    
    def get_executed_commands(self) -> List[Command]:
        """Get list of executed commands"""
        with self._lock:
            return list(self._executed_commands)
    
    def on_execute(self, callback: callable) -> None:
        """
        Register a callback to be called after command execution.
        
        Args:
            callback: Function that takes (command, result)
        """
        with self._lock:
            self._on_execute_callbacks.append(callback)
    
    def on_undo(self, callback: callable) -> None:
        """
        Register a callback to be called after command undo.
        
        Args:
            callback: Function that takes (command)
        """
        with self._lock:
            self._on_undo_callbacks.append(callback)
    
    def __len__(self) -> int:
        """Get total command count"""
        return self.get_total_count()
    
    def __bool__(self) -> bool:
        """Check if queue has commands"""
        return self.get_total_count() > 0


class CommandManager:
    """
    A higher-level manager for organizing commands into named queues.
    
    Useful for applications with multiple command streams or undo stacks.
    """
    
    def __init__(self):
        self._queues: Dict[str, CommandQueue] = {}
        self._lock = threading.RLock()
        self._default_queue: Optional[CommandQueue] = None
    
    def create_queue(self, name: str) -> CommandQueue:
        """
        Create a new named queue.
        
        Args:
            name: Unique queue name
            
        Returns:
            The created queue
        """
        with self._lock:
            if name in self._queues:
                raise ValueError(f"Queue '{name}' already exists")
            queue = CommandQueue(name)
            self._queues[name] = queue
            return queue
    
    def get_queue(self, name: str) -> Optional[CommandQueue]:
        """
        Get a queue by name.
        
        Args:
            name: Queue name
            
        Returns:
            The queue or None if not found
        """
        with self._lock:
            return self._queues.get(name)
    
    def remove_queue(self, name: str) -> bool:
        """
        Remove a queue by name.
        
        Args:
            name: Queue name
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._queues:
                del self._queues[name]
                return True
            return False
    
    def get_default_queue(self) -> CommandQueue:
        """Get or create the default queue"""
        if self._default_queue is None:
            self._default_queue = self.create_queue("_default")
        return self._default_queue
    
    def get_all_queues(self) -> List[CommandQueue]:
        """Get all named queues"""
        with self._lock:
            return list(self._queues.values())
    
    def get_queue_count(self) -> int:
        """Get the number of queues"""
        with self._lock:
            return len(self._queues)
    
    def clear_all(self) -> None:
        """Clear all queues"""
        with self._lock:
            for queue in self._queues.values():
                queue.clear_all()
            self._queues.clear()
            self._default_queue = None


# Example usage and demo functions
def create_command_pattern_demo():
    """Create a demonstration of the command pattern"""
    
    # Create a document for editing
    document = {"content": "Hello World"}
    
    # Create commands using SimpleCommand
    def update_content(new_text):
        old_text = document["content"]
        document["content"] = new_text
        return old_text
    
    def restore_content(old_text):
        document["content"] = old_text
    
    # Create a queue
    queue = CommandQueue("DocumentEditor")
    
    # Track changes for demo
    changes = []
    
    def on_execute(cmd, result):
        changes.append(("execute", cmd.name, result))
    
    def on_undo(cmd):
        changes.append(("undo", cmd.name, None))
    
    queue.on_execute(on_execute)
    queue.on_undo(on_undo)
    
    # Create and queue commands
    cmd1 = SimpleCommand(
        lambda: update_content("Hello Python"),
        lambda: restore_content("Hello World"),
        "Change to Hello Python"
    )
    cmd2 = SimpleCommand(
        lambda: update_content("Hello Command Pattern"),
        lambda: restore_content("Hello Python"),
        "Change to Hello Command Pattern"
    )
    cmd3 = SimpleCommand(
        lambda: update_content("Hello OpenClaw"),
        lambda: restore_content("Hello Command Pattern"),
        "Change to Hello OpenClaw"
    )
    
    queue.enqueue(cmd1)
    queue.enqueue(cmd2)
    queue.enqueue(cmd3)
    
    print(f"Document before: {document}")
    print(f"Commands in queue: {queue.get_pending_count()}")
    
    # Execute all commands
    results = queue.execute_all()
    print(f"Document after: {document}")
    print(f"Executed commands: {queue.get_executed_count()}")
    
    # Undo last command
    queue.undo()
    print(f"Document after undo: {document}")
    
    # Undo another command
    queue.undo()
    print(f"Document after another undo: {document}")
    
    # Undo all remaining
    queue.undo_all()
    print(f"Document after undo all: {document}")
    
    return queue, document, changes


def create_macro_command_demo():
    """Demonstrate macro commands"""
    
    # Create some state
    state = {
        "a": 1,
        "b": 2,
        "c": 3
    }
    
    def get_val(key):
        return state[key]
    
    def set_val(key, val):
        state[key] = val
    
    # Create value commands
    cmd1 = ValueCommand(
        lambda: get_val("a"), lambda k, v: set_val(k, v), state["a"], 10, "Set a=10"
    )
    cmd2 = ValueCommand(
        lambda: get_val("b"), lambda k, v: set_val(k, v), state["b"], 20, "Set b=20"
    )
    cmd3 = ValueCommand(
        lambda: get_val("c"), lambda k, v: set_val(k, v), state["c"], 30, "Set c=30"
    )
    
    # Create macro
    macro = MacroCommand("Set All Values")
    macro.add_command(cmd1)
    macro.add_command(cmd2)
    macro.add_command(cmd3)
    
    # Create queue and execute macro
    queue = CommandQueue("MacroDemo")
    queue.enqueue(macro)
    
    print(f"State before: {state}")
    queue.execute_all()
    print(f"State after: {state}")
    
    # Undo the macro
    queue.undo()
    print(f"State after undo: {state}")
    
    return queue, state


if __name__ == "__main__":
    print("=" * 50)
    print("Command Pattern Demo")
    print("=" * 50)
    create_command_pattern_demo()
    
    print("\n" + "=" * 50)
    print("Macro Command Demo")
    print("=" * 50)
    create_macro_command_demo()
