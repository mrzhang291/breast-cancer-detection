"""检索索引。

不引入向量库：语料只有几百条，用 SQLite 倒排表 + IDF 加权就够，
而且中文用"单字 + 二元词"切分，比 FTS5 的 trigram 对两字查询更可靠。
"""
import json
import math
import os
import re
import sqlite3
from typing import Dict, List

from .. import db

CJK_RE = re.compile(r'[\u4e00-\u9fff]+')
LATIN_RE = re.compile(r'[a-zA-Z0-9_]{2,}')

# 高频虚字，单字索引里噪音太大
STOP_CHARS = set('的了是在和与我你他她它这那有就都而及或其之为以对可很更最不也都还要会能被把从到对于关于')

_STOP_TERMS = {
    '什么', '怎么', '如何', '可以', '我们', '你们', '这个', '那个', '一个', '是否',
    'the', 'and', 'for', 'with', 'this', 'that', 'you', 'are', 'how', 'what',
}


_SYNONYMS = {
    '置信度': ['校准', '概率', 'confidence'],
    '校准': ['置信度', 'isotonic'],
    '报告': ['导出', 'pdf', '产物'],
    '导出': ['下载', '报告', 'csv'],
    '证据': ['依据', '引用', '条款'],
    '依据': ['证据', '引用'],
    '凹点': ['凹陷', 'concave'],
    '批量': ['csv', 'excel', '导入'],
    '区间': ['最近', '汇总', '时间范围'],
    '权限': ['角色', '管理员', '医生'],
}


def expand_query(query: str) -> List[str]:
    """同义词扩展：把用户说法映射到文档里的术语。"""
    extra: List[str] = []
    for word, alts in _SYNONYMS.items():
        if word in (query or ''):
            extra.extend(alts)
    return extra


def tokenize(text: str) -> List[str]:
    """中文：单字 + 二元词；英文/数字：小写词。"""
    text = (text or '').lower()
    tokens: List[str] = []

    for token in LATIN_RE.findall(text):
        if token not in _STOP_TERMS:
            tokens.append(token)

    for run in CJK_RE.findall(text):
        for ch in run:
            if ch not in STOP_CHARS:
                tokens.append(ch)
        for i in range(len(run) - 1):
            bigram = run[i:i + 2]
            if bigram not in _STOP_TERMS:
                tokens.append(bigram)
    return tokens


def _conn() -> sqlite3.Connection:
    conn = db.connect()
    conn.execute('CREATE TABLE IF NOT EXISTS rag_terms ('
                 'term TEXT NOT NULL, clause_id TEXT NOT NULL, tf INTEGER NOT NULL, '
                 'PRIMARY KEY (term, clause_id))')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_terms_term ON rag_terms(term)')
    conn.commit()
    return conn


def rebuild() -> Dict:
    """重建索引：清空 -> 写入条款 -> 写倒排。"""
    from . import corpus

    db.init_schema()
    chunks = corpus.all_chunks()

    conn = _conn()
    try:
        conn.execute('DELETE FROM rag_chunks')
        conn.execute('DELETE FROM rag_terms')

        for chunk in chunks:
            conn.execute(
                'INSERT OR REPLACE INTO rag_chunks'
                ' (clause_id, doc_id, source, version, section, text, meta_json)'
                ' VALUES (?,?,?,?,?,?,?)',
                (chunk['clause_id'], chunk['doc_id'], chunk['source'],
                 chunk['version'], chunk['section'], chunk['text'],
                 json.dumps(chunk.get('meta', {}), ensure_ascii=False)),
            )
            counts: Dict[str, int] = {}
            for token in tokenize(chunk['section'] + ' ' + chunk['text']):
                counts[token] = counts.get(token, 0) + 1
            conn.executemany(
                'INSERT OR REPLACE INTO rag_terms (term, clause_id, tf) VALUES (?,?,?)',
                [(t, chunk['clause_id'], c) for t, c in counts.items()],
            )
        conn.commit()

        total = conn.execute('SELECT COUNT(*) FROM rag_chunks').fetchone()[0]
        terms = conn.execute('SELECT COUNT(*) FROM rag_terms').fetchone()[0]
        return {'chunks': total, 'terms': terms}
    finally:
        conn.close()


def stats() -> Dict:
    conn = db.connect()
    try:
        chunks = conn.execute('SELECT COUNT(*) FROM rag_chunks').fetchone()[0]
        try:
            terms = conn.execute('SELECT COUNT(*) FROM rag_terms').fetchone()[0]
        except sqlite3.OperationalError:
            terms = 0
        return {'chunks': chunks, 'terms': terms}
    finally:
        conn.close()


INSTRUCTION_WORDS = ('点击', '访问', '上传', '填写', '提交', '选择', '打开',
                     '在结果页', '在首页', '下载', '导出')


def _quality_boost(text: str, section: str) -> float:
    """教程类内容加分，纯表格/代码块减分。"""
    boost = 1.0
    body = text or ''

    pipes = sum(1 for line in body.splitlines() if line.strip().startswith('|'))
    total = max(1, len([line for line in body.splitlines() if line.strip()]))
    if pipes / total > 0.5:
        boost *= 0.72           # 以表格为主：不适合回答"怎么用"
    if body.count('```') >= 2:
        boost *= 0.8            # 以代码块为主

    hits = sum(body.count(word) for word in INSTRUCTION_WORDS)
    boost *= 1.0 + min(hits, 6) * 0.07

    if '已移除' in (section or '') or '已移除' in body[:40]:
        boost *= 0.6            # 废弃说明不该抢答
    return boost


def search(query: str, k: int = 5, prefer: str = '') -> List[Dict]:
    """IDF 加权检索 + 质量重排，返回带分值的条款。"""
    tokens = tokenize(query)
    if not tokens:
        return []

    conn = _conn()
    try:
        total = conn.execute('SELECT COUNT(*) FROM rag_chunks').fetchone()[0]
        if not total:
            return []

        uniq = list(dict.fromkeys(tokens + [t for w in expand_query(query)
                                              for t in tokenize(w)]))
        placeholders = ','.join('?' * len(uniq))
        rows = conn.execute(
            'SELECT term, clause_id, tf FROM rag_terms WHERE term IN (%s)' % placeholders,
            uniq).fetchall()
        if not rows:
            return []

        df = {}
        for term, _clause, _tf in rows:
            df[term] = df.get(term, 0) + 1

        scores = {}
        for term, clause, tf in rows:
            idf = math.log((total + 1.0) / (df[term] + 0.5))
            scores[clause] = scores.get(clause, 0.0) + idf * (1.0 + math.log(tf))
        if not scores:
            return []

        # 一次性取出候选条款的正文与章节，避免 N+1
        ids = list(scores)
        placeholders = ','.join('?' * len(ids))
        detail = {row['clause_id']: row for row in conn.execute(
            'SELECT clause_id, doc_id, source, version, section, text, meta_json'
            ' FROM rag_chunks WHERE clause_id IN (%s)' % placeholders, ids).fetchall()}

        phrase = (query or '').strip()
        token_set = set(uniq)
        doc_matched = set()
        for clause_id in ids:
            row = detail.get(clause_id)
            if not row:
                continue
            text = row['text'] or ''
            section = row['section'] or ''

            if len(phrase) >= 2 and phrase in text:
                scores[clause_id] *= 1.35
            overlap = len(token_set & set(tokenize(section)))
            if overlap:
                scores[clause_id] *= 1.0 + 0.15 * min(overlap, 3)
            scores[clause_id] *= _quality_boost(text, section)

            # 覆盖率重排：命中查询词越多越可信，避免长文档靠单个高频词上位
            covered = len(token_set & set(tokenize(text)))
            if token_set:
                scores[clause_id] *= 0.55 + 0.45 * (covered / float(len(token_set)))

            if prefer == 'howto':
                numbered = len(re.findall(r'^\s*\d+\.', text, re.M))
                actions = sum(text.count(w) for w in ('点击', '进入', '访问', '上传',
                                                      '填写', '提交', '选择', '打开'))
                scores[clause_id] *= 1.0 + min(actions, 6) * 0.06
                if numbered >= 2:
                    scores[clause_id] *= 3.0   # 成步骤的条款，才是"怎么做"的答案

            # 文档名命中：问 "SHAP 怎么用" 时优先 SHAP 那篇
            source_lower = (row['source'] or '').lower()
            if any(len(tok) >= 3 and tok in source_lower for tok in token_set):
                scores[clause_id] *= 1.45
                doc_matched.add(clause_id)

        # 问「怎么用」且问题里点了某一篇文档的名字时，就只在那篇里找答案
        if prefer == 'howto' and doc_matched:
            scores = {cid: sc for cid, sc in scores.items() if cid in doc_matched}

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        if not ranked:
            return []

        cutoff = ranked[0][1] * 0.35
        ranked = [(cid, sc) for cid, sc in ranked if sc >= cutoff][:k]

        results = []
        for clause_id, score in ranked:
            row = detail.get(clause_id)
            if not row:
                continue
            results.append({
                'clause_id': row['clause_id'],
                'doc_id': row['doc_id'],
                'source': row['source'],
                'version': row['version'],
                'section': row['section'],
                'text': row['text'],
                'meta': json.loads(row['meta_json'] or '{}'),
                'score': round(score, 4),
            })
        # 相对阈值：低于最高分 35% 的命中视为噪音
        if results:
            top = results[0]['score']
            results = [r for r in results if r['score'] >= max(top * 0.35, 1e-6)]
        return results
    finally:
        conn.close()


def get_chunk(clause_id: str) -> Dict:
    conn = db.connect()
    try:
        row = conn.execute('SELECT * FROM rag_chunks WHERE clause_id = ?', (clause_id,)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()
