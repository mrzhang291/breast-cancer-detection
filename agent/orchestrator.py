"""编排器：确定性状态机 route → act → compose → verify → guard。

刻意不用"自主 agent"：医疗场景要可复现、可审计。
节点固定，只有措辞由模型润色；所有数字来自工具事实。
"""
import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from . import cache, db, llm, policy, registry, tracing, verify
from .graph import Graph, Interrupt, JsonCheckpointer
from . import dialog
from .context import AgentContext

# 确保工具被注册
from . import tools  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES_FILE = os.path.join(ROOT, 'agent', 'knowledge', 'features.json')

INTENT = {
    'interpret': 'result_interpretation',
    'feature': 'feature_question',
    'usage': 'usage',
    'history': 'history',
    'cases': 'similar_cases',
    'report': 'report',
    'general': 'general',
    'task': 'multi_step_task',
    'sql': 'data_query',
    'export': 'report_export',
    'compare': 'record_compare',
    'clarify': 'clarify',
}

INTENT_LABEL = {
    'result_interpretation': '解读预测结果',
    'feature_question': '解释特征含义',
    'usage': '系统使用咨询',
    'history': '查看历史记录',
    'similar_cases': '检索相似病例',
    'report': '生成分析报告',
    'general': '一般咨询',
    'multi_step_task': '多步任务',
    'data_query': '数据查询',
    'refused': '超出范围',
    'report_export': '生成报告',
    'record_compare': '记录对比',
    'clarify': '澄清追问',
}

_FEATURES: List[Dict] = []


def features() -> List[Dict]:
    global _FEATURES
    if not _FEATURES and os.path.exists(FEATURES_FILE):
        with open(FEATURES_FILE, encoding='utf-8') as f:
            _FEATURES = json.load(f).get('items', [])
    return _FEATURES


def feature_names() -> List[str]:
    return [item['feature'] for item in features()]


# ------------------------------------------------------------------ 路由

_USAGE_HINTS = ['怎么', '如何', '在哪', '哪里', '使用', '操作', '导入', '上传', '导出',
                '批量', '模板', '登录', '注册', '密码', 'shap', '报告下载']
_HISTORY_HINTS = ['记录', '历史', '统计', '多少条', '多少次', '趋势', '我做过',
                  '做过几次', '预测记录', '我的预测']
_CASE_HINTS = ['相似', '相近', '类似', '邻居', '对照']
_EXPORT_HINTS = ['生成报告', '出份报告', '出一份报告', '导出报告', '生成一份报告',
                 '导出 pdf', '导出pdf', '生成 pdf', '生成pdf', '报告文件', '出报告',
                 '导出我的数据', '导出数据']

_REPORT_HINTS = ['生成报告', '总结报告', '出一份', '写一份', '分析报告', '生成一份']
_INTERPRET_HINTS = ['这个结果', '结果什么', '什么意思', '严重', '要紧', '怎么看',
                    '解读', '意味着', '风险']
_TASK_HINTS = ['逐条', '每条', '分别', '依次', '一条一条', '批量解释', '对比这几', '都解释']
_SQL_HINTS = ['占比', '数量', '最高', '最低', '分布', '汇总', '统计一下']



def classify(question: str, has_features: bool) -> str:
    text = (question or '').lower()

    if dialog.looks_compare(text):
        return INTENT['compare']

    # 「导出报告」是动作，不是能力询问（后者以「吗」结尾，仍归 usage）
    if any(h in text for h in _EXPORT_HINTS) and not text.rstrip('？?').endswith('吗'):
        return INTENT['export']

    if any(h in text for h in _TASK_HINTS):
        return INTENT['task']
    if any(h in text for h in _SQL_HINTS) and '记录' not in text:
        return INTENT['sql']
    if ('平均' in text or '均值' in text) and any(w in text for w in ('病例', '样本', '患者')) and '记录' not in text:
        return INTENT['sql']
    # 「记录怎么删」「报告怎么导出」这类是操作问题，不是查历史
    if any(h in text for h in ('怎么', '如何')) and any(
            w in text for w in ('删', '导出', '上传', '导入', '操作', '填写', '用')):
        return INTENT['usage']
    if any(h in text for h in _CASE_HINTS):
        return INTENT['cases']
    if any(h in text for h in _REPORT_HINTS):
        return INTENT['report']
    if any(h in text for h in _HISTORY_HINTS):
        return INTENT['history']

    for item in features():
        if item['feature'].lower() in text or item['name_zh'] in text:
            return INTENT['feature']

    if any(h in text for h in _INTERPRET_HINTS):
        return INTENT['interpret'] if has_features else INTENT['general']
    if any(h in text for h in _USAGE_HINTS):
        return INTENT['usage']

    return INTENT['interpret'] if has_features else INTENT['general']


def mentioned_features(question: str) -> List[Dict]:
    text = (question or '').lower()
    hit = []
    for item in features():
        if item['feature'].lower() in text or item['name_zh'] in text:
            hit.append(item)
    return hit


# ------------------------------------------------------------------ 事实

def add_input_fact(ctx: AgentContext, values: List[float]) -> None:
    names = feature_names()
    payload = {'features': [{'name': n, 'value': round(float(v), 6)}
                            for n, v in zip(names, values)]}
    ctx.add_fact(registry.make_fact('input', payload, tool='input',
                                    run_id=ctx.run_id, ident='in_%s' % ctx.run_id[:8]))


def _prediction_fact(ctx: AgentContext) -> Optional[Dict]:
    for fact in ctx.facts:
        if fact['kind'] == 'prediction':
            return fact
    return None


def _shap_fact(ctx: AgentContext) -> Optional[Dict]:
    for fact in ctx.facts:
        if fact['kind'] == 'shap':
            return fact
    return None


def _clause_facts(ctx: AgentContext) -> List[Dict]:
    return [f for f in ctx.facts if f['kind'] == 'clause']


def _cases_fact(ctx: AgentContext) -> Optional[Dict]:
    for fact in ctx.facts:
        if fact['kind'] == 'case':
            return fact
    return None


# ------------------------------------------------------------------ 工具节点

def _call(ctx: AgentContext, name: str, args: Dict, emit=None) -> Dict:
    started = time.time()
    result = registry.call_tool(ctx, name, args)
    latency = int((time.time() - started) * 1000)
    step = tracing.record_step(
        ctx, node='act', tool=name, args=args,
        result_digest=registry.digest(result.data) if result.ok else result.error_type,
        verdict='ok' if result.ok else result.error_type, latency_ms=latency)
    if emit:
        emit('step', {'seq': step['seq'], 'node': 'act', 'tool': name,
                      'label': '%s 完成' % name, 'ok': result.ok,
                      'ms': latency, 'error': result.error})
    return result.to_dict()


def _act_interpret(ctx: AgentContext, values: List[float], emit=None) -> None:
    pred = _call(ctx, 'predict', {'features': values}, emit)
    if not pred['ok']:
        raise RuntimeError(pred['error'])

    payload = pred['data']
    _call(ctx, 'explain', {'features': values,
                           'prediction': payload['output'],
                           'confidence': payload['confidence']}, emit)

    shap_fact = _shap_fact(ctx)
    if shap_fact:
        for item in shap_fact['payload'].get('top_features', [])[:3]:
            _call(ctx, 'search_knowledge', {'query': item['name'], 'k': 2}, emit)

    _call(ctx, 'similar_cases', {'features': values, 'k': 5}, emit)


def _act_features(ctx: AgentContext, question: str,
                  values: Optional[List[float]] = None, emit=None) -> None:
    hits = mentioned_features(question)
    if hits:
        # 已知是哪个特征时直接按编号取条款，避免检索串到别的特征上
        for item in hits[:3]:
            _call(ctx, 'get_clause', {'clause_id': item['clause_id']}, emit)
    else:
        _call(ctx, 'search_knowledge', {'query': question, 'k': 3}, emit)


def _act_usage(ctx: AgentContext, question: str, emit=None) -> None:
    _call(ctx, 'search_knowledge', {'query': question, 'k': 5}, emit)


def _act_history(ctx: AgentContext, emit=None) -> None:
    _call(ctx, 'statistics', {}, emit)
    _call(ctx, 'records', {'limit': 10}, emit)


def _act_cases(ctx: AgentContext, values: Optional[List[float]], emit=None) -> None:
    if values:
        _call(ctx, 'similar_cases', {'features': values, 'k': 5}, emit)


def _act_sql(ctx: AgentContext, question: str, emit=None) -> None:
    """让 agent 自己写 SQL 查库。"""
    _call(ctx, 'sql_query', {'question': question}, emit)


def _act_task(ctx: AgentContext, question: str, emit=None) -> None:
    """多步任务：按记录逐条预测 + 归因，步数由数据决定。"""
    import re as _re

    from . import runtime as _runtime

    rt = _runtime.get()
    rt.require('fetch_records')

    match = _re.search(r'(\d+)\s*[条个例]', question)
    limit = min(int(match.group(1)), 5) if match else 3
    label = '恶性' if '恶性' in question else ('良性' if '良性' in question else None)

    page = rt.fetch_records(ctx.user_id, 1, 20) or {}
    items = page.get('items') or []
    if label:
        items = [it for it in items if label in str(it.get('prediction_result'))]
    items = items[:limit]

    rows = []
    for idx, item in enumerate(items, start=1):
        feats = item.get('features') or {}
        vector = [feats.get('feature_%d' % i) for i in range(1, 31)]
        if any(v is None for v in vector):
            continue
        vector = [float(v) for v in vector]

        pred = registry.call_tool(ctx, 'predict', {'features': vector})
        tracing.record_step(ctx, node='act', tool='predict',
                            args={'record_id': item.get('id')},
                            result_digest=registry.digest(pred.data) if pred.ok else pred.error_type,
                            verdict='ok' if pred.ok else pred.error_type,
                            latency_ms=pred.latency_ms)
        row = {'seq': idx, 'record_id': item.get('id'),
               'recorded': item.get('prediction_result'),
               'recorded_confidence': item.get('confidence'),
               'created_at': item.get('created_at')}
        if pred.ok:
            row['output'] = pred.data.get('output')
            row['confidence'] = pred.data.get('confidence')
            row['consistent'] = (row['output'] == row['recorded'])
            if idx <= 2:
                exp = registry.call_tool(ctx, 'explain', {
                    'features': vector,
                    'prediction': pred.data.get('output'),
                    'confidence': pred.data.get('confidence')})
                tracing.record_step(ctx, node='act', tool='explain',
                                    args={'record_id': item.get('id')},
                                    result_digest=registry.digest(exp.data) if exp.ok else exp.error_type,
                                    verdict='ok' if exp.ok else exp.error_type,
                                    latency_ms=exp.latency_ms)
                if exp.ok:
                    top = (exp.data.get('top_features') or [{}])[0]
                    row['top_feature'] = top.get('name')
                    row['top_direction'] = top.get('direction')
        rows.append(row)
        if emit:
            emit('step', {'seq': 500 + idx, 'node': 'act', 'tool': 'predict',
                          'label': '逐条处理 %d/%d' % (idx, len(items)),
                          'ok': pred.ok, 'ms': 0})

    fact = registry.make_fact('task', {
        'requested': limit,
        'processed': len(rows),
        'filter': label or '全部',
        'items': rows,
    }, tool='multi_step', run_id=ctx.run_id, ident='task_%s' % ctx.run_id[:8])
    ctx.add_fact(fact)



def _record_values(item):
    """从一条记录里取出 30 维特征，兼容 dict / list 两种返回。"""
    if isinstance(item, dict):
        feats = item.get('features')
        if isinstance(feats, dict) and feats:
            out = []
            for idx in range(1, 31):
                value = feats.get('feature_%d' % idx)
                if value is None:
                    return None
                out.append(float(value))
            return out
        if isinstance(feats, list) and len(feats) >= 30:
            return [float(v) for v in feats[:30]]
        values = item.get('values')
        if isinstance(values, list) and len(values) >= 30:
            return [float(v) for v in values[:30]]
    if isinstance(item, (list, tuple)) and len(item) >= 35:
        return [float(v) for v in item[5:35]]
    return None


def _act_compare(ctx: AgentContext, values: Optional[List[float]] = None, emit=None) -> None:
    """取最近两条记录，和当前这次输入做逐项对比。"""
    _call(ctx, 'records', {'limit': 5}, emit)

    items = []
    for fact in ctx.facts:
        if fact.get('kind') == 'record':
            items = (fact.get('payload') or {}).get('items') or []
            break

    current = list(values) if values else None
    if not current and items:
        current = _record_values(items[0])

    previous = None
    for item in items:
        candidate = _record_values(item)
        if not candidate:
            continue
        if current and all(abs(a - b) < 1e-9 for a, b in zip(candidate, current)):
            continue
        previous = candidate
        break

    if current and previous:
        _call(ctx, 'compare_records', {'current': current, 'previous': previous}, emit)


def _act_export(ctx: AgentContext, values, state, emit=None) -> None:
    """生成报告：先补齐预测/归因事实，再交给 export_report。"""
    if values:
        _act_interpret(ctx, values, emit)
    _call(ctx, 'export_report', {'kind': 'single'}, emit)


def _compose_export(ctx: AgentContext):
    artifact = ctx.artifacts[-1] if ctx.artifacts else None
    if not artifact:
        return ('报告没生成出来。可能是当前没有可用的预测结果，先在首页做一次预测，'
                '再让我生成报告。', [])
    return ('报告已生成：**%s**（%.0f KB）。\n\n'
            '点击下面的卡片即可下载，文件保留 7 天。'
            % (artifact.get('filename'), artifact.get('size', 0) / 1024.0), [])


def _compose_compare(ctx: AgentContext):
    fact = next((f for f in ctx.facts if f.get('kind') == 'compare'), None)
    if not fact:
        return ('我暂时凑不齐两条可对比的记录。先做一次预测，再问我和上次比，'
                '我就能把 30 项特征逐项比给你看。', [])

    payload = fact.get('payload') or {}
    top = payload.get('top') or []
    changed = int(payload.get('changed_count') or 0)

    lines = ['我把两条记录逐项比了一遍：有 **%d** 项特征变化超过 5%%。' % changed, '']
    for item in top[:4]:
        arrow = '↑' if item['change_pct'] > 0 else '↓'
        lines.append('- **%s**：%.2f → %.2f（%s %.0f%%）'
                     % (item['name_zh'], item['previous'], item['current'],
                        arrow, abs(item['change_pct'])))

    lines += ['',
              '变化最大的几项通常就是结论差异的来源。如果其中包含「最差值」类指标'
              '（面积、凹点、concave points），对恶性判断的影响会更直接。']
    return '\n'.join(lines), []


def _act_report(ctx: AgentContext, values: List[float], emit=None) -> None:
    _act_interpret(ctx, values, emit)


# ------------------------------------------------------------------ 生成（模板）

def _fmt_pct(value: float) -> str:
    return '%.2f%%' % (float(value) * 100.0)


def _fmt_num(value: float) -> str:
    return ('%.4f' % float(value)).rstrip('0').rstrip('.')


def _compose_interpret(ctx: AgentContext, values: Optional[List[float]]) -> Tuple[str, List[str]]:
    pred = _prediction_fact(ctx)
    shap_fact = _shap_fact(ctx)
    cases = _cases_fact(ctx)
    if not pred:
        return '暂时无法完成预测，请稍后重试。', []

    payload = pred['payload']
    output = payload['output']
    confidence = payload['confidence']
    model_type = payload.get('model_type', '')
    lines = ['**预测结论**：%s（置信度 %s，模型：%s）' % (
        output, _fmt_pct(confidence), model_type or '默认')]

    if shap_fact:
        lines.append('\n**主要归因**（数值来自模型归因结果，不是推测）：')
        for rank, item in enumerate(shap_fact['payload'].get('top_features', [])[:5], 1):
            direction = '推向恶性' if item.get('shap_value', 0) > 0 else '推向良性'
            lines.append('%d. `%s` = %s —— %s' % (
                rank, item['name'], _fmt_num(item['value']), direction))

    clauses = _clause_facts(ctx)
    if clauses:
        lines.append('\n**指标含义**（引用特征词典）：')
        seen = set()
        for clause in clauses:
            for hit in clause['payload'].get('hits', [])[:3]:
                if hit['clause_id'] in seen or not hit['clause_id'].startswith('FEAT'):
                    continue
                seen.add(hit['clause_id'])
                lines.append('- %s [%s]' % (hit['text'], hit['clause_id']))

    if cases and cases['payload'].get('cases'):
        cp = cases['payload']
        lines.append('\n**相似历史样本**：最近的 %d 个样本中，恶性 %d 个、良性 %d 个（相似度 %.3f ~ %.3f）。'
                     '仅用于直观对照，属于数据集邻居，不构成临床证据。' % (
                         cp['k'], cp['malignant_count'], cp['benign_count'],
                         cp['cases'][-1]['similarity'], cp['cases'][0]['similarity']))

    lines.append('\n**下一步建议**：' + (
        '结果提示恶性可能性较高，建议尽快到乳腺专科就诊，结合影像学与病理学检查进一步确认。'
        if output == '恶性' else
        '结果提示良性可能性较高，建议按常规随访；若出现形态变化或新发症状，请及时就诊。'))

    return '\n'.join(lines), list(ctx.citations)


def _compose_feature(ctx: AgentContext, question: str,
                     values: Optional[List[float]]) -> Tuple[str, List[str]]:
    hits = mentioned_features(question)
    clauses = _clause_facts(ctx)
    lines = []
    if hits:
        lines.append('**您问的是**：' + '、'.join('%s（%s）' % (h['name_zh'], h['feature']) for h in hits))

    seen = set()
    for clause in clauses:
        for hit in clause['payload'].get('hits', []):
            if hit['clause_id'] in seen:
                continue
            seen.add(hit['clause_id'])
            lines.append('\n**%s** `%s`\n\n%s\n\n> 来源：%s §%s <%s>' % (
                hit['section'], hit['clause_id'], hit['text'],
                hit['source'], hit['section'], hit['clause_id']))

    if values and hits:
        names = feature_names()
        for item in hits:
            idx = item.get('index', 0) - 1
            if 0 <= idx < len(values):
                lines.append('\n**您这次填写的值**：`%s` = %s' % (item['feature'], _fmt_num(values[idx])))

    if not lines:
        return '没有找到相关说明，请换个说法再问一次。', []
    return '\n'.join(lines), list(ctx.citations)


def _looks_noisy(text: str) -> bool:
    """过滤目录树、纯代码块这类"检索得到但答不了问题"的条款。"""
    lines = [line for line in (text or '').splitlines() if line.strip()]
    if not lines:
        return True
    tree = sum(1 for line in lines if line.lstrip().startswith(('├', '└', '│', '┌')))
    fences = sum(1 for line in lines if line.strip().startswith('```'))
    return tree >= 3 or fences >= 2


def _first_sentence(text: str, limit: int = 90) -> str:
    """取条款的第一句，用来做顶部摘要。"""
    body = re.sub(r'^[#>*\-\s]+', '', (text or '').strip().splitlines()[0] if (text or '').strip() else '')
    match = re.search(r'[。！？.!?]', body)
    if match and match.start() > 8:
        body = body[:match.start() + 1]
    return body[:limit]


def _clean_clause(text: str, limit: int = 420) -> str:
    """把 markdown 原文整理成可读段落：去标题井号、去过密空行、去掉零碎列表头。"""
    lines = []
    for raw in (text or '').splitlines():
        line = raw.rstrip()
        if re.match(r'^#{1,6}\s*', line):
            line = re.sub(r'^#{1,6}\s*', '', line)
        if line.strip() in ('```', ''):
            if lines and lines[-1] == '':
                continue
            lines.append('')
            continue
        lines.append(line)
    body = '\n'.join(lines).strip()
    body = re.sub(r'\n{3,}', '\n\n', body)
    if len(body) > limit:
        body = body[:limit].rstrip() + '…'
    return body


def _compose_usage(ctx: AgentContext) -> Tuple[str, List[str]]:
    """使用类问题：策展答案优先，检索兜底。"""
    from .knowledge import faq

    curated = faq.match(ctx.question)
    if curated:
        body = '### %s\n\n%s' % (curated['title'], curated['body'])
        return body, [curated['id']]

    hits = []
    seen = set()
    for clause in _clause_facts(ctx):
        for hit in clause['payload'].get('hits', [])[:5]:
            if hit['clause_id'] in seen or _looks_noisy(hit['text']):
                continue
            seen.add(hit['clause_id'])
            hits.append(hit)
            if len(hits) >= 3:
                break
        if len(hits) >= 3:
            break

    if not hits:
        return ('没有在系统文档里找到对应说明。您可以换个问法，'
                '或者直接说明要操作的功能（例如"批量预测怎么上传文件"）。'), []

    top = hits[0]
    parts = ['**%s**：%s' % (top['section'], _first_sentence(top['text'])), '']
    for hit in hits:
        parts.append('### %s' % hit['section'])
        parts.append('')
        parts.append(_clean_clause(hit['text']))
        parts.append('')

    sources = '、'.join(sorted({h['source'] for h in hits}))
    parts.append('> 依据：%s ｜ 引用编号：%s' % (
        sources, '、'.join(h['clause_id'] for h in hits)))

    return '\n'.join(parts).strip(), [h['clause_id'] for h in hits]


def _compose_history(ctx: AgentContext) -> Tuple[str, List[str]]:
    stat = next((f for f in ctx.facts if f['kind'] == 'stat'), None)
    record = next((f for f in ctx.facts if f['kind'] == 'record'), None)
    if not stat:
        return '暂时读不到统计信息，请稍后重试。', []

    p = stat['payload']
    lines = ['**统计概览**：累计 %d 条预测，其中良性 %d 条、恶性 %d 条，平均置信度 %s。'
             % (p['total'], p['benign'], p['malignant'], _fmt_pct(p['avg_confidence']))]

    if record and record['payload'].get('items'):
        lines.append('\n**最近记录**：')
        for item in record['payload']['items'][:5]:
            lines.append('- #%s %s 置信度 %s %s' % (
                item.get('id'), item.get('prediction_result'),
                _fmt_pct(item.get('confidence', 0)), item.get('created_at', '')))
    return '\n'.join(lines), list(ctx.citations)


def _compose_cases(ctx: AgentContext) -> Tuple[str, List[str]]:
    cases = _cases_fact(ctx)
    if not cases:
        return '请先提供 30 项特征，我才能检索相似病例。', []
    p = cases['payload']
    lines = ['**相似病例检索**：在数据集里找到最近 %d 个样本，其中恶性 %d 个、良性 %d 个。'
             % (p['k'], p['malignant_count'], p['benign_count']), '']
    for case in p['cases']:
        lines.append('- #%d %s 相似度 %s，半径均值 %s，面积均值 %s' % (
            case['rank'], case['label'], _fmt_num(case['similarity']),
            _fmt_num(case['radius_mean']), _fmt_num(case['area_mean'])))
    lines.append('\n> 说明：这些是训练数据集中的历史样本，仅用于直观对照，不能作为临床证据。')
    return '\n'.join(lines), list(ctx.citations)


def _compose_sql(ctx: AgentContext) -> Tuple[str, List[str]]:
    fact = next((f for f in ctx.facts if f['kind'] == 'sql'), None)
    if not fact:
        return '没有查到数据。', []

    payload = fact['payload']
    columns = payload.get('columns') or []
    rows = payload.get('rows') or []
    lines = ['**查询思路**：%s' % payload.get('explanation', ''),
             '',
             '```sql',
             payload.get('sql', ''),
             '```',
             '']
    if not rows:
        lines.append('查询没有返回数据。')
    else:
        lines.append('| ' + ' | '.join(str(c) for c in columns) + ' |')
        lines.append('|' + '|'.join(['---'] * len(columns)) + '|')
        for row in rows[:20]:
            lines.append('| ' + ' | '.join(str(row.get(c, '')) for c in columns) + ' |')
        lines.append('')
        lines.append('共 %d 行。' % payload.get('row_count', len(rows)))
    return '\n'.join(lines), list(ctx.citations)


def _compose_task(ctx: AgentContext) -> Tuple[str, List[str]]:
    fact = next((f for f in ctx.facts if f['kind'] == 'task'), None)
    if not fact:
        return '没有找到可处理的记录。', []

    payload = fact['payload']
    items = payload.get('items') or []
    if not items:
        return ('没有找到符合条件的记录。可以先做几次预测，或换一个筛选条件（恶性 / 良性）。'), []

    consistent = sum(1 for it in items if it.get('consistent'))
    lines = ['**任务结果**：处理了 %d 条%s记录（请求 %d 条），其中 %d 条与当时记录一致。'
             % (len(items), payload.get('filter', ''), payload.get('requested', 0), consistent),
             '',
             '| # | 记录 | 当时结论 | 重算结论 | 置信度 | 主要归因 |',
             '|---|---|---|---|---|---|']
    for it in items:
        lines.append('| %d | #%s | %s | %s | %s | %s |' % (
            it.get('seq'), it.get('record_id'), it.get('recorded', '-'),
            it.get('output', '-'),
            ('%.2f%%' % (float(it.get('confidence') or 0) * 100)) if it.get('confidence') else '-',
            it.get('top_feature', '-')))

    inconsistent = [it for it in items if it.get('consistent') is False]
    if inconsistent:
        lines.append('')
        lines.append('**注意**：%d 条记录重算结果与当时不一致（#%s），可能是模型版本变化或输入有误。'
                     % (len(inconsistent), ', #'.join(str(x.get('record_id')) for x in inconsistent)))
    return '\n'.join(lines), list(ctx.citations)


def _compose_report(ctx: AgentContext) -> Tuple[str, List[str]]:
    body, citations = _compose_interpret(ctx, None)
    pred = _prediction_fact(ctx)
    header = '# 乳腺癌辅助分析报告\n'
    if pred:
        header += '\n> 生成时间：%s ｜ run_id：%s\n' % (
            time.strftime('%Y-%m-%d %H:%M:%S'), ctx.run_id)
    footer = ('\n\n---\n\n**说明**：本报告由确定性规则 + 机器学习模型 + 知识库检索生成，'
              '所有数值均来自工具返回值，可逐项溯源（见 citations）。')
    return header + '\n' + body + footer, citations


# ------------------------------------------------------------------ 模型润色

def _polish(ctx: AgentContext, draft: str, question: str) -> Optional[str]:
    """只在模型可用、且属叙述型问题时润色；数值仍须通过 verify。"""
    if not llm.available():
        return None

    facts_json = json.dumps(ctx.facts, ensure_ascii=False)[:4000]
    system = ('你是乳腺癌辅助系统的解释助手。只能使用给定的事实数据，'
              '不得新增任何数字、结论或医学断言；不得诊断为确诊。'
              '输出中文 Markdown，控制在 400 字以内。')
    user = '用户问题：%s\n\n可用事实（JSON）：%s\n\n请在此基础上重写表达，使其更易读。' % (question, facts_json)
    return llm.complete(system, user)


# ------------------------------------------------------------------ 主流程

NODE_LABELS = {
    'guard': '输入检查',
    'cache': '缓存查询',
    'route': '意图识别',
    'act': '工具执行',
    'assess': '不确定性评估',
    'compose': '生成回答',
    'verify': '事实对账',
    'guard_out': '输出护栏',
    'persist': '落库',
}


def _node_guard(state, ctx):
    verdict = policy.check_question(state.get('question', ''), ctx.lang)
    state['verdict'] = verdict
    if verdict['action'] == 'refuse':
        state['status'] = 'refused'
        state['intent'] = 'refused'
        state['answer'] = policy.inject_disclaimer(
            policy.REFUSAL.get(ctx.lang, policy.REFUSAL['zh']), ctx.lang)


def _router_guard(state):
    return 'refuse' if state.get('status') == 'refused' else 'ok'


def _node_refuse(state, ctx):
    pass


def _node_cache(state, ctx):
    if state.get('values'):
        return
    cached = cache.get(ctx.user_id, ctx.lang, state['question'], state.get('intent_hint', ''))
    if cached:
        state['intent'] = classify(state['question'], bool(state.get('values')))
        state['answer'] = cached['answer_md']
        state['citations'] = cached['citations']
        state['cached'] = True
        state['status'] = 'ok'
        state['verify'] = {'ok': True, 'cached': True, 'checked': 0, 'unmatched': []}


def _router_cache(state):
    return 'hit' if state.get('cached') else 'miss'


def _node_route(state, ctx):
    plan = state.get('plan') or {}
    if plan.get('mode') == 'compare':
        intent = INTENT['compare']
    elif state.get('intent_hint'):
        intent = state['intent_hint']
    else:
        intent = classify(dialog.merge_question(state['question'], ctx.history),
                          bool(state.get('values')))
    if intent in (INTENT['interpret'], INTENT['report']) and not state.get('values'):
        intent = INTENT['usage']
    state['intent'] = intent

    # 多步任务 / 数据查询 / 历史统计 与「这一次预测」无关，不继承上一轮的特征
    if intent in (INTENT['task'], INTENT['sql'], INTENT['history']):
        state['values'] = None

    if state.get('values'):
        add_input_fact(ctx, state['values'])
    state['facts'] = ctx.facts
    state['citations'] = ctx.citations


def _node_act(state, ctx):
    intent = state.get('intent')
    values = state.get('values')
    try:
        if intent in (INTENT['interpret'], INTENT['report']):
            _act_interpret(ctx, values, state.get('_emit'))
        elif intent == INTENT['feature']:
            _act_features(ctx, state['question'], values, state.get('_emit'))
        elif intent == INTENT['history']:
            _act_history(ctx, state.get('_emit'))
        elif intent == INTENT['cases']:
            _act_cases(ctx, values, state.get('_emit'))
        elif intent == INTENT['task']:
            _act_task(ctx, state['question'], state.get('_emit'))
        elif intent == INTENT['sql']:
            _act_sql(ctx, state['question'], state.get('_emit'))
        elif intent == INTENT['compare']:
            _act_compare(ctx, values, state.get('_emit'))
        elif intent == INTENT['export']:
            _act_export(ctx, values, state, state.get('_emit'))
        else:
            _act_usage(ctx, state['question'], state.get('_emit'))
    except Exception as exc:  # noqa: BLE001
        state['status'] = 'error'
        state['answer'] = policy.inject_disclaimer(
            '处理过程中出现异常（%s），请稍后重试。' % str(exc)[:120], ctx.lang)


def _node_assess(state, ctx):
    """不确定性评估：产出三档，并在需要时挂起等待确认。"""
    if state.get('status') in ('refused', 'error'):
        return
    values = state.get('values')
    if not values:
        state['uncertainty'] = {}
        state['tier'] = 'confident'
        return

    from . import uncertainty

    pred = _prediction_fact(ctx)
    if not pred:
        state['tier'] = 'confident'
        return

    payload = pred['payload']

    # 证据强度：取命中的最高检索分，做一次平滑归一
    evidence_raw = 0.0
    for fact in ctx.facts:
        if fact.get('kind') == 'clause':
            for hit in (fact.get('payload') or {}).get('hits') or []:
                evidence_raw = max(evidence_raw, float(hit.get('score') or 0))
    evidence_score = min(1.0, evidence_raw / 30.0)

    assessment = uncertainty.assess(values, payload['confidence'], payload['output'],
                                    evidence_score=evidence_score)
    state['uncertainty'] = assessment
    state['tier'] = assessment['tier']

    if assessment['tier'] == 'abstain' and state.get('require_confirm') and not state.get('confirmed'):
        raise Interrupt('assess', {
            'tier': assessment['tier'],
            'reason': assessment.get('reason', ''),
            'uncertainty': assessment,
            'question': '当前证据不足以给出确定结论，是否继续生成提示性说明？',
        })


def _node_compose(state, ctx):
    if state.get('status') in ('refused', 'error'):
        return
    intent = state.get('intent')
    question = state['question']
    values = state.get('values')
    composers = {
        INTENT['interpret']: lambda: _compose_interpret(ctx, values),
        INTENT['feature']: lambda: _compose_feature(ctx, question, values),
        INTENT['usage']: lambda: _compose_usage(ctx),
        INTENT['history']: lambda: _compose_history(ctx),
        INTENT['cases']: lambda: _compose_cases(ctx),
        INTENT['report']: lambda: _compose_report(ctx),
        INTENT['general']: lambda: _compose_usage(ctx),
        INTENT['task']: lambda: _compose_task(ctx),
        INTENT['sql']: lambda: _compose_sql(ctx),
        INTENT['compare']: lambda: _compose_compare(ctx),
        INTENT['export']: lambda: _compose_export(ctx),
    }
    answer, citations = composers.get(intent, lambda: _compose_usage(ctx))()
    if intent in (INTENT['usage'], INTENT['general']):
        from .knowledge import faq as _faq
        state['curated'] = bool(_faq.match(state['question']))
    state['answer'] = answer
    state['citations'] = list(citations)
    state['_base_answer'] = answer

    # 三档决定措辞：证据不足时不给结论，只给线索
    tier = state.get('tier', 'confident')
    info = state.get('uncertainty') or {}
    if tier == 'abstain' and values:
        pred = _prediction_fact(ctx)
        output = (pred or {}).get('payload', {}).get('output', '未知')
        state['answer'] = (
            '**这组数据超出了模型的可靠范围，因此这次不下结论。**\n\n'
            '触发原因：%s\n\n'
            '模型按惯例给出了「%s」，但这个判断建立在训练数据没有覆盖到的输入上，'
            '外推结果不可靠，直接采信反而危险。\n\n'
            '**建议**：先核对 30 项数值的单位与录入位置（面积/周长最容易填错）；'
            '若确认无误，这属于模型经验之外的病例，请以影像学和专科医生判断为准。'
            % ('；'.join(info.get('reasons') or ['证据强度不足']), output)
        )
    elif tier == 'cautious' and values:
        state['answer'] = ('> ⚠️ 证据有限：%s\n\n' % ('；'.join(info.get('reasons') or ['证据偏弱']))
                           + answer)


def _node_verify(state, ctx):
    if state.get('status') in ('refused', 'error'):
        return
    answer = state.get('answer', '')
    if state.get('curated'):
        state['verify'] = {'ok': True, 'curated': True, 'checked': 0, 'unmatched': []}
        state['model_used'] = 'template'
        return

    fact_pool = list(state.get('facts') or [])
    if state.get('uncertainty'):
        fact_pool.append({'kind': 'uncertainty', 'payload': state['uncertainty']})
    check = verify.verify_answer(answer, fact_pool)
    state['verify'] = check
    state['model_used'] = 'template'

    if state.get('intent') in (INTENT['usage'], INTENT['general']):
        polished = _polish(ctx, answer, state['question'])
        if polished:
            polished_check = verify.verify_answer(polished, fact_pool)
            if polished_check['ok']:
                state['answer'] = polished
                state['verify'] = polished_check
                state['model_used'] = 'deepseek'

    if not state['verify']['ok'] and state.get('model_used') == 'deepseek':
        # 润色引入了不存在数字 -> 丢回模板
        state['answer'] = state.get('_base_answer', answer)
        state['model_used'] = 'template'
        state['verify'] = verify.verify_answer(state['answer'], fact_pool)


def _node_guard_out(state, ctx):
    if state.get('status') in ('refused', 'error'):
        return
    verdict = state.get('verdict') or {}
    answer, issues = policy.check_output(
        state.get('answer', ''), state.get('citations') or [], verdict.get('risk', 'low'), ctx.lang)
    answer = policy.apply_banner(answer, verdict.get('banner', ''))
    answer = policy.inject_disclaimer(answer, ctx.lang)
    state['answer'] = answer
    state['policy_issues'] = issues
    if verdict.get('action') == 'escalate':
        state['status'] = 'escalated'


def _node_persist(state, ctx):
    if state.get('status') == 'refused':
        db.update_run(ctx.run_id, intent='refused', status='refused',
                      answer_md=state.get('answer', ''), latency_ms=state.get('latency_ms', 0))
        return

    latency = state.get('latency_ms', 0)
    db.update_run(ctx.run_id, intent=state.get('intent', ''), status=state.get('status', 'ok'),
                  answer_md=state.get('answer', ''),
                  citations_json=json.dumps(state.get('citations') or [], ensure_ascii=False),
                  artifacts_json=json.dumps(ctx.artifacts, ensure_ascii=False) if ctx.artifacts else None,
                  model=state.get('model_used', 'template'),
                  latency_ms=latency)

    # 生成报告有副作用，绝不写缓存
    if (not state.get('values') and state.get('status') == 'ok' and not state.get('cached')
            and state.get('intent') not in (INTENT['task'], INTENT['sql'], INTENT['history'],
                                            INTENT['export'], INTENT['compare'])):
        cache.put(ctx.user_id, ctx.lang, state['question'],
                  state.get('answer', ''), state.get('citations') or [], '')


def _node_finish(state, ctx):
    pass


def _build_graph() -> Graph:
    graph = Graph('breast-cancer-agent')
    graph.add_node('guard', _node_guard)
    graph.add_node('cache', _node_cache)
    graph.add_node('route', _node_route)
    graph.add_node('act', _node_act)
    graph.add_node('assess', _node_assess)
    graph.add_node('compose', _node_compose)
    graph.add_node('verify', _node_verify)
    graph.add_node('guard_out', _node_guard_out)
    graph.add_node('persist', _node_persist)
    graph.add_node('refuse', _node_refuse)
    graph.add_node('finish', _node_finish)

    graph.set_entry('guard')
    graph.add_conditional_edges('guard', _router_guard,
                                {'refuse': 'refuse', 'ok': 'cache'})
    graph.add_edge('refuse', 'persist')
    graph.add_conditional_edges('cache', _router_cache,
                                {'hit': 'persist', 'miss': 'route'})
    graph.add_edge('route', 'act')
    graph.add_edge('act', 'assess')
    graph.add_edge('assess', 'compose')
    graph.add_edge('compose', 'verify')
    graph.add_edge('verify', 'guard_out')
    graph.add_edge('guard_out', 'persist')
    graph.add_edge('persist', 'finish')
    return graph


_GRAPH = None


def get_graph() -> Graph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def run(ctx: AgentContext, question: str, values: Optional[List[float]] = None,
        emit=None, require_confirm: bool = False) -> Dict:
    started = time.time()
    db.init_schema()

    if not ctx.run_id:
        ctx.run_id = db.create_run(ctx)
    ctx.question = question

    plan = dialog.plan(question, ctx.history, ctx.context, bool(values))

    # 问题含糊时先反问，不硬猜
    if plan.get('mode') == 'clarify':
        ctx.add_step(node='clarify', verdict='ask', latency_ms=0)
        answer = plan.get('text') or '能再说清楚一点吗？'
        db.update_run(ctx.run_id, status='ok', answer_md=answer,
                      citations_json='[]', latency_ms=0)
        result = _result(ctx, question, INTENT['clarify'], 'ok', answer, [],
                         {'risk': 'low'}, {'ok': True, 'checked': 0, 'unmatched': []},
                         started)
        result['clarify'] = plan.get('options') or []
        result['graph'] = [{'seq': 1, 'node': 'clarify', 'verdict': 'ask'}]
        result['tier'] = 'confident'
        result['uncertainty'] = {}
        result['model_used'] = 'template'
        result['policy_issues'] = []
        result['cached'] = False
        return result

    state = {
        'run_id': ctx.run_id,
        'question': question,
        'values': list(values) if values else None,
        'facts': ctx.facts,
        'citations': ctx.citations,
        'status': 'ok',
        'require_confirm': bool(require_confirm),
        'confirmed': False,
        '_emit': emit,
        'plan': plan,
        'intent_hint': INTENT.get(plan.get('inherit'), '') if plan.get('inherit') else '',
    }

    if emit:
        emit('step', {'seq': 0, 'node': 'route', 'label': '开始处理'})

    outcome = get_graph().invoke(state, ctx, checkpointer=JsonCheckpointer(), emit=emit)
    state = outcome['state']
    latency = int((time.time() - started) * 1000)
    state['latency_ms'] = latency

    # 节点级轨迹单独落库（seq 偏移 1000），便于回放时区分「节点」与「工具」
    for step in outcome.get('steps') or []:
        db.add_step(ctx.run_id, 1000 + int(step.get('seq', 0)), step.get('node', ''),
                    tool='@node', verdict=step.get('verdict', ''),
                    latency_ms=int(step.get('latency_ms') or 0),
                    result_digest=(step.get('error') or '')[:120])

    # 落库（图里 persist 节点写 run，这里补一次延迟与最终状态）
    if outcome['status'] != 'interrupted':
        db.update_run(ctx.run_id,
                      status=state.get('status', 'ok'),
                      answer_md=state.get('answer', ''),
                      citations_json=json.dumps(state.get('citations') or [], ensure_ascii=False),
                      latency_ms=latency)

    result = _result(ctx, question, state.get('intent', ''),
                     state.get('status', 'ok'), state.get('answer', ''),
                     state.get('citations') or [], state.get('verdict') or {},
                     state.get('verify') or {}, started)
    result['model_used'] = state.get('model_used', 'template')
    result['policy_issues'] = state.get('policy_issues', [])
    result['tier'] = state.get('tier', 'confident')
    result['uncertainty'] = state.get('uncertainty') or {}
    result['graph'] = [dict(step) for step in outcome['steps']]
    result['cached'] = bool(state.get('cached'))

    if outcome['status'] == 'interrupted':
        result['status'] = 'interrupted'
        result['pending'] = outcome.get('pending') or {}
        result['resume_at'] = outcome.get('resume_at')

    if emit and outcome['status'] == 'interrupted':
        emit('interrupted', {'run_id': ctx.run_id,
                             'pending': outcome.get('pending') or {}})
    return result


def resume(run_id: str, ctx: AgentContext, confirmed: bool = True,
           emit=None) -> Dict:
    """从检查点恢复执行（默认走「已确认」分支）。"""
    checkpoint = db.load_checkpoint(run_id)
    if not checkpoint:
        raise ValueError('没有找到可恢复的检查点: %s' % run_id)

    state = checkpoint['state']
    state['run_id'] = run_id
    state['confirmed'] = bool(confirmed)
    state['require_confirm'] = False
    state['status'] = 'ok'
    ctx.run_id = run_id
    ctx.question = state.get('question', '')
    ctx.facts = state.get('facts') or []
    ctx.citations = state.get('citations') or []
    state['facts'] = ctx.facts
    state['citations'] = ctx.citations
    state['_emit'] = emit

    started = time.time()
    outcome = get_graph().invoke(state, ctx, checkpointer=JsonCheckpointer(),
                                 emit=emit, start=checkpoint['next_node'] or 'compose')
    state = outcome['state']
    latency = int((time.time() - started) * 1000)
    db.update_run(run_id, status=state.get('status', 'ok'),
                  answer_md=state.get('answer', ''),
                  citations_json=json.dumps(state.get('citations') or [], ensure_ascii=False),
                  latency_ms=latency)

    result = _result(ctx, ctx.question, state.get('intent', ''),
                     state.get('status', 'ok'), state.get('answer', ''),
                     state.get('citations') or [], state.get('verdict') or {},
                     state.get('verify') or {}, started)
    result['tier'] = state.get('tier', 'confident')
    result['uncertainty'] = state.get('uncertainty') or {}
    result['graph'] = [dict(step) for step in outcome['steps']]
    result['resumed'] = True
    return result


def _result(ctx, question, intent, status, answer, citations, q_verdict, check, started) -> Dict:
    return {
        'run_id': ctx.run_id,
        'question': question,
        'intent': intent,
        'intent_label': INTENT_LABEL.get(intent, intent),
        'status': status,
        'answer_md': answer,
        'citations': citations,
        'facts': ctx.facts,
        'steps': ctx.steps,
        'risk': q_verdict.get('risk', 'low'),
        'verify': check,
        'artifacts': list(ctx.artifacts),
        'latency_ms': int((time.time() - started) * 1000),
    }


def stream(ctx: AgentContext, question: str, values: Optional[List[float]] = None,
           require_confirm: bool = False):
    """SSE 事件生成器：yield (event, data)。"""
    events: List[Tuple[str, Dict]] = []

    def emit(name: str, data: Dict) -> None:
        events.append((name, data))

    result = run(ctx, question, values, emit=emit, require_confirm=require_confirm)

    # 先回放步骤，再给 token（简化流式：整段答案分片）
    for name, data in events:
        if name in ('done',):
            continue
        if name in ('interrupt', 'interrupted'):
            payload = dict(data or {})
            payload.setdefault('run_id', result['run_id'])
            yield 'interrupt', payload
            continue
        if name == 'node':
            node = data.get('node', '')
            yield 'step', {
                'seq': data.get('seq', 0),
                'node': node,
                'label': NODE_LABELS.get(node, node),
                'ms': data.get('ms'),
                'ok': True,
            }
            continue
        yield name, data

    if result.get('status') == 'interrupted':
        yield 'done', {
            'run_id': result['run_id'],
            'intent': result.get('intent'),
            'status': 'interrupted',
            'pending': result.get('pending') or {},
            'resume_at': result.get('resume_at'),
            'citations': result.get('citations') or [],
            'tier': result.get('tier'),
            'uncertainty': result.get('uncertainty') or {},
        }
        return

    answer = result['answer_md']
    chunk = 120
    for i in range(0, len(answer), chunk):
        yield 'token', {'text': answer[i:i + chunk]}

    yield 'done', {
        'run_id': result['run_id'],
        'intent': result['intent'],
        'status': result['status'],
        'citations': result['citations'],
        'risk': result['risk'],
        'latency_ms': result['latency_ms'],
        'model_used': result.get('model_used', 'template'),
        'verify': result.get('verify', {}),
        'tier': result.get('tier', 'confident'),
        'uncertainty': result.get('uncertainty') or {},
        'graph': result.get('graph') or [],
    }
