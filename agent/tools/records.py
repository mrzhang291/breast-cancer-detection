"""历史记录与统计工具（带行级权限）。"""
from .. import policy, registry, runtime


@registry.tool(
    'records',
    description='查询某个用户的预测历史记录与统计摘要',
    schema={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'string'},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50},
        },
        'required': [],
    },
    permission='records:read',
    timeout=10.0,
)
def records(ctx, user_id=None, limit=10):
    rt = runtime.get()
    rt.require('fetch_records')

    target = str(user_id) if user_id else str(ctx.user_id)
    if target != str(ctx.user_id) and not policy.can_view_other_users(ctx):
        return registry.ToolResult(ok=False, error='无权查看其他用户的记录',
                                   error_type='permission')

    page = rt.fetch_records(target, 1, int(limit)) or {}
    items = page.get('items', [])
    fact = registry.make_fact(
        'record',
        {'user_id': target, 'total': int(page.get('total', len(items))),
         'items': items[:int(limit)]},
        tool='records', run_id=ctx.run_id,
        ident='rec_%s' % ctx.run_id[:8],
    )
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=fact['payload'], facts=[fact])


@registry.tool(
    'statistics',
    description='查询某个用户的预测统计（总数、良恶性分布、平均置信度）',
    schema={'type': 'object', 'properties': {'user_id': {'type': 'string'}}, 'required': []},
    permission='stats:read',
    timeout=10.0,
)
def statistics(ctx, user_id=None):
    rt = runtime.get()
    rt.require('fetch_stats')

    target = str(user_id) if user_id else str(ctx.user_id)
    if target != str(ctx.user_id) and not policy.can_view_other_users(ctx):
        return registry.ToolResult(ok=False, error='无权查看其他用户的统计',
                                   error_type='permission')

    stats = rt.fetch_stats(target) or {}
    payload = {
        'user_id': target,
        'total': int(stats.get('total', 0)),
        'benign': int(stats.get('benign', 0)),
        'malignant': int(stats.get('malignant', 0)),
        'avg_confidence': round(float(stats.get('avg_confidence', 0) or 0), 6),
    }
    fact = registry.make_fact('stat', payload, tool='statistics',
                              run_id=ctx.run_id, ident='stat_%s' % ctx.run_id[:8])
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=payload, facts=[fact])
