"""
from abc import abstractmethod
Tests for Agent Communication Module
"""

import asyncio
import pytest
from agent_os_kernel.agents.communication import (
    create_messenger,
    create_knowledge_sharing,
    Message,
    MessageType,
)


@pytest.fixture
async def messenger():
    """Create test messenger"""
    m = create_messenger()
    yield m
    await m.clear()


@pytest.fixture
async def knowledge():
    """Create test knowledge sharing"""
    k = create_knowledge_sharing()
    yield k
    await k.clear()


class TestMessenger:
    """Test message passing"""
    
    @pytest.mark.asyncio
    async def test_register_agent(self, messenger):
        """Test agent registration"""
        await messenger.register_agent("test-agent", "TestAgent")
        stats = messenger.get_statistics()
        assert stats["registered_agents"] == 1
    
    @pytest.mark.asyncio
    async def test_send_message(self, messenger):
        """Test sending message"""
        await messenger.register_agent("sender", "Sender")
        await messenger.register_agent("receiver", "Receiver")
        
        msg = Message.create(
            msg_type=MessageType.CHAT,
            sender_id="sender",
            sender_name="Sender",
            content="Hello!",
            receiver_id="receiver"
        )
        
        result = await messenger.send(msg)
        assert result is True
        
        received = await messenger.receive("receiver", timeout=2.0)
        assert received is not None
        assert received.content == "Hello!"
    
    @pytest.mark.asyncio
    async def test_broadcast(self, messenger):
        """Test broadcast message"""
        for i in range(3):
            await messenger.register_agent(f"agent-{i}", f"Agent{i}")
        
        msg = Message.create(
            msg_type=MessageType.NOTIFICATION,
            sender_id="agent-0",
            sender_name="Agent0",
            content="Broadcast message"
        )
        
        result = await messenger.send(msg)
        assert result is True


class TestKnowledgeSharing:
    """Test knowledge sharing"""
    
    @pytest.mark.asyncio
    async def test_share_knowledge(self, knowledge):
        """Test sharing knowledge"""
        from agent_os_kernel.agents.communication.knowledge_share import (
            KnowledgePacket, KnowledgeType
        )
        
        packet = KnowledgePacket.create(
            knowledge_type=KnowledgeType.FACT,
            title="Test Fact",
            content="This is a test fact",
            source_agent="test-agent",
            source_task="test",
            confidence=0.9
        )
        
        packet_id = await knowledge.share(packet)
        assert packet_id is not None
        
        stats = await knowledge.get_statistics()
        assert stats["total_knowledge"] >= 1
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge(self, knowledge):
        """Test retrieving knowledge"""
        from agent_os_kernel.agents.communication.knowledge_share import (
            KnowledgePacket, KnowledgeType
        )
        
        packet = KnowledgePacket.create(
            knowledge_type=KnowledgeType.PROCEDURE,
            title="How to Test",
            content="Step 1: Write test. Step 2: Run test.",
            source_agent="test-agent",
            source_task="testing",
            confidence=0.8,
            tags=["testing", "tutorial"]
        )
        
        await knowledge.share(packet)
        
        results = await knowledge.retrieve("testing", limit=10)
        assert len(results) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
