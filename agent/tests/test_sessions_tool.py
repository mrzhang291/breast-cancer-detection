"""sessions 工具测试。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent import db, registry, tools  # noqa: F401


def _ctx():
    class Ctx:
        run_id = 'sesstest'
        user_id = '3'
        role_id = 3
        facts = []

        def add_fact(self, fact):
            self.facts.append(fact)
    return Ctx()


def test_sessions_tool_counts_messages():
    db.init_schema()
    sid = db.create_session('3', '工具测试')
    db.add_message(sid, 'user', '你好')
    db.add_message(sid, 'assistant', '你好呀')
    try:
        result = registry.call_tool(_ctx(), 'sessions', {})
        assert result.ok
        assert result.data['sessions_total'] >= 1
        assert result.data['messages_total'] >= 2
        assert result.data['active_days'] >= 1
        assert isinstance(result.data['recent_sessions'], list)
    finally:
        db.delete_session(sid, '3')


def test_sessions_tool_empty_user():
    db.init_schema()
    result = registry.call_tool(_ctx(), 'sessions', {})
    assert result.ok
    assert 'sessions_total' in result.data
