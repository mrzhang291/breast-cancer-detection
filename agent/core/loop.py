"""模型 ↔ 工具 的执行循环。

约束（与主项目一致，宁可少做也不乱做）：
    - 步数上限，避免无限工具调用
    - 每次工具调用都过 registry 的权限/参数校验
    - 工具失败把错误回灌给模型，由模型决定是否换路子
    - 任何异常都收敛成可读回答，不把栈抛给前端
"""
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .schemas import build_tools
from .session import AgentSession


@dataclass
class LoopResult:
    answer: str
    steps: List[Dict] = field(default_factory=list)
    stopped: str = 'answer'          # answer | max_steps | error
    usage: Dict = field(default_factory=dict)


class AgentLoop:
    def __init__(self, provider, registry_tools: Dict, ctx,
                 allowed_tools: Optional[List[str]] = None,
                 max_steps: int = 6,
                 emit: Optional[Callable] = None):
        self.provider = provider
        self.registry_tools = registry_tools
        self.ctx = ctx
        self.allowed = set(allowed_tools) if allowed_tools is not None else None
        self.tools = build_tools(registry_tools, allowed_tools)
        self.max_steps = max_steps
        self.emit = emit
        self.steps: List[Dict] = []

    # ------------------------------------------------------------------
    def _event(self, kind: str, payload: Dict) -> None:
        if self.emit:
            try:
                self.emit(kind, payload)
            except Exception:  # noqa: BLE001
                pass

    def _run_tool(self, call) -> str:
        from .. import registry

        started = time.time()
        # 白名单必须在执行处再校验一次：模型可能被诱导调用未授权工具
        if self.allowed is not None and call.name not in self.allowed:
            self.steps.append({'tool': call.name, 'args': call.arguments or {},
                               'ok': False, 'latency_ms': 0, 'verdict': 'unknown_tool'})
            self._event('step', {'tool': call.name, 'ok': False, 'latency_ms': 0})
            return json.dumps({'error': '未授权工具: %s' % call.name}, ensure_ascii=False)

        spec = self.registry_tools.get(call.name)
        if spec is None:
            self.steps.append({'tool': call.name, 'args': call.arguments or {},
                               'ok': False, 'latency_ms': 0, 'verdict': 'unknown_tool'})
            self._event('step', {'tool': call.name, 'ok': False, 'latency_ms': 0})
            return json.dumps({'error': '未知工具: %s' % call.name}, ensure_ascii=False)

        result = registry.call_tool(self.ctx, call.name, call.arguments or {})
        latency = int((time.time() - started) * 1000)

        self.steps.append({
            'tool': call.name,
            'args': call.arguments or {},
            'ok': bool(result.ok),
            'latency_ms': latency,
            'verdict': 'ok' if result.ok else (result.error_type or 'error'),
        })
        self._event('step', {'tool': call.name, 'ok': bool(result.ok),
                             'latency_ms': latency,
                             'args': call.arguments or {}})

        if not result.ok:
            return json.dumps({'error': result.error or '工具执行失败',
                               'error_type': result.error_type},
                              ensure_ascii=False)
        try:
            return json.dumps(result.data, ensure_ascii=False, default=str)[:1800]
        except (TypeError, ValueError):
            return str(result.data)[:1800]

    # ------------------------------------------------------------------
    def run(self, session: AgentSession, question: str) -> LoopResult:
        session.user(question)
        self._event('user', {'question': question})

        for step in range(self.max_steps):
            try:
                completion = self.provider.complete(
                    session.messages, tools=self.tools,
                    max_tokens=session.max_tokens)
            except Exception as exc:  # noqa: BLE001
                self._event('error', {'message': str(exc)[:200]})
                return LoopResult(answer='模型调用失败：%s' % str(exc)[:120],
                                  steps=self.steps, stopped='error')

            usage = completion.usage or {}
            if usage:
                last = session.meta.setdefault('usage', {})
                for key, value in usage.items():
                    if isinstance(value, (int, float)):
                        last[key] = last.get(key, 0) + value

            if not completion.wants_tools:
                answer = completion.content or ''
                self._event('answer', {'content': answer[:200]})
                return LoopResult(answer=answer, steps=self.steps,
                                  stopped='answer', usage=session.meta.get('usage', {}))

            session.assistant(completion.content, completion.tool_calls)

            for call in completion.tool_calls:
                self._event('tool_call', {'tool': call.name, 'args': call.arguments})
                output = self._run_tool(call)
                session.tool(call.id, call.name, output)

        self._event('error', {'message': '达到步数上限'})
        return LoopResult(answer='这次问题需要的步骤太多，我先停在这里。'
                                 '可以把它拆成更小的问题再问我。',
                          steps=self.steps, stopped='max_steps',
                          usage=session.meta.get('usage', {}))
