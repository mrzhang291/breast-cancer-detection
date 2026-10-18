"""流式 provider：DeepSeek SSE，逐 token 产出 content / tool_call_delta / finish。"""
import json
from typing import Dict, Generator, List, Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from .provider import API_URL, MODEL, DeepSeekProvider


class StreamingDeepSeekProvider(DeepSeekProvider):
    def stream_complete(self, messages: List[Dict], tools: Optional[List[Dict]] = None,
                        temperature: float = 0.2,
                        max_tokens: int = 900) -> Generator:
        if not self.available():
            raise RuntimeError('DeepSeek API 未配置')

        payload: Dict = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': True,
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        resp = requests.post(
            API_URL,
            headers={'Authorization': 'Bearer %s' % self.api_key,
                     'Content-Type': 'application/json'},
            json=payload, timeout=self.timeout, stream=True,
        )
        if resp.status_code >= 400:
            raise RuntimeError('DeepSeek HTTP %d: %s' % (resp.status_code, resp.text[:160]))

        for raw in resp.iter_lines(decode_unicode=False):
            if not raw:
                continue
            line = raw.decode('utf-8', 'ignore').strip()
            if line.startswith('data:'):
                line = line[5:].strip()
            if not line:
                continue
            if line == '[DONE]':
                break
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            choices = obj.get('choices') or []
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get('delta') or {}
            if delta.get('content'):
                yield ('content', delta['content'])
            for call in delta.get('tool_calls') or []:
                yield ('tool_call_delta', call)
            if choice.get('finish_reason'):
                yield ('finish', choice['finish_reason'])


class StreamingFakeProvider:
    """测试用：给定事件序列，模拟流式输出。"""

    def __init__(self, rounds):
        self.rounds = list(rounds)
        self.calls = []

    def available(self):
        return True

    def stream_complete(self, messages, tools=None, temperature=0.2, max_tokens=900):
        self.calls.append(list(messages))
        events = self.rounds.pop(0) if self.rounds else [('finish', 'stop')]
        for event in events:
            yield event
