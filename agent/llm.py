"""大模型适配层（可完全离线）。

设计原则：
    数值型回答永远走模板，不经过模型；模型只用于"叙述型"问题的措辞润色。
    这样即使 API 不可用、或模型胡编，也不会污染关键数字。
"""
import json
import os
import threading
import time
from typing import Dict, List, Optional

try:  # requests 是项目既有依赖
    import requests
except Exception:  # pragma: no cover
    requests = None

_API_URL = 'https://api.deepseek.com/v1/chat/completions'
_MODEL = 'deepseek-chat'

_LOCK = threading.Lock()
_STATE: Dict = {'checked_at': 0.0, 'available': False}


def _api_key() -> str:
    return os.environ.get('DEEPSEEK_API_KEY', '').strip()


def mode() -> str:
    """auto / off / api"""
    return os.environ.get('AGENT_LLM', 'auto').strip().lower() or 'auto'


def available(timeout: float = 3.0) -> bool:
    """探测模型是否可用（结果缓存 60 秒）。"""
    if mode() == 'off':
        return False
    if not _api_key() or requests is None:
        return False
    if mode() == 'api':
        return True

    with _LOCK:
        if time.time() - _STATE['checked_at'] < 60:
            return _STATE['available']
        _STATE['checked_at'] = time.time()
        try:
            resp = requests.post(
                _API_URL,
                headers={'Authorization': 'Bearer %s' % _api_key(),
                         'Content-Type': 'application/json'},
                json={'model': _MODEL, 'messages': [{'role': 'user', 'content': 'ping'}],
                      'max_tokens': 1},
                timeout=timeout,
            )
            _STATE['available'] = resp.status_code < 500
        except Exception:
            _STATE['available'] = False
        return _STATE['available']


def complete(system: str, user: str, temperature: float = 0.2,
             max_tokens: int = 900) -> Optional[str]:
    """返回文本；不可用时返回 None（调用方走模板）。"""
    if not available():
        return None
    try:
        resp = requests.post(
            _API_URL,
            headers={'Authorization': 'Bearer %s' % _api_key(),
                     'Content-Type': 'application/json'},
            json={
                'model': _MODEL,
                'messages': [{'role': 'system', 'content': system},
                             {'role': 'user', 'content': user}],
                'temperature': temperature,
                'max_tokens': max_tokens,
            },
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content']
    except Exception:
        return None


def usage() -> Dict:
    return {'mode': mode(), 'available': available(), 'model': _MODEL}
