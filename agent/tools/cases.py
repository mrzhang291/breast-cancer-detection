"""相似病例检索：在数据集的历史样本里找最接近的 k 个。

注意：这是"同一批训练数据里的邻居"，只能用于直观参照，
不能当作临床证据 —— 因此在事实里明确标注 evidence_level。
"""
import os
from typing import Dict

import numpy as np
import pandas as pd

from .. import registry

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(ROOT, 'Breast Cancer Data.csv')

_CACHE: Dict = {}


def _load():
    if _CACHE:
        return _CACHE

    df = pd.read_csv(CSV)
    X = df.iloc[:, 2:32].values.astype(float)
    y = df.iloc[:, 1].astype(str).str.strip().values

    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    Xz = (X - mean) / std
    norms = np.linalg.norm(Xz, axis=1)
    norms[norms == 0] = 1.0

    _CACHE.update({'X': X, 'Xz': Xz, 'y': y, 'mean': mean, 'std': std, 'norms': norms})
    return _CACHE


@registry.tool(
    'similar_cases',
    description='在当前特征向量附近检索最相似的历史样本，用于直观对照',
    schema={
        'type': 'object',
        'properties': {
            'features': {'type': 'array', 'items': {'type': 'number'},
                         'minItems': 30, 'maxItems': 30},
            'k': {'type': 'integer', 'minimum': 1, 'maximum': 10},
        },
        'required': ['features'],
    },
    permission='cases:read',
    timeout=5.0,
)
def similar_cases(ctx, features, k=5):
    data = _load()
    vector = np.asarray(features, dtype=float)
    vector_z = (vector - data['mean']) / data['std']
    norm = np.linalg.norm(vector_z) or 1.0
    sims = data['Xz'].dot(vector_z) / (data['norms'] * norm)

    order = np.argsort(sims)[::-1][:int(k)]
    cases = []
    for rank, idx in enumerate(order, start=1):
        label = '恶性' if data['y'][idx] == 'M' else '良性'
        cases.append({
            'rank': rank,
            'sample_index': int(idx),
            'label': label,
            'similarity': round(float(sims[idx]), 4),
            'radius_mean': round(float(data['X'][idx][0]), 3),
            'area_mean': round(float(data['X'][idx][3]), 2),
            'concave_points_mean': round(float(data['X'][idx][7]), 5),
        })

    malignant = sum(1 for c in cases if c['label'] == '恶性')
    payload = {'k': len(cases), 'malignant_count': malignant,
               'benign_count': len(cases) - malignant, 'cases': cases,
               'evidence_level': 'dataset_neighbor'}

    fact = registry.make_fact('case', payload, tool='similar_cases',
                              run_id=ctx.run_id, ident='case_%s' % ctx.run_id[:8])
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=payload, facts=[fact])
