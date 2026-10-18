"""向量检索：fastembed 本地嵌入 + SQLite 存向量，缺失时自动降级。"""
import io
import math
import os
import sys
from typing import Dict, List, Optional

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

MODEL_NAME = os.environ.get('RAG_EMBED_MODEL', 'BAAI/bge-small-zh-v1.5')
_DIM = 512
_STATE = {'model': None, 'checked': False, 'error': ''}


def _db():
    from .. import db
    return db


SHIPPED_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'agent', 'knowledge', 'rag_vectors.sqlite')


def ensure_schema() -> None:
    conn = _db().connect()
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS rag_vectors ('
                     'clause_id TEXT PRIMARY KEY, dim INTEGER, vec BLOB, model TEXT)')
        conn.commit()
        count = conn.execute('SELECT COUNT(*) FROM rag_vectors').fetchone()[0]
        if os.path.exists(SHIPPED_DB):
            import sqlite3
            src = sqlite3.connect(SHIPPED_DB)
            try:
                shipped = src.execute('SELECT COUNT(*) FROM rag_vectors').fetchone()[0]
                if shipped and shipped != count:
                    rows = src.execute(
                        'SELECT clause_id, dim, vec, model FROM rag_vectors').fetchall()
                    conn.execute('DELETE FROM rag_vectors')
                    conn.executemany('INSERT OR REPLACE INTO rag_vectors'
                                     ' (clause_id, dim, vec, model) VALUES (?,?,?,?)', rows)
                    conn.commit()
            finally:
                src.close()
    finally:
        conn.close()


def _instance():
    if _STATE['checked']:
        return _STATE['model']
    _STATE['checked'] = True
    try:
        from fastembed import TextEmbedding
        from .fetch_model import ensure_model
        path = ensure_model()
        _STATE['model'] = TextEmbedding(model_name=MODEL_NAME, specific_model_path=path)
    except Exception as exc:  # noqa: BLE001
        _STATE['error'] = str(exc)[:200]
        _STATE['model'] = None
    return _STATE['model']


def available() -> bool:
    if np is None:
        return False
    ensure_schema()
    conn = _db().connect()
    try:
        row = conn.execute('SELECT COUNT(*) FROM rag_vectors').fetchone()
        count = row[0] if row else 0
    finally:
        conn.close()
    return count > 0 and _instance() is not None


def status() -> Dict:
    ensure_schema()
    conn = _db().connect()
    try:
        count = conn.execute('SELECT COUNT(*) FROM rag_vectors').fetchone()[0]
    finally:
        conn.close()
    return {'vectors': count, 'model': MODEL_NAME,
            'loaded': _STATE['model'] is not None, 'error': _STATE['error']}


def _embed_texts(texts: List[str]) -> List[List[float]]:
    model = _instance()
    if model is None:
        raise RuntimeError('embedding model unavailable: %s' % _STATE['error'])
    return [list(map(float, vec)) for vec in model.embed(texts)]


def build(batch: int = 32) -> Dict:
    """为所有条款重建向量。"""
    from . import corpus
    if np is None:
        raise RuntimeError('numpy missing')
    chunks = corpus.all_chunks()
    ensure_schema()
    conn = _db().connect()
    try:
        conn.execute('DELETE FROM rag_vectors')
        total = 0
        for start in range(0, len(chunks), batch):
            part = chunks[start:start + batch]
            texts = [('%s\n%s' % (c['section'], c['text']))[:1500] for c in part]
            vectors = _embed_texts(texts)
            rows = []
            for chunk, vec in zip(part, vectors):
                arr = np.asarray(vec, dtype=np.float32)
                rows.append((chunk['clause_id'], int(arr.shape[0]), arr.tobytes(), MODEL_NAME))
                total += 1
            conn.executemany('INSERT OR REPLACE INTO rag_vectors'
                             ' (clause_id, dim, vec, model) VALUES (?,?,?,?)', rows)
            conn.commit()
        return {'vectors': total, 'model': MODEL_NAME}
    finally:
        conn.close()


def search(query: str, k: int = 30) -> List[Dict]:
    """余弦相似度检索；不可用时返回空列表。"""
    if not available():
        return []
    qv = np.asarray(_embed_texts([query])[0], dtype=np.float32)
    qn = float(np.linalg.norm(qv)) or 1.0

    conn = _db().connect()
    try:
        rows = conn.execute('SELECT clause_id, dim, vec FROM rag_vectors').fetchall()
    finally:
        conn.close()

    scored = []
    for row in rows:
        vec = np.frombuffer(row['vec'], dtype=np.float32)
        if vec.shape[0] != qv.shape[0]:
            continue
        denom = (float(np.linalg.norm(vec)) or 1.0) * qn
        score = float(np.dot(qv, vec) / denom)
        scored.append((row['clause_id'], score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [{'clause_id': cid, 'score': round(score, 6)} for cid, score in scored[:k]]
