"""子代理工具：主循环通过它把只读分析任务委派出去。"""
from .. import registry


@registry.tool(
    'delegate',
    description='把只读分析子任务交给子代理执行（查记录、算统计、检索知识、解释特征）',
    schema={
        'type': 'object',
        'properties': {
            'task': {'type': 'string'},
            'role': {'type': 'string', 'enum': ['analyst']},
        },
        'required': ['task'],
    },
    permission='agent:delegate',
    timeout=90.0,
    idempotent=False,
)
def delegate(ctx, task='', role='analyst'):
    from ..core.subagent import SPECS, run_subagent

    task = (task or '').strip()
    if not task:
        return registry.ToolResult(ok=False, error='子任务为空', error_type='validation')

    spec = SPECS.get(role) or SPECS['analyst']
    result = run_subagent(task, ctx, spec=spec)

    if not result.get('ok') and result.get('stopped') == 'unavailable':
        return registry.ToolResult(ok=False, error=result['answer'],
                                   error_type='unavailable')

    return registry.ToolResult(
        ok=bool(result.get('ok')),
        data={'answer': result.get('answer', ''),
              'steps': result.get('steps', []),
              'spec': result.get('spec')},
        error='' if result.get('ok') else '子代理未给出最终回答',
        error_type='' if result.get('ok') else 'incomplete',
    )
