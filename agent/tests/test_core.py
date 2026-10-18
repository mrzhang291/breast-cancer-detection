"""Agent 核心循环测试：用假模型驱动，不联网。"""
from agent import registry, tools  # noqa: F401
from agent.core import AgentLoop, AgentSession, Completion, FakeProvider, ToolCall


def _ctx():
    class Ctx:
        run_id = 'testrun'
        user_id = '3'
        role_id = 3
        lang = 'zh'
    return Ctx()


def test_tool_call_then_answer():
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id='c1', name='statistics', arguments={})]),
        Completion(content='统计已完成：共 97 条记录。'),
    ])
    session = AgentSession()
    loop = AgentLoop(provider, registry.TOOLS, _ctx(), allowed_tools=['statistics'],
                     max_steps=3)
    result = loop.run(session, '我有多少条记录')

    assert result.stopped == 'answer'
    assert '统计已完成' in result.answer
    assert len(result.steps) == 1
    assert result.steps[0]['tool'] == 'statistics'
    # 工具结果被回灌进对话
    assert any(m['role'] == 'tool' for m in session.messages)


def test_unknown_tool_is_reported():
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id='c1', name='not_a_tool', arguments={})]),
        Completion(content='换个方式回答。'),
    ])
    loop = AgentLoop(provider, registry.TOOLS, _ctx(), allowed_tools=['statistics'],
                     max_steps=3)
    result = loop.run(AgentSession(), '随便问问')
    assert result.stopped == 'answer'
    assert result.steps[0]['verdict'] == 'error'


def test_permission_denied_does_not_crash():
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id='c1', name='export_data', arguments={})]),
        Completion(content='你没有导出权限。'),
    ])
    loop = AgentLoop(provider, registry.TOOLS, _ctx(),
                     allowed_tools=['export_data'], max_steps=3)
    result = loop.run(AgentSession(), '导出数据')
    assert result.stopped == 'answer'
    assert result.steps[0]['ok'] is False
    assert result.steps[0]['verdict'] in ('permission', 'runtime', 'empty')


def test_max_steps_guard():
    script = [Completion(tool_calls=[ToolCall(id='c%d' % i, name='statistics', arguments={})])
              for i in range(5)]
    provider = FakeProvider(script)
    loop = AgentLoop(provider, registry.TOOLS, _ctx(), allowed_tools=['statistics'],
                     max_steps=2)
    result = loop.run(AgentSession(), '一直调工具')
    assert result.stopped == 'max_steps'
    assert len(result.steps) == 2


def test_provider_error_is_caught():
    class Broken:
        def available(self):
            return True

        def complete(self, *args, **kwargs):
            raise RuntimeError('网络错误')

    loop = AgentLoop(Broken(), registry.TOOLS, _ctx(), allowed_tools=['statistics'])
    result = loop.run(AgentSession(), '你好')
    assert result.stopped == 'error'
    assert '模型调用失败' in result.answer
