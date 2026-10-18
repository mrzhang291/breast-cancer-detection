"""SHAP 归因工具：解释"为什么模型这么判"。"""
from .. import registry, runtime


@registry.tool(
    'explain',
    description='对一次预测做特征归因（SHAP），返回影响力最大的若干特征及其方向',
    schema={
        'type': 'object',
        'properties': {
            'features': {'type': 'array', 'items': {'type': 'number'},
                         'minItems': 30, 'maxItems': 30},
            'prediction': {'type': 'string'},
            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
            'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 10},
        },
        'required': ['features', 'prediction', 'confidence'],
    },
    permission='explain',
    timeout=20.0,
)
def explain(ctx, features, prediction, confidence, top_k=5):
    rt = runtime.get()
    rt.require('explain')

    result = rt.explain(features, prediction, confidence)
    if not result:
        raise RuntimeError('归因服务返回空结果')

    top = result.get('top_features', [])[:top_k]
    fact = registry.make_fact(
        'shap',
        {'prediction': prediction, 'confidence': round(float(confidence), 6),
         'top_features': top},
        tool='explain', run_id=ctx.run_id,
        ident='shap_%s' % ctx.run_id[:8],
    )
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=fact['payload'], facts=[fact])
