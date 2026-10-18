"""模型提供方：DeepSeek function calling + 测试用假模型。

只要实现 complete(messages, tools) -> Completion 就能接进循环。
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict = field(default_factory=dict)

    def to_message(self) -> Dict:
        return {
            'id': self.id,
            'type': 'function',
            'function': {
                'name': self.name,
                'arguments': json.dumps(self.arguments, ensure_ascii=False),
            },
        }

    @classmethod
    def from_message(cls, raw: Dict) -> 'ToolCall':
        fn = (raw or {}).get('function') or {}
        raw_args = fn.get('arguments')
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args or '{}')
            except ValueError:
                raw_args = {}
        return cls(id=(raw or {}).get('id') or '', name=fn.get('name') or '',
                   arguments=raw_args or {})


@dataclass
class Completion:
    content: str = ''
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = 'stop'
    usage: Dict = field(default_factory=dict)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class DeepSeekProvider:
    """真实的 DeepSeek 调用（function calling）。"""

    def __init__(self, api_key: str = '', model: str = MODEL, timeout: float = 60.0):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY', '').strip()
        self.model = model
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key) and requests is not None

    def complete(self, messages: List[Dict], tools: Optional[List[Dict]] = None,
                 temperature: float = 0.2, max_tokens: int = 900) -> Completion:
        if not self.available():
            raise RuntimeError('DeepSeek API 未配置')

        payload: Dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        resp = requests.post(
            API_URL,
            headers={'Authorization': 'Bearer %s' % self.api_key,
                     'Content-Type': 'application/json'},
            json=payload, timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise RuntimeError('DeepSeek HTTP %d: %s' % (resp.status_code, resp.text[:160]))

        data = resp.json()
        choice = (data.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        calls = [ToolCall.from_message(item) for item in (message.get('tool_calls') or [])]
        return Completion(
            content=message.get('content') or '',
            tool_calls=[c for c in calls if c.name],
            finish_reason=choice.get('finish_reason') or 'stop',
            usage=data.get('usage') or {},
        )


class FakeProvider:
    """测试用：按脚本返回预设的 Completion 序列。"""

    def __init__(self, script: List[Completion]):
        self.script = list(script)
        self.calls: List[Dict] = []

    def available(self) -> bool:
        return True

    def complete(self, messages: List[Dict], tools=None,
                 temperature: float = 0.2, max_tokens: int = 900) -> Completion:
        self.calls.append({'messages': list(messages), 'tools': tools})
        if not self.script:
            return Completion(content='（脚本用尽）')
        return self.script.pop(0)
