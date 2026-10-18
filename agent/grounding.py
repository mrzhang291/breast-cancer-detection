"""溯源接地：把答案拆成句子，逐句绑定事实来源。

目标（P0-1）：
    - 含数字的句子，数字必须能在 facts 里找到，否则整句丢弃
    - 含结论的句子，必须能映射到某类事实（预测/归因/统计/条款）
    - 映射不到的句子标记为「推断」，不混进有出处的结论里
"""
import re
from typing import Dict, List, Optional

from .policy import extract_numbers, fact_numbers

# 判定类关键词 -> 需要的事实类别
CLAIM_KINDS = [
    ('prediction', ('良性', '恶性', '判为', '结论', '结果提示')),
    ('confidence', ('置信度', '概率')),
    ('feature', ('特征', '凹度', '凹点', '面积', '半径', '纹理', '对称', '分形', '周长', '平滑', '紧凑')),
    ('record', ('记录', '条', '历史', '样本')),
    ('clause', ('条款', '指南', '文档', '知识库', '依据')),
]

# 建议/提示类句子不算断言，不要求出处
ADVICE_WORDS = ('建议', '请', '注意', '随访', '就医', '复查', '可以', '如需', '仅供')

_SENT_SPLIT = re.compile(r'(?<=[。！？!?；;])')


def split_sentences(text: str) -> List[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text or '') if p and p.strip()]
    return parts


def _has_advice(sentence: str) -> bool:
    return any(word in sentence for word in ADVICE_WORDS)


def _claim_kinds(sentence: str) -> List[str]:
    kinds = []
    for kind, words in CLAIM_KINDS:
        if any(word in sentence for word in words):
            kinds.append(kind)
    return kinds


def _fact_payloads(facts: List[Dict]) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for fact in facts or []:
        kind = fact.get('kind')
        if kind and kind not in out:
            out[kind] = fact.get('payload') or {}
    return out


def _source_label(kind: str, payload: Dict, citations: List[str]) -> str:
    if kind == 'prediction':
        return '预测 %s %.2f%%' % (payload.get('output', ''),
                                   float(payload.get('confidence') or 0) * 100)
    if kind == 'shap':
        tops = payload.get('top_features') or []
        name = (tops[0] or {}).get('name_zh') or (tops[0] or {}).get('name') or ''
        return '归因 Top%d%s' % (len(tops), ('：' + name) if name else '')
    if kind == 'stat':
        return '统计 %s 条' % payload.get('total', '—')
    if kind == 'case':
        return '相似病例 %d 条' % len(payload.get('cases') or [])
    if kind == 'clause':
        return '条款 %s' % ('、'.join(citations[:2]) if citations else '')
    if kind == 'input':
        return '输入 30 项'
    if kind == 'uncertainty':
        return '证据档位 %s' % payload.get('tier', '')
    if kind == 'record':
        return '记录'
    if kind == 'sessions':
        return '会话统计'
    return kind


def ground(answer_md: str, facts: List[Dict],
           citations: Optional[List[str]] = None) -> Dict:
    """返回 {ok, coverage, claims, dropped, unsupported, answer_md}。"""
    citations = list(citations or [])
    payloads = _fact_payloads(facts)
    pool = fact_numbers(facts or [])

    kept: List[str] = []
    claims: List[Dict] = []
    dropped: List[str] = []
    unsupported: List[str] = []
    claim_total = 0
    supported_total = 0

    for sentence in split_sentences(answer_md):
        numbers = [v for v in extract_numbers(sentence)
                   if not (v == int(v) and abs(v) <= 40)]
        bad_numbers = [v for v in numbers if not _matches_any(v, pool)]
        if bad_numbers:
            dropped.append(sentence)
            continue

        kinds = _claim_kinds(sentence)
        advice = _has_advice(sentence)
        sources = []
        if kinds:
            for kind in kinds:
                if kind == 'clause' and citations:
                    sources.append({'kind': 'clause', 'label': '条款 ' + '、'.join(citations[:2])})
                elif kind == 'confidence' and 'prediction' in payloads:
                    sources.append({'kind': 'prediction',
                                    'label': _source_label('prediction', payloads['prediction'], citations)})
                elif kind in payloads:
                    sources.append({'kind': kind,
                                    'label': _source_label(kind, payloads[kind], citations)})

        seen = set()
        deduped = []
        for src in sources:
            if src['label'] not in seen:
                seen.add(src['label'])
                deduped.append(src)
        sources = deduped

        if kinds and not advice:
            claim_total += 1
            if sources:
                supported_total += 1
            else:
                unsupported.append(sentence)

        text = sentence
        if kinds and not advice and not sources:
            text = sentence.rstrip('。；;') + '（推断）。'
        kept.append(text)
        claims.append({'sentence': sentence, 'sources': sources,
                       'advice': advice, 'supported': bool(sources) or advice})

    coverage = round(supported_total / claim_total, 3) if claim_total else 1.0
    answer = ''.join(kept).strip() or answer_md
    return {
        'ok': not dropped and coverage >= 0.6,
        'coverage': coverage,
        'claims': claims,
        'dropped': dropped[:5],
        'dropped_count': len(dropped),
        'unsupported': unsupported[:5],
        'answer_md': answer,
    }


def _matches_any(value: float, pool: List[float]) -> bool:
    for candidate in pool:
        for form in (candidate, candidate * 100.0, candidate / 100.0, 1.0 - candidate):
            tolerance = max(0.02, abs(form) * 0.002)
            if abs(value - form) <= tolerance:
                return True
    return False
