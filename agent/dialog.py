"""多轮对话规划：指代解析、意图延续、对比识别、澄清追问。

这一层不碰模型，只做对话结构判断，保证没有 LLM 也能工作。
"""
from typing import Dict, List, Optional

COMPARE_HINTS = ('对比', '比较', '差在哪', '差异', '区别', '和上次', '跟上次', '比上次', '变化')

REFER_WORDS = ('它', '这个', '这条', '这次', '该', '上面', '刚才', '那它', '那条', '这份')

FOLLOW_HINTS = ('为什么', '怎么说', '还有呢', '继续', '详细', '展开', '依据', '证据', '具体', '然后呢')

CLARIFY_OPTIONS = [
    '解释这次预测结果',
    '对比这次和上一次记录',
    '这类病例一共多少条',
    '怎么填写这些特征',
]


def looks_compare(text: str) -> bool:
    return any(h in text for h in COMPARE_HINTS)


def is_bare_reference(text: str) -> bool:
    """「它呢」「为什么」「展开说说」这类没有明确主语的追问。"""
    t = (text or '').strip()
    if not t:
        return True
    if len(t) <= 8 and (any(w in t for w in REFER_WORDS) or any(w in t for w in FOLLOW_HINTS)):
        return True
    return len(t) <= 4 and t.endswith(('呢', '吗', '？', '?'))


def plan(question: str, history: Optional[List[Dict]] = None,
         context: Optional[Dict] = None, has_values: bool = False) -> Dict:
    """决定这一轮怎么处理。

    返回:
        mode: normal | followup | compare | clarify
        inherit: 需要沿用的意图键（interpret / feature / ...）
        text: 澄清时给用户的话
        options: 澄清时可点的选项
    """
    text = (question or '').strip()
    history = history or []
    context = context or {}
    last = history[-1] if history else {}

    if looks_compare(text):
        if has_values or context.get('record_id') or history:
            return {'mode': 'compare', 'inherit': None, 'text': '', 'options': []}
        return {
            'mode': 'clarify',
            'inherit': None,
            'text': '你想对比哪两条记录？我可以对比这次和上一次，或者最近两条历史记录。',
            'options': ['对比这次和上一次记录', '对比最近两次记录'],
        }

    if is_bare_reference(text):
        if last.get('intent'):
            return {'mode': 'followup', 'inherit': last['intent'], 'text': '', 'options': []}
        if has_values:
            return {'mode': 'followup', 'inherit': 'interpret', 'text': '', 'options': []}
        return {
            'mode': 'clarify',
            'inherit': None,
            'text': '我不太确定你指的是哪一项，可以从下面选一个，或者把问题说完整一点。',
            'options': CLARIFY_OPTIONS,
        }

    return {'mode': 'normal', 'inherit': None, 'text': '', 'options': []}


def merge_question(question: str, history: Optional[List[Dict]]) -> str:
    """把「那它呢」补全成能独立理解的问题，供后续意图判断使用。"""
    text = (question or '').strip()
    history = history or []
    if not history or not is_bare_reference(text):
        return text
    last_question = (history[-1].get('question') or '').strip()
    if not last_question:
        return text
    return '%s（追问：%s）' % (last_question, text)
