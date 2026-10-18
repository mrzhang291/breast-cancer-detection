"""claim ↔ fact 对账。

生成层允许组织语言，但不允许发明数字。这里把回答里的数值逐个拿去和
facts 比对，对不上就打回重写；重写仍不合格则降级为模板答案。
"""
import re
from typing import Dict, List

from .policy import extract_numbers, fact_numbers

# 计数类整数（特征数、条数、序号）不参与对账
IGNORE_INT_MAX = 40

# 时间戳、run_id 不是医学断言，不参与对账
_META_PATTERNS = [
    re.compile(r'\d{4}-\d{2}-\d{2}'),          # 2026-10-18
    re.compile(r'\d{1,2}:\d{2}(?::\d{2})?'),   # 15:47:44
    re.compile(r'\b[0-9a-f]{8,}\b'),           # run_id
]


def strip_meta(text: str) -> str:
    cleaned = text or ''
    for pattern in _META_PATTERNS:
        cleaned = pattern.sub(' ', cleaned)
    return cleaned


def _matches(value: float, pool: List[float], tol: float = 0.02) -> bool:
    for candidate in pool:
        # 百分比形态：0.9737 -> 97.37
        forms = [candidate, candidate * 100.0, candidate / 100.0, 1.0 - candidate]
        for form in forms:
            scale = max(abs(form), 1.0)
            if abs(value - form) <= max(tol, 0.01 * scale):
                return True
    return False


def verify_answer(answer_md: str, facts: List[Dict]) -> Dict:
    """返回 {ok, checked, unmatched}。"""
    pool = fact_numbers(facts)
    numbers = extract_numbers(strip_meta(answer_md))

    checked = 0
    unmatched: List[float] = []
    for value in numbers:
        if value == int(value) and abs(value) <= IGNORE_INT_MAX:
            continue  # 计数/序号，不对账
        checked += 1
        if not _matches(value, pool):
            unmatched.append(value)

    return {
        'ok': not unmatched,
        'checked': checked,
        'unmatched': unmatched[:10],
    }
