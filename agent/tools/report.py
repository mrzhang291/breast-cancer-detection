"""报告导出工具：把当前 run 的结论渲染成可下载产物。"""
from .. import registry, runtime


def _payload_of(ctx, kind):
    for fact in ctx.facts:
        if fact.get('kind') == kind:
            return fact.get('payload') or {}
    return {}


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
        'properties': {'kind': {'type': 'string', 'enum': ['single', 'compare', 'range', 'batch', 'csv']}},
        'required': [],
    },
    permission='report:generate',
    timeout=25.0,
    idempotent=False,
)
def export_report(ctx, kind='single'):
    rt = runtime.get()
    rt.require('render_report')

    context = ctx.context or {}
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
