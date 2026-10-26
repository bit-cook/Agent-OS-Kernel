"""测试可观测性"""

from agent_os_kernel.core.observability import Observability, Event, Session, EventType


class TestObservability:
    """测试可观测性"""

    def test_initialization(self):
        """测试初始化"""
        obs = Observability()
        assert obs is not None

    def test_start_session(self):
        """测试启动会话"""
        obs = Observability()
        session = obs.start_session("test-session")

        assert session is not None
        assert session.name == "test-session"
        assert session.status == "running"

    def test_end_session(self):
        """测试结束会话"""
        obs = Observability()
        obs.start_session("test")
        session = obs.end_session()

        assert session is not None
        assert session.status == "completed"

    def test_record_event(self):
        """测试记录事件"""
        obs = Observability()
        obs.start_session("test")

        event = obs.record_event(EventType.TASK_START, agent_id="agent-001")

        assert event is not None
        assert event.type == "task_start"

    def test_get_stats(self):
        """测试获取统计"""
        obs = Observability()
        obs.start_session("test")
        obs.record_event(EventType.TASK_START)

        stats = obs.get_stats()

        assert "total_events" in stats
        assert stats["total_events"] >= 1


class TestEvent:
    """测试事件"""

    def test_create_event(self):
        """测试创建事件"""
        event = Event(id="test-001", type="test")

        assert event.id == "test-001"
        assert event.type == "test"
        assert event.timestamp is not None

    def test_event_to_dict(self):
        """测试事件转字典"""
        event = Event(id="test-001", type="test", data={"key": "value"})

        data = event.to_dict()

        assert data["id"] == "test-001"
        assert data["type"] == "test"
        assert data["data"]["key"] == "value"


class TestSession:
    """测试会话"""

    def test_create_session(self):
        """测试创建会话"""
        session = Session(id="session-001", name="test")

        assert session.id == "session-001"
        assert session.name == "test"
        assert session.status == "running"

    def test_session_to_dict(self):
        """测试会话转字典"""
        session = Session(id="session-001", name="test")

        data = session.to_dict()

        assert data["id"] == "session-001"
        assert data["name"] == "test"
