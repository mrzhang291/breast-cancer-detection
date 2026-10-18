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
    if kind == 'batch':
        rows = context.get('batch') or []
        if not rows:
            return registry.ToolResult(
                ok=False, error='没有拿到批量结果，请在「批量结果」页面里让我汇总',
                error_type='empty')
        payload_extra = {'batch': rows}
    else:
        payload_extra = {}
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
        'input_features': (_payload_of(ctx, 'input').get('features') or []),
        'similar': _payload_of(ctx, 'case'),
        'compare': _payload_of(ctx, 'compare'),
        'series': series,
        'stats': stats,
        'window': {'mode': 'days' if days else ('limit' if limit else 'all'),
                   'n': int(days or limit or 0)},
        **payload_extra,
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


def _feature_names():
    import json as _json
    import os as _os
    path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         'knowledge', 'features.json')
    try:
        with open(path, encoding='utf-8') as fh:
            data = _json.load(fh)
        items = data.get('items', []) if isinstance(data, dict) else data
        return [it.get('name_zh') or it.get('feature') for it in items]
    except Exception:  # noqa: BLE001
        return []


@registry.tool(
    'export_data',
    description='导出当前账号的原始预测记录为 CSV',
    schema={'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50}},
            'required': []},
    permission='export',
    timeout=20.0,
    idempotent=False,
)
def export_data(ctx, limit=30):
    rt = runtime.get()
    rt.require('fetch_records', 'render_report')

    page = rt.fetch_records(str(ctx.user_id), 1, 50) or {}
    items = list(page.get('items') or [])
    items.sort(key=lambda item: str(item.get('created_at') or ''), reverse=True)
    items = items[:min(int(limit or 30), 50)]

    names = _feature_names()
    series = []
    for item in items:
        feats = item.get('features') or {}
        values = []
        for idx in range(1, 31):
            values.append(feats.get('feature_%d' % idx, ''))
        series.append({
            'id': item.get('id'),
            'at': str(item.get('created_at') or '')[:19].replace('T', ' '),
            'result': item.get('prediction_result') or item.get('result') or '',
            'confidence': round(float(item.get('confidence') or 0), 4),
            'features': values,
        })

    if not series:
        return registry.ToolResult(ok=False, error='没有可导出的记录', error_type='empty')

    payload = {
        'user_id': ctx.user_id,
        'run_id': ctx.run_id,
        'series': series,
        'feature_names': names,
    }
    try:
        artifact = rt.render_report('csv', payload)
    except Exception as exc:  # noqa: BLE001
        return registry.ToolResult(ok=False, error='导出失败: %s' % str(exc)[:100],
                                   error_type='runtime')

    ctx.add_artifact(artifact)
    return registry.ToolResult(ok=True, data={'rows': len(series)}, artifacts=[artifact])
