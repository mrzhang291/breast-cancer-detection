"""agent.db —— 运行轨迹、语料索引、语义缓存、用户反馈。

刻意与 admin.db 分开：agent 层可以随时清空重建，不影响业务数据。
"""
import json
import os
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'agent.db')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    role_id INTEGER,
    question TEXT,
    intent TEXT,
    status TEXT,
    answer_md TEXT,
    citations_json TEXT,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS agent_steps (
    run_id TEXT,
    seq INTEGER,
    node TEXT,
    tool TEXT,
    args_json TEXT,
    result_digest TEXT,
    verdict TEXT,
    latency_ms INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (run_id, seq)
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    clause_id TEXT PRIMARY KEY,
    doc_id TEXT,
    source TEXT,
    version TEXT,
    section TEXT,
    text TEXT,
    meta_json TEXT
);

CREATE TABLE IF NOT EXISTS answer_cache (
    cache_key TEXT PRIMARY KEY,
    question TEXT,
    answer_md TEXT,
    citations_json TEXT,
    created_at REAL,
    hits INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_feedback (
    run_id TEXT,
    user_id TEXT,
    useful INTEGER,
    note TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS graph_checkpoints (
    run_id TEXT PRIMARY KEY,
    seq INTEGER,
    node TEXT,
    next_node TEXT,
    state_json TEXT,
    pending_json TEXT,
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_runs_user ON agent_runs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_steps_run ON agent_steps(run_id, seq);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.text_factory = str
    return conn


def init_schema() -> None:
    conn = connect()
    try:
        conn.executescript(_SCHEMA)
        # 中文全文检索必须用 trigram，unicode61 对中文几乎不分词
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5("
                "text, clause_id UNINDEXED, tokenize='trigram')"
            )
        except sqlite3.OperationalError:
            # 老版本 SQLite 不支持 trigram，退化为 unicode61
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5("
                "text, clause_id UNINDEXED)"
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- runs

def create_run(ctx) -> str:
    run_id = ctx.run_id or uuid.uuid4().hex[:16]
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO agent_runs (id, user_id, role_id, question, intent, status)"
            " VALUES (?,?,?,?,?,?)",
            (run_id, str(ctx.user_id), int(ctx.role_id), ctx.question, '', 'running'),
        )
        conn.commit()
    finally:
        conn.close()
    return run_id


def update_run(run_id: str, **fields) -> None:
    if not fields:
        return
    allowed = {'intent', 'status', 'answer_md', 'citations_json', 'model',
               'tokens_in', 'tokens_out', 'latency_ms'}
    pairs = [(k, v) for k, v in fields.items() if k in allowed]
    if not pairs:
        return
    sql = 'UPDATE agent_runs SET ' + ', '.join('%s = ?' % k for k, _ in pairs) + ' WHERE id = ?'
    conn = connect()
    try:
        conn.execute(sql, [v for _, v in pairs] + [run_id])
        conn.commit()
    finally:
        conn.close()


def add_step(run_id: str, seq: int, node: str, tool: str = '', args: Any = None,
             result_digest: str = '', verdict: str = '', latency_ms: int = 0) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO agent_steps"
            " (run_id, seq, node, tool, args_json, result_digest, verdict, latency_ms)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (run_id, seq, node, tool,
             json.dumps(args, ensure_ascii=False)[:2000] if args is not None else '',
             result_digest, verdict, latency_ms),
        )
        conn.commit()
    finally:
        conn.close()


def get_run(run_id: str) -> Optional[Dict]:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        run = dict(row)
        run['steps'] = [dict(r) for r in conn.execute(
            "SELECT * FROM agent_steps WHERE run_id = ? ORDER BY seq", (run_id,))]
        return run
    finally:
        conn.close()


def list_runs(user_id: Any, limit: int = 20) -> List[Dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, question, intent, status, latency_ms, created_at"
            " FROM agent_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (str(user_id), limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------- cache

def cache_get(key: str, ttl: int = 3600) -> Optional[Dict]:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM answer_cache WHERE cache_key = ?", (key,)).fetchone()
        if not row:
            return None
        if time.time() - float(row['created_at']) > ttl:
            conn.execute("DELETE FROM answer_cache WHERE cache_key = ?", (key,))
            conn.commit()
            return None
        conn.execute("UPDATE answer_cache SET hits = hits + 1 WHERE cache_key = ?", (key,))
        conn.commit()
        return {'answer_md': row['answer_md'],
                'citations': json.loads(row['citations_json'] or '[]')}
    finally:
        conn.close()


def cache_put(key: str, question: str, answer_md: str, citations: List[str]) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO answer_cache"
            " (cache_key, question, answer_md, citations_json, created_at)"
            " VALUES (?,?,?,?,?)",
            (key, question, answer_md, json.dumps(citations, ensure_ascii=False), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def add_feedback(run_id: str, user_id: Any, useful: int, note: str = '') -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO agent_feedback (run_id, user_id, useful, note) VALUES (?,?,?,?)",
            (run_id, str(user_id), int(useful), note),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- 检查点

def save_checkpoint(run_id: str, seq: int, node: str, next_node: Optional[str],
                    state: Dict, pending: Optional[Dict] = None) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO graph_checkpoints"
            " (run_id, seq, node, next_node, state_json, pending_json, updated_at)"
            " VALUES (?,?,?,?,?,?, datetime('now','localtime'))",
            (run_id, seq, node, next_node or '',
             json.dumps(state, ensure_ascii=False, default=str),
             json.dumps(pending, ensure_ascii=False) if pending else ''),
        )
        conn.commit()
    finally:
        conn.close()


def load_checkpoint(run_id: str) -> Optional[Dict]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM graph_checkpoints WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return {
            'run_id': row['run_id'],
            'seq': row['seq'],
            'node': row['node'],
            'next_node': row['next_node'],
            'state': json.loads(row['state_json'] or '{}'),
            'pending': json.loads(row['pending_json']) if row['pending_json'] else None,
            'updated_at': row['updated_at'],
        }
    finally:
        conn.close()
