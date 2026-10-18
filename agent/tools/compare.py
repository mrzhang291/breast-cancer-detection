"""两次预测之间的特征对比。"""
import json
import os

from .. import registry

_FEATURES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              'knowledge', 'features.json')
_CACHE = {}


def _features():
    if 'items' not in _CACHE:
        with open(_FEATURES_PATH, encoding='utf-8') as fh:
            data = json.load(fh)
        _CACHE['items'] = data.get('items', []) if isinstance(data, dict) else data
    return _CACHE['items']


@registry.tool(
    'compare_records',
    description='对比两次预测的 30 项细胞核特征，找出差异最大的项目',
    schema={
        'type': 'object',
        'properties': {
            'current': {'type': 'array', 'items': {'type': 'number'}},
            'previous': {'type': 'array', 'items': {'type': 'number'}},
        },
        'required': ['current', 'previous'],
    },
    permission='records:read',
    timeout=10.0,
)
def compare_records(ctx, current, previous):
    items = _features()
    if len(current) != len(items) or len(previous) != len(items):
        return registry.ToolResult(ok=False, error='特征数量与模型不一致',
                                   error_type='invalid_input')

    diffs = []
    for meta, cur, prev in zip(items, current, previous):
        cur = float(cur)
        prev = float(prev)
        base = abs(prev) if abs(prev) > 1e-9 else 1e-9
        rel = (cur - prev) / base
        diffs.append({
            'feature': meta['feature'],
            'name_zh': meta.get('name_zh') or meta['feature'],
            'current': round(cur, 4),
            'previous': round(prev, 4),
            'change_pct': round(rel * 100, 1),
            'abs_change_pct': abs(rel),
        })

    diffs.sort(key=lambda d: d['abs_change_pct'], reverse=True)
    top = diffs[:6]

    rising = [d for d in top if d['change_pct'] > 0]
    falling = [d for d in top if d['change_pct'] < 0]

    fact = registry.make_fact(
        'compare',
        {
            'top': top,
            'changed_count': sum(1 for d in diffs if d['abs_change_pct'] >= 5),
            'rising': len(rising),
            'falling': len(falling),
        },
        tool='compare_records', run_id=ctx.run_id,
        ident='cmp_%s' % ctx.run_id[:8],
    )
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=fact['payload'], facts=[fact])
