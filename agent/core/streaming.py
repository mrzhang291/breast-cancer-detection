"""流式 agent：把模型输出、工具调用、工具结果实时推给前端。

与同步版的区别：
    - provider 走 stream=True，逐 token 产出
    - 循环在两次模型调用之间执行工具，并把调用/结果作为事件抛出
    - 前端能按顺序看到：开始 → 模型输出 → 调工具 → 工具结果 → 继续 → 最终答案
"""
import json
import time
from typing import Dict, Generator, List, Optional

from .loop import AgentLoop
from .provider import ToolCall


def _extract_sub_steps(output: str):
    """子代理返回的 JSON 里带 steps 时，抽出来单独展示。"""
    try:
        data = json.loads(output or '{}')
    except ValueError:
        return []
    steps = data.get('steps') or []
    out = []
    for step in steps[:5]:
        tool = step.get('tool') or ''
        out.append({'tool': tool,
                    'label': tool.replace('_', ' '),
                    'ok': bool(step.get('ok')),
                    'verdict': step.get('verdict') or '',
                    'latency_ms': step.get('latency_ms') or 0})
    return out

class StreamingAgentLoop(AgentLoop):
    """在 AgentLoop 基础上增加 stream()，事件与同步版语义一致。"""

    def _event(self, kind: str, payload: Dict) -> None:
        if self.emit:
            try:
                self.emit(kind, payload)
            except Exception:  # noqa: BLE001
                pass

    def stream(self, session, question: str) -> Generator[Dict, None, None]:
        session.user(question)
        yield {'event': 'start', 'data': {'question': question}}

        provider = self.provider
        if not hasattr(provider, 'stream_complete'):
            # 退化为同步：至少把结果一次性给出
            result = self.run(session, question)
            yield {'event': 'answer', 'data': {'delta': result.answer}}
            yield {'event': 'done', 'data': {'stopped': result.stopped,
                                             'steps': self.steps}}
            return

        for step in range(self.max_steps):
            content_parts: List[str] = []
            calls: Dict[int, Dict] = {}
            finish = 'stop'

            yield {'event': 'thinking', 'data': {'step': step + 1}}

            try:
                for kind, payload in provider.stream_complete(
                        session.messages, tools=self.tools,
                        max_tokens=session.max_tokens):
                    if kind == 'content':
                        content_parts.append(payload)
                        yield {'event': 'token', 'data': {'delta': payload}}
                    elif kind == 'tool_call_delta':
                        index = int(payload.get('index') or 0)
                        slot = calls.setdefault(index, {'id': '', 'name': '', 'arguments': ''})
                        if payload.get('id'):
                            slot['id'] = payload['id']
                        fn = payload.get('function') or {}
                        if fn.get('name'):
                            slot['name'] = fn['name']
                        if fn.get('arguments'):
                            slot['arguments'] += fn['arguments']
                    elif kind == 'finish':
                        finish = payload or 'stop'
            except Exception as exc:  # noqa: BLE001
                yield {'event': 'error', 'data': {'message': '模型调用失败：%s' % str(exc)[:120]}}
                return

            content = ''.join(content_parts)
            tool_calls = []
            for index in sorted(calls):
                slot = calls[index]
                if not slot.get('name'):
                    continue
                try:
                    args = json.loads(slot.get('arguments') or '{}')
                except ValueError:
                    args = {}
                tool_calls.append(ToolCall(id=slot.get('id') or 'call_%d' % index,
                                           name=slot['name'], arguments=args))

            if not tool_calls:
                session.assistant(content)
                yield {'event': 'done', 'data': {'stopped': 'answer', 'steps': self.steps,
                                                 'content': content}}
                return

            session.assistant(content, tool_calls)

            for call in tool_calls:
                yield {'event': 'tool_call', 'data': {'tool': call.name,
                                                      'args': call.arguments}}
                started = time.time()
                output = self._run_tool(call)
                sub_steps = _extract_sub_steps(output)
                if sub_steps:
                    yield {'event': 'sub_steps', 'data': {'tool': call.name,
                                                          'steps': sub_steps}}
                yield {'event': 'tool_result', 'data': {
                    'tool': call.name,
                    'ok': self.steps[-1]['ok'] if self.steps else False,
                    'latency_ms': int((time.time() - started) * 1000),
                    'preview': output[:220],
                }}
                session.tool(call.id, call.name, output)

        yield {'event': 'error', 'data': {'message': '达到步数上限'}}
        yield {'event': 'done', 'data': {'stopped': 'max_steps', 'steps': self.steps}}
