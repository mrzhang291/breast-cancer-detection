"""LLM agent 门面：把 DeepSeek + 工具循环接进主项目。

调用方（app.py）只需要：
    from agent.llm_agent import run_llm_agent
    result = run_llm_agent(question, ctx, emit=...)
返回 None 表示"没启用或不可用"，调用方回退到确定性编排器。
"""
import time
from typing import Callable, Dict, Optional

from . import registry
from .core import AgentLoop, AgentSession, DeepSeekProvider
from .core.presentation import describe, summarize

SYSTEM_PROMPT = """你是乳腺癌辅助分析系统的 AI 助手。你的回答会被医生和患者看到。

规则：
1. 所有数字必须来自工具返回结果，禁止自己编造。工具没给的数据就说"我查不到"。
2. 涉及预测结论时，必须同时说明置信度和证据强度。
3. 用户要报告、导出、汇总时，调用对应工具产出文件，不要只用文字描述。
4. 证据不足时明确说不下结论，并说明缺什么。
5. 用简洁中文回答，不要用夸张措辞，不要做诊断承诺。
6. 一次只调用必要的工具，能一步解决就不要拆成多步。
7. 遇到需要多步查证的分析类问题，可以调用 delegate 交给子代理处理。
8. 用户说"生成报告/出份报告"时不要反问类型：有本次预测就用 export_report(kind=single)，说"和上次比"用 compare，说"最近N次/最近N天"用 range，说"批量"用 batch。
9. 查用户自己的数据优先用 records / statistics，不要用 sql_query；sql_query 只用于跨用户的聚合统计。
"""

DEFAULT_TOOLS = [
    'predict', 'explain', 'records', 'statistics', 'similar_cases',
    'search_knowledge', 'sql_query', 'compare_records',
    'export_report', 'export_data', 'delegate',
]


def build_session(ctx, question_meta: Optional[Dict] = None) -> AgentSession:
    session = AgentSession(run_id=getattr(ctx, 'run_id', ''),
                           user_id=getattr(ctx, 'user_id', 0),
                           role_id=getattr(ctx, 'role_id', 3),
                           lang=getattr(ctx, 'lang', 'zh'))
    session.system(SYSTEM_PROMPT)
    if question_meta:
        session.meta.update(question_meta)
    return session


def _context_brief(ctx) -> str:
    """把本次预测的事实压缩成一段上下文，供模型直接使用。"""
    lines = []
    for fact in (getattr(ctx, 'facts', None) or []):
        kind = fact.get('kind')
        payload = fact.get('payload') or {}
        if kind == 'input':
            values = payload.get('values') or []
            if values:
                lines.append('本次输入的 30 项特征值：%s' % ', '.join('%.6g' % v for v in values))
        elif kind == 'prediction':
            lines.append('本次预测：%s，置信度 %.4f' % (
                payload.get('output'), float(payload.get('confidence') or 0)))
        elif kind == 'shap':
            tops = (payload.get('top_features') or [])[:3]
            names = [str(t.get('name_zh') or t.get('name') or '') for t in tops]
            if names:
                lines.append('主要贡献特征：%s' % '、'.join(names))
    return '\n'.join(lines)

def run_llm_agent(question: str, ctx, emit: Optional[Callable] = None,
                  max_steps: int = 5) -> Optional[Dict]:
    """返回与确定性编排器相近的结构；不可用时返回 None。"""
    provider = DeepSeekProvider()
    if not provider.available():
        return None

    session = build_session(ctx)
    brief = _context_brief(ctx)
    if brief:
        session.user('（系统注：以下是当前会话已有的上下文）\n' + brief)
        session.assistant('收到，我会基于这个上下文回答。')

    loop = AgentLoop(provider, registry.TOOLS, ctx,
                     allowed_tools=DEFAULT_TOOLS, max_steps=max_steps, emit=emit)
    started = time.time()
    result = loop.run(session, question)

    steps = []
    for index, step in enumerate(result.steps, start=1):
        info = describe(step.get('tool', ''))
        steps.append({
            'seq': index,
            'node': 'tool',
            'tool': step.get('tool'),
            'label': info['label'],
            'verdict': step.get('verdict'),
            'latency_ms': step.get('latency_ms'),
            'summary': summarize(step),
        })

    return {
        'engine': 'llm',
        'answer_md': result.answer,
        'steps': steps,
        'artifacts': list(getattr(ctx, 'artifacts', []) or []),
        'citations': list(getattr(ctx, 'citations', []) or []),
        'stopped': result.stopped,
        'usage': result.usage,
        'latency_ms': int((time.time() - started) * 1000),
        'model_used': provider.model,
    }
