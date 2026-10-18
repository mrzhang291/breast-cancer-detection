"""时间区间参数解析：自由文本 → 结构化窗口，带强校验。

设计（对应 Q8=A + 护栏）：
    1. 先用规则解析（覆盖 90% 的说法，且 LLM 关闭时也能工作）
    2. 规则失败且 LLM 可用 → 让模型输出 JSON，再走同一套校验
    3. 校验失败 → 返回 needs_clarify，由上层转成澄清选项
校验是硬约束：模型给什么都不信。
"""
import json
import re
from typing import Dict, List, Optional

MAX_LIMIT = 30
MAX_DAYS = 365
MIN_VALUE = 1

_CN_NUM = {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
           '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def _to_int(token: str) -> Optional[int]:
    token = (token or '').strip()
    if token.isdigit():
        return int(token)
    if token in _CN_NUM:
        return _CN_NUM[token]
    return None


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _clean(mode: str, n: Optional[int]) -> Dict:
    """统一出口：任何来源的参数都必须经过这里。"""
    if mode not in ('limit', 'days', 'all'):
        return {'ok': False, 'reason': 'unknown_mode'}
    if mode == 'all':
        return {'ok': True, 'mode': 'all', 'n': MAX_LIMIT}
    if n is None:
        return {'ok': False, 'reason': 'missing_n'}
    if not isinstance(n, int) or n < MIN_VALUE:
        return {'ok': False, 'reason': 'invalid_n'}
    capped = _clamp(n, MIN_VALUE, MAX_LIMIT if mode == 'limit' else MAX_DAYS)
    return {'ok': True, 'mode': mode, 'n': capped, 'capped': capped != n}


def parse_rules(text: str) -> Optional[Dict]:
    """规则解析。命中返回已校验结果，否则 None。"""
    t = (text or '').strip()

    if re.search(r'(全部|所有|所有记录|全部记录)', t):
        return _clean('all', MAX_LIMIT)

    m = re.search(r'最近\s*([0-9]+|[一二两三四五六七八九十])\s*(次|条|个|份)', t)
    if m:
        return _clean('limit', _to_int(m.group(1)))

    m = re.search(r'(最后|最近|前)\s*([0-9]+|[一二两三四五六七八九十])\s*(次|条|个|份)', t)
    if m:
        return _clean('limit', _to_int(m.group(2)))

    m = re.search(r'最近\s*([0-9]+|[一二两三四五六七八九十])\s*(天|日|周|星期|个月|月)', t)
    if m:
        n = _to_int(m.group(1))
        unit = m.group(2)
        if n is None:
            return None
        if unit in ('周', '星期'):
            n *= 7
        elif unit in ('月', '个月'):
            n *= 30
        return _clean('days', n)

    return None


def parse_llm(text: str) -> Optional[Dict]:
    """让模型输出 JSON 参数（可选路径，失败即返回 None）。"""
    try:
        from . import llm
    except Exception:  # noqa: BLE001
        return None
    if not getattr(llm, 'enabled', lambda: False)():
        return None
    prompt = (
        '把用户的问题转换成 JSON，只输出 JSON，不要解释。格式：\n'
        '{"mode": "limit"|"days"|"all", "n": 整数}\n'
        'mode=limit 表示最近 n 条记录；mode=days 表示最近 n 天；mode=all 表示全部。\n'
        '用户问题：%s' % text
    )
    try:
        raw = llm.complete(prompt, max_tokens=80) or ''
        match = re.search(r'\{.*\}', raw, re.S)
        if not match:
            return None
        data = json.loads(match.group(0))
        return _clean(str(data.get('mode')), data.get('n'))
    except Exception:  # noqa: BLE001
        return None


def parse_range(text: str) -> Dict:
    """对外入口。返回 {'ok': bool, 'mode', 'n', 'needs_clarify'}。"""
    ruled = parse_rules(text)
    if ruled and ruled.get('ok'):
        return ruled
    llmed = parse_llm(text)
    if llmed and llmed.get('ok'):
        return llmed
    return {'ok': False, 'needs_clarify': True, 'reason': 'unparsed'}


def wants_range(text: str) -> bool:
    """这句话是不是在要一个"区间汇总"而不是单次报告。"""
    t = (text or '').lower()
    hints = ('最近', '区间', '整理', '小结', '汇总', '这段时间', '以来', '历史')
    return any(h in t for h in hints)


CLARIFY_OPTIONS: List[str] = ['最近 3 次', '最近 30 天', '全部记录']
