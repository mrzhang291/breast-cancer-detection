"""预测工具：30 项特征 -> 良恶性 + 置信度。

工具的返回值就是事实来源；模型只能引用，不能改写数值。
"""
from .. import registry, runtime

FEATURE_SCHEMA = {
    'type': 'object',
    'properties': {
        'features': {
            'type': 'array',
            'items': {'type': 'number'},
            'minItems': 30,
            'maxItems': 30,
        },
    },
    'required': ['features'],
}


@registry.tool(
    'predict',
    description='用训练好的模型对 30 项细胞核特征做良恶性预测，返回结果与置信度',
    schema=FEATURE_SCHEMA,
    permission='predict',
    timeout=10.0,
    idempotent=True,
)
def predict(ctx, features):
    rt = runtime.get()
    rt.require('predict')

    result = rt.predict(features)
    if not result or 'output' not in result:
        raise RuntimeError('预测服务返回空结果')

    fact = registry.make_fact(
        'prediction',
        {
            'output': result['output'],
            'raw_output': int(result.get('raw_output', 0)),
            'confidence': round(float(result['confidence']), 6),
            'latency_ms': round(float(result.get('time', 0)) * 1000, 1),
            'model_type': result.get('model_type', 'unknown'),
        },
        tool='predict', run_id=ctx.run_id,
        ident='pred_%s' % ctx.run_id[:8],
    )
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=fact['payload'], facts=[fact])
