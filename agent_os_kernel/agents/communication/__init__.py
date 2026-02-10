# Communication Module - Agent 通信与协作

from .messenger import AgentMessenger, Message, MessageType, create_messenger
from .knowledge_share import KnowledgeSharing, KnowledgePacket, create_knowledge_sharing
from .group_chat import GroupChatManager, ChatRole
from .collaboration import AgentCollaboration, TaskType

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
    'AgentCollaboration',
    'TaskType',
]
