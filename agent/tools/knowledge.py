"""知识检索工具：从特征词典与系统文档里取条款，并把 clause_id 记为引用。"""
from .. import registry
from ..rag import hybrid, index


@registry.tool(
    'search_knowledge',
    description='在特征词典与系统文档中检索相关条款，返回带 clause_id 的依据',
    schema={
        'type': 'object',
        'properties': {
            'query': {'type': 'string'},
            'k': {'type': 'integer', 'minimum': 1, 'maximum': 10},
            'domains': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['query'],
    },
    permission='knowledge:read',
    timeout=25.0,
)
def search_knowledge(ctx, query, k=5, domains=None):
    prefer = 'howto' if any(w in query for w in ('怎么', '如何', '在哪', '步骤')) else ''
    try:
        hits = hybrid.search(query, k=int(k), prefer=prefer, domains=domains)
    except Exception:  # noqa: BLE001
        hits = index.search(query, k=int(k), prefer=prefer)
    payload = {
        'query': query,
        'count': len(hits),
        'hits': [{key: hit.get(key) for key in
                  ('clause_id', 'source', 'version', 'section', 'text', 'score',
                   'domain', 'level', 'url')}
                 for hit in hits],
    }

    facts = []
    if hits:
        fact = registry.make_fact('clause', payload, tool='search_knowledge',
                                  run_id=ctx.run_id, ident='rag_%s' % ctx.run_id[:8])
        facts.append(fact)
        ctx.add_fact(fact)
        for hit in hits:
            ctx.add_citation(hit['clause_id'])

    return registry.ToolResult(ok=True, data=payload, facts=facts)


@registry.tool(
    'get_clause',
    description='按 clause_id 精确取一条条款（用于已知特征编号时的确定性查询）',
    schema={'type': 'object', 'properties': {'clause_id': {'type': 'string'}},
            'required': ['clause_id']},
    permission='knowledge:read',
    timeout=5.0,
)
def get_clause(ctx, clause_id):
    chunk = index.get_chunk(clause_id)
    if not chunk:
        return registry.ToolResult(ok=False, error='条款不存在: %s' % clause_id,
                                   error_type='validation')

    payload = {
        'query': clause_id,
        'count': 1,
        'hits': [{
            'clause_id': chunk['clause_id'],
            'source': chunk['source'],
            'version': chunk['version'],
            'section': chunk['section'],
            'text': chunk['text'],
            'score': 1.0,
        }],
    }
    fact = registry.make_fact('clause', payload, tool='get_clause',
                              run_id=ctx.run_id, ident='rag_%s' % ctx.run_id[:8])
    ctx.add_fact(fact)
    ctx.add_citation(chunk['clause_id'])
    return registry.ToolResult(ok=True, data=payload, facts=[fact])
