"""子代理测试：用假模型验证委派链路。"""
import pytest

from agent import registry, tools  # noqa: F401
from agent.core import Completion, FakeProvider, ToolCall
from agent.core.subagent import ANALYST, run_subagent


class Ctx:
    run_id = 'subrun'
    user_id = '3'
    role_id = 3
    lang = 'zh'


def test_subagent_returns_answer():
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id='c1', name='statistics', arguments={})]),
        Completion(content='你共有 97 条记录，其中恶性 41 条。'),
    ])
    result = run_subagent('统计一下我的记录', Ctx(), spec=ANALYST, provider=provider)
    assert result['ok'] is True
    assert '97' in result['answer']
    assert result['steps'][0]['tool'] == 'statistics'


def test_subagent_cannot_delegate_again():
    # analyst 白名单里没有 delegate，模型即使想调也会被当作未知工具
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id='c1', name='delegate', arguments={'task': '再来一层'})]),
        Completion(content='我不能再委派。'),
    ])
    result = run_subagent('递归一下', Ctx(), spec=ANALYST, provider=provider)
    assert result['ok'] is True
    assert result['steps'][0]['verdict'] == 'unknown_tool'


def test_subagent_reports_unavailable_without_provider():
    class Dead:
        def available(self):
            return False

    result = run_subagent('随便', Ctx(), spec=ANALYST, provider=Dead())
    assert result['ok'] is False
    assert result['stopped'] == 'unavailable'
