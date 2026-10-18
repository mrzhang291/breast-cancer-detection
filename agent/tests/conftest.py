import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.chdir(ROOT)
os.environ.setdefault('AGENT_LLM', 'off')  # 测试不依赖网络

from agent import runtime as agent_runtime  # noqa: E402
from agent.context import AgentContext  # noqa: E402

FEATURES = [
    17.99, 10.38, 122.8, 1001.0, 0.1184, 0.2776, 0.3001, 0.1471, 0.2419, 0.07871,
    1.095, 0.9053, 8.589, 153.4, 0.006399, 0.04904, 0.05373, 0.01587, 0.03003, 0.006193,
    25.38, 17.33, 184.6, 2019.0, 0.1622, 0.6656, 0.7119, 0.2654, 0.4601, 0.1189,
]


def _fake_predict(features):
    return {'output': '恶性', 'raw_output': 1, 'confidence': 0.999,
            'time': 0.02, 'model_type': 'fake'}


def _fake_explain(features, prediction, confidence):
    return {
        'prediction': prediction,
        'confidence': confidence,
        'top_features': [
            {'name': 'area_worst', 'value': features[23], 'shap_value': 0.42,
             'importance': 0.42, 'direction': '推向恶性'},
            {'name': 'concave points_mean', 'value': features[7], 'shap_value': 0.31,
             'importance': 0.31, 'direction': '推向恶性'},
        ],
    }


def _fake_records(user_id, page, size):
    feats = {'feature_%d' % i: v for i, v in enumerate(FEATURES, start=1)}
    return {'total': 2, 'items': [
        {'id': 1, 'prediction_result': 'Malignant', 'confidence': 0.99,
         'created_at': '2026-05-18 10:00:00', 'features': dict(feats)},
        {'id': 2, 'prediction_result': 'Benign', 'confidence': 0.91,
         'created_at': '2026-05-18 11:00:00', 'features': dict(feats)},
    ]}


def _fake_stats(user_id):
    return {'total': 2, 'benign': 1, 'malignant': 1, 'avg_confidence': 0.95}


@pytest.fixture(scope='session', autouse=True)
def bind_runtime():
    agent_runtime.get().bind(predict=_fake_predict, explain=_fake_explain,
                             fetch_records=_fake_records, fetch_stats=_fake_stats)
    from agent import db
    from agent.rag import index as rag_index
    db.init_schema()

    # 新克隆的仓库里没有预建检索索引，测试前补建，避免依赖本地残留文件
    try:
        conn = db.connect()
        chunks = conn.execute('SELECT COUNT(*) FROM rag_chunks').fetchone()[0]
        conn.close()
    except Exception:  # noqa: BLE001
        chunks = 0
    if not chunks:
        rag_index.rebuild()

    # 清掉历史缓存：索引缺失时跑出来的无引用答案会被缓存，污染后续测试
    try:
        conn = db.connect()
        conn.execute('DELETE FROM answer_cache')
        conn.commit()
        conn.close()
    except Exception:  # noqa: BLE001
        pass

    yield


@pytest.fixture()
def ctx():
    return AgentContext(user_id=3, role_id=3, lang='zh')


@pytest.fixture()
def features():
    return list(FEATURES)
