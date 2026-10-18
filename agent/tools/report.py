"""报告导出工具：把当前 run 的结论渲染成可下载产物。"""
import time

from .. import registry, runtime


def _payload_of(ctx, kind):
    for fact in ctx.facts:
        if fact.get('kind') == kind:
            return fact.get('payload') or {}
    return {}


def _collect_range(ctx, days=None, limit=None):
    """取记录并聚合：区间小结的数据源。"""
    page = runtime.get().fetch_records(str(ctx.user_id), 1, 50) or {}
    items = list(page.get('items') or [])

    def _ts(item):
        return str(item.get('created_at') or '')

    items.sort(key=_ts, reverse=True)

    if days:
        cutoff = time.time() - int(days) * 86400
        kept = []
        for item in items:
            raw = _ts(item)[:19].replace('T', ' ')
            try:
                ts = time.mktime(time.strptime(raw, '%Y-%m-%d %H:%M:%S'))
            except Exception:  # noqa: BLE001
                kept.append(item)
                continue
            if ts >= cutoff:
                kept.append(item)
        items = kept

    limit = int(limit or 30)
    items = items[:min(limit, 30)]

    series = []
    for item in items:
        series.append({
            'id': item.get('id'),
            'at': _ts(item)[:19].replace('T', ' '),
            'result': item.get('prediction_result') or item.get('result') or '',
            'confidence': float(item.get('confidence') or 0),
        })

    malignant = sum(1 for s in series if s['result'] in ('恶性', 'Malignant'))
    benign = len(series) - malignant
    confs = [s['confidence'] for s in series] or [0]
    stats = {
        'total': len(series),
        'benign': benign,
        'malignant': malignant,
        'avg_conf': sum(confs) / len(confs),
        'max_conf': max(confs),
        'min_conf': min(confs),
    }
    return series, stats

def _top_features(ctx):
    shap = _payload_of(ctx, 'shap')
    items = shap.get('top_features') or []
    out = []
    for item in items[:8]:
        name = (item.get('name_zh') or item.get('name') or item.get('feature') or '特征')
        value = item.get('value')
        if value is None:
            value = item.get('contribution')
        if value is None:
            value = item.get('shap')
        try:
            out.append({'name': str(name), 'value': float(value or 0)})
        except (TypeError, ValueError):
            continue
    return out


@registry.tool(
    'export_report',
    description='生成可下载的分析报告（PDF/CSV），产物会随本次运行一并返回',
    schema={
        'type': 'object',
        'properties': {'kind': {'type': 'string',
                               'enum': ['single', 'compare', 'range', 'batch', 'csv']},
                       'days': {'type': 'integer', 'minimum': 1, 'maximum': 365},
                       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 30}},
        'required': [],
    },
    permission='report:generate',
    timeout=25.0,
    idempotent=False,
)
def export_report(ctx, kind='single', days=None, limit=None):
    rt = runtime.get()
    rt.require('render_report')

    context = ctx.context or {}

    if kind == 'single' and not _payload_of(ctx, 'prediction'):
        return registry.ToolResult(ok=False,
                                   error='当前没有预测结果，先在首页做一次预测再生成报告',
                                   error_type='empty')

    series = stats = None
    if kind == 'range':
        series, stats = _collect_range(ctx, days, limit)
        if not series:
            return registry.ToolResult(ok=False, error='该区间内没有预测记录',
                                       error_type='empty')

    payload = {
        'user_id': ctx.user_id,
        'run_id': ctx.run_id,
        'username': context.get('username') or ctx.user_id,
        'record_id': context.get('record_id'),
        'prediction': _payload_of(ctx, 'prediction'),
        'top_features': _top_features(ctx),
        'narrative': context.get('narrative') or '',
        'citations': list(ctx.citations),
        'compare': _payload_of(ctx, 'compare'),
        'series': series,
        'stats': stats,
        'window': {'mode': 'days' if days else ('limit' if limit else 'all'),
                   'n': int(days or limit or 0)},
    }

    try:
        artifact = rt.render_report(kind, payload)
    except Exception as exc:  # noqa: BLE001
        return registry.ToolResult(ok=False, error='报告渲染失败: %s' % str(exc)[:120],
                                   error_type='runtime')

    if not artifact or not artifact.get('filename'):
        return registry.ToolResult(ok=False, error='报告渲染失败', error_type='runtime')

    ctx.add_artifact(artifact)
    return registry.ToolResult(ok=True, data={'artifact': artifact['filename']},
                               artifacts=[artifact])
