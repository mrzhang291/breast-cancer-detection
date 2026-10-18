"""会话统计工具：回答"我有几个对话/最近聊了什么"。"""
from .. import db, registry


@registry.tool(
    'sessions',
    description='查询当前用户的 AI 助手会话统计（会话数、消息数、活跃天数、最近会话）',
    schema={'type': 'object', 'properties': {}, 'required': []},
    permission='records:read',
    timeout=10.0,
)
def sessions(ctx):
    stats = db.session_stats(ctx.user_id)
    fact = registry.make_fact('sessions', stats, tool='sessions',
                              run_id=ctx.run_id, ident='sess_%s' % (ctx.run_id or '')[:8])
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=stats, facts=[fact])
