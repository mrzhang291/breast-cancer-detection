"""混合检索：词法（TF-IDF）+ 向量（fastembed）RRF 融合，再用 LLM 重排。

降级策略：
    - 没有向量索引 -> 只用词法，重排照常
    - 模型不可用   -> 跳过重排，保留 RRF 顺序
"""
import json
import os
from typing import Dict, List, Optional

from . import embed, index

RRF_K = 60
CANDIDATE_N = 20
RERANK_ENV = os.environ.get('RAG_RERANK', 'auto').strip().lower()


def _load_details(ids: List[str]) -> Dict[str, Dict]:
    if not ids:
        return {}
    from .. import db
    conn = db.connect()
    try:
        placeholders = ','.join('?' * len(ids))
        rows = conn.execute(
            'SELECT clause_id, doc_id, source, version, section, text, meta_json'
            ' FROM rag_chunks WHERE clause_id IN (%s)' % placeholders, ids).fetchall()
    finally:
        conn.close()
    out = {}
    for row in rows:
        item = dict(row)
        try:
            item['meta'] = json.loads(item.get('meta_json') or '{}')
        except ValueError:
            item['meta'] = {}
        out[item['clause_id']] = item
    return out


def _fuse(lex: List[Dict], vec: List[Dict]) -> List[Dict]:
    scores: Dict[str, float] = {}
    for rank, hit in enumerate(lex):
        cid = hit['clause_id']
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, hit in enumerate(vec):
        cid = hit['clause_id']
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [{'clause_id': cid, 'score': round(score, 6)} for cid, score in ordered]


def _llm_rerank(query: str, candidates: List[Dict], top_n: int) -> Optional[List[str]]:
    if RERANK_ENV == 'off' or not candidates:
        return None
    try:
        from .. import llm
        if not llm.available():
            return None
        items = [{'id': c['clause_id'], 'title': c.get('section') or '',
                  'text': (c.get('text') or '')[:200]} for c in candidates]
        system = ('你是医学检索重排器。按与问题的相关程度给候选条款排序，只输出 JSON 数组，'
                  '元素是条款 id，最多 8 个，不要解释。不相关的不要输出。')
        user = '问题：%s\n\n候选：%s' % (query, json.dumps(items, ensure_ascii=False))
        text = llm.complete(system, user, temperature=0.0, max_tokens=300)
        if not text:
            return None
        start, end = text.find('['), text.rfind(']')
        if start < 0 or end < start:
            return None
        order = json.loads(text[start:end + 1])
        valid = {c['clause_id'] for c in candidates}
        picked = [str(cid) for cid in order if str(cid) in valid]
        return picked or None
    except Exception:  # noqa: BLE001
        return None


def search(query: str, k: int = 5, prefer: str = '') -> List[Dict]:
    lex = index.search(query, k=30, prefer=prefer)
    vec = []
    try:
        if embed.available():
            vec = embed.search(query, k=30)
    except Exception:  # noqa: BLE001
        vec = []

    fused = _fuse(lex, vec)[:CANDIDATE_N]
    if not fused:
        return []

    details = _load_details([c['clause_id'] for c in fused])
    lex_scores = {h['clause_id']: float(h.get('score') or 0) for h in lex}
    vec_scores = {h['clause_id']: float(h.get('score') or 0) for h in vec}
    candidates = []
    for item in fused:
        cid = item['clause_id']
        row = details.get(cid)
        if not row:
            continue
        # score 统一成"可读的相关度"：词法分优先，纯向量命中按余弦折算
        score = lex_scores.get(cid)
        if not score:
            score = round(vec_scores.get(cid, 0.0) * 40.0, 3)
        candidates.append({
            'clause_id': row['clause_id'],
            'doc_id': row['doc_id'],
            'source': row['source'],
            'version': row['version'],
            'section': row['section'],
            'text': row['text'],
            'score': round(score, 3),
            'fused': item['score'],
            'meta': row.get('meta') or {},
        })

    order = _llm_rerank(query, candidates, k)
    if order:
        by_id = {c['clause_id']: c for c in candidates}
        ranked = [by_id[cid] for cid in order if cid in by_id]
        ranked += [c for c in candidates if c['clause_id'] not in set(order)]
        for pos, item in enumerate(ranked, start=1):
            item['rerank'] = pos
        candidates = ranked
    return candidates[:k]


def stats() -> Dict:
    info = index.stats()
    emb = embed.status()
    info.update({'vectors': emb['vectors'], 'embed_model': emb['model'],
                 'embed_ready': emb['loaded'] and emb['vectors'] > 0,
                 'rerank': RERANK_ENV != 'off'})
    return info
