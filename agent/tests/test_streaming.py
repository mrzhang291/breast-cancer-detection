"""流式 agent 测试：事件顺序、工具调用、子代理步骤。"""
from agent import registry, tools  # noqa: F401
from agent.core.streaming import StreamingAgentLoop
from agent.core.streaming_provider import StreamingFakeProvider


class Ctx:
    run_id = 'streamrun'
    user_id = '3'
    role_id = 3
    lang = 'zh'


def _stream_events(provider, allowed, max_steps=3, question='测试'):
    loop = StreamingAgentLoop(provider, registry.TOOLS, Ctx(),
                              allowed_tools=allowed, max_steps=max_steps)
    from agent.core.session import AgentSession
    session = AgentSession()
    events = []
    for item in loop.stream(session, question):
        events.append(item['event'])
    return events


def test_stream_order_tool_then_answer():
    provider = StreamingFakeProvider([
        [
            ('tool_call_delta', {'index': 0, 'id': 'c1',
                                 'function': {'name': 'statistics', 'arguments': '{}'}}),
            ('finish', 'tool_calls'),
        ],
        [
            ('content', '你共有 '),
            ('content', '97 条记录。'),
            ('finish', 'stop'),
        ],
    ])
    events = _stream_events(provider, ['statistics'])
    assert events[0] == 'start'
    assert 'thinking' in events
    assert 'tool_call' in events
    assert 'tool_result' in events
    assert 'token' in events
    assert events[-1] == 'done'


def test_stream_stops_at_max_steps():
    rounds = []
    for i in range(4):
        rounds.append([
            ('tool_call_delta', {'index': 0, 'id': 'c%d' % i,
                                 'function': {'name': 'statistics', 'arguments': '{}'}}),
            ('finish', 'tool_calls'),
        ])
    provider = StreamingFakeProvider(rounds)
    events = _stream_events(provider, ['statistics'], max_steps=2)
    assert events[-1] == 'done'
    assert events.count('tool_call') == 2


def test_stream_rejects_tool_outside_whitelist():
    provider = StreamingFakeProvider([
        [('tool_call_delta', {'index': 0, 'id': 'c1',
                              'function': {'name': 'export_data', 'arguments': '{}'}}),
         ('finish', 'tool_calls')],
        [('content', '没有权限。'), ('finish', 'stop')],
    ])
    loop = StreamingAgentLoop(provider, registry.TOOLS, Ctx(),
                              allowed_tools=['statistics'], max_steps=2)
    from agent.core.session import AgentSession
    events = [item['event'] for item in loop.stream(AgentSession(), '导出')]
    assert 'tool_result' in events
    assert loop.steps[0]['verdict'] == 'unknown_tool'


def test_stream_falls_back_to_sync_when_provider_has_no_stream():
    class SyncOnly:
        def available(self):
            return True

        def complete(self, messages, tools=None, temperature=0.2, max_tokens=900):
            from agent.core.provider import Completion
            return Completion(content='同步回答')

    loop = StreamingAgentLoop(SyncOnly(), registry.TOOLS, Ctx(),
                              allowed_tools=['statistics'], max_steps=1)
    from agent.core.session import AgentSession
    events = [item['event'] for item in loop.stream(AgentSession(), '你好')]
    assert 'answer' in events and events[-1] == 'done'
