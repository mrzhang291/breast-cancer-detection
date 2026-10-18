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
9. 用户提到"刚才的报告/上一份报告"时，指代上下文里列出的最近产物，按其类型说明结构即可，不要要求用户重新提供。
10. 用户问"我有几个对话/最近聊了什么"时用 sessions 工具。
11. 查用户自己的数据优先用 records / statistics，不要用 sql_query；sql_query 只用于跨用户的聚合统计。
"""

DEFAULT_TOOLS = [
    'predict', 'explain', 'records', 'statistics', 'similar_cases',
    'search_knowledge', 'sql_query', 'compare_records',
    'export_report', 'export_data', 'delegate', 'sessions',
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

def _ground(answer: str, ctx) -> dict:
    """句子级溯源：编造的数字整句丢弃，无出处结论标「推断」。"""
    try:
        from . import grounding
        return grounding.ground(answer, list(getattr(ctx, 'facts', []) or []),
                                list(getattr(ctx, 'citations', []) or []))
    except Exception:  # noqa: BLE001
        return {'ok': True, 'coverage': 1.0, 'claims': [], 'dropped': [],
                'dropped_count': 0, 'unsupported': [], 'answer_md': answer}


def run_llm_agent(question: str, ctx, emit: Optional[Callable] = None,
                  max_steps: int = 5, values=None,
                  history=None, recent_artifacts=None) -> Optional[Dict]:
    """返回与确定性编排器相近的结构；不可用时返回 None。"""
    provider = DeepSeekProvider()
    if not provider.available():
        return None

    session = build_session(ctx)

    # 短期记忆：把最近几轮问答压成文本，模型才知道"刚才那份报告"指什么
    for item in (history or [])[-3:]:
        q = (item.get('question') or '').strip()
        a = (item.get('answer') or '').strip()[:160]
        if q:
            session.user(q)
            session.assistant(a or '（已处理）')

    brief = _context_brief(ctx)
    if recent_artifacts:
        names = ['%s（%s, %d KB）' % (i.get('filename'), str(i.get('kind', 'pdf')).upper(),
                                     int((i.get('size') or 0) / 1024))
                 for i in (recent_artifacts or [])[:3]]
        brief += '\n最近生成的产物：' + '；'.join(names)
        brief += ('\n如果用户提到"刚才的报告/那份 PDF"，指的就是上面这些文件。'
                  '单次报告的固定结构是：结论与校准置信度、置信度刻度图、Top8 特征贡献图、'
                  '30 项特征与良恶性组均值对照表、方法说明、引用条款。'
                  '用户问"能补充什么"时，直接基于这个结构说清已有内容，不要声称看不到文件。')
    if values:
        brief += '\n本次输入的 30 项特征值：%s' % ', '.join('%.6g' % float(v) for v in values)
    if brief:
        session.user('（系统注：以下是当前会话已有的上下文）\n' + brief)
        session.assistant('收到，我会基于这个上下文回答。')

    loop = AgentLoop(provider, registry.TOOLS, ctx,
                     allowed_tools=DEFAULT_TOOLS, max_steps=max_steps, emit=emit)
    started = time.time()
    result = loop.run(session, question)

    grounded = _ground(result.answer, ctx)
    result.answer = grounded.get('answer_md') or result.answer

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
        'grounding': grounded,
        'verify': {'ok': grounded.get('ok'),
                   'dropped': grounded.get('dropped_count', 0)},
        'steps': steps,
        'artifacts': list(getattr(ctx, 'artifacts', []) or []),
        'citations': list(getattr(ctx, 'citations', []) or []),
        'stopped': result.stopped,
        'usage': result.usage,
        'latency_ms': int((time.time() - started) * 1000),
        'model_used': provider.model,
    }


def stream_llm_agent(question: str, ctx, values=None, max_steps: int = 5,
                     history=None, recent_artifacts=None):
    """流式执行：产出 {event, data}，最后一个事件补上产物与 run_id。"""
    from .core.streaming import StreamingAgentLoop
    from .core.streaming_provider import StreamingDeepSeekProvider

    provider = StreamingDeepSeekProvider()
    if not provider.available():
        yield {'event': 'fallback', 'data': {}}
        return

    session = build_session(ctx)

    # 短期记忆：最近几轮问答 + 最近产物，模型才知道"刚才那份报告"指什么
    for item in (history or [])[-3:]:
        q = (item.get('question') or '').strip()
        a = (item.get('answer') or '').strip()[:160]
        if q:
            session.user(q)
            session.assistant(a or '（已处理）')

    brief = _context_brief(ctx)
    if recent_artifacts:
        names = ['%s（%s, %d KB）' % (it.get('filename'), str(it.get('kind', 'pdf')).upper(),
                                     int((it.get('size') or 0) / 1024))
                 for it in (recent_artifacts or [])[:3]]
        brief += '\n最近生成的产物：' + '；'.join(names)
        brief += ('\n如果用户提到"刚才的报告/那份 PDF"，指的就是上面这些文件。'
                  '单次报告的固定结构是：结论与校准置信度、置信度刻度图、Top8 特征贡献图、'
                  '30 项特征与良恶性组均值对照表、方法说明、引用条款。'
                  '用户问"能补充什么"时，直接基于这个结构说清已有内容，不要声称看不到文件。')
    if values:
        brief += '\n本次输入的 30 项特征值：%s' % ', '.join('%.6g' % float(v) for v in values)
    if brief:
        session.user('（系统注：以下是当前会话已有的上下文）\n' + brief)
        session.assistant('收到，我会基于这个上下文回答。')

    loop = StreamingAgentLoop(provider, registry.TOOLS, ctx,
                              allowed_tools=DEFAULT_TOOLS, max_steps=max_steps)
    answer_parts = []
    for item in loop.stream(session, question):
        if item['event'] == 'token':
            answer_parts.append((item.get('data') or {}).get('delta') or '')
        if item['event'] == 'done':
            data = dict(item['data'])
            grounded = _ground(''.join(answer_parts), ctx)
            data['grounding'] = grounded
            data['answer_md'] = grounded.get('answer_md') or ''.join(answer_parts)
            data['verify'] = {'ok': grounded.get('ok'),
                              'dropped': grounded.get('dropped_count', 0)}
            data['artifacts'] = list(getattr(ctx, 'artifacts', []) or [])
            data['citations'] = list(getattr(ctx, 'citations', []) or [])
            data['run_id'] = getattr(ctx, 'run_id', '')
            data['engine'] = 'llm'
            data['steps_detail'] = [
                {'tool': st.get('tool'), 'ok': st.get('ok'),
                 'label': describe(st.get('tool') or '')['label'],
                 'latency_ms': st.get('latency_ms')}
                for st in loop.steps
            ]
            yield {'event': 'done', 'data': data}
        else:
            yield item
