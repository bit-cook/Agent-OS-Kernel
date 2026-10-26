# Communication Module - Agent 通信与协作

from .messenger import AgentMessenger, Message, MessageType, create_messenger
from .knowledge_share import KnowledgeSharing, KnowledgePacket, create_knowledge_sharing
from .group_chat import GroupChatManager, ChatRole, create_group_chat_manager
from .collaboration import AgentCollaboration, TaskType, create_collaboration

__all__ = [
    'AgentMessenger',
    'Message',
    'MessageType',
    'create_messenger',
    'KnowledgeSharing',
    'KnowledgePacket',
    'create_knowledge_sharing',
    'GroupChatManager',
    'ChatRole',
    'create_group_chat_manager',
    'AgentCollaboration',
    'TaskType',
    'create_collaboration',
]
