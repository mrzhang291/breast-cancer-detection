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
    artifacts_json TEXT,
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

CREATE TABLE IF NOT EXISTS batch_results (
    batch_id TEXT PRIMARY KEY,
    user_id TEXT,
    payload_json TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
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

CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    content TEXT,
    meta_json TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON agent_messages(session_id, id);
"""


def _migrate(conn) -> None:
    """轻量迁移：老库缺列时补上。"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(agent_runs)")}
    if 'artifacts_json' not in cols:
        conn.execute("ALTER TABLE agent_runs ADD COLUMN artifacts_json TEXT")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.text_factory = str
    return conn


def init_schema() -> None:
    conn = connect()
    try:
        conn.executescript(_SCHEMA)
        _migrate(conn)
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
               'tokens_in', 'tokens_out', 'latency_ms', 'artifacts_json'}
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


# ------------------------------------------------------------------ 会话

def create_session(user_id: str, title: str = '新会话') -> str:
    import uuid
    sid = uuid.uuid4().hex[:16]
    conn = connect()
    try:
        conn.execute('INSERT INTO agent_sessions (id, user_id, title) VALUES (?,?,?)',
                     (sid, str(user_id), (title or '新会话')[:60]))
        conn.commit()
        return sid
    finally:
        conn.close()


def list_sessions(user_id: str, limit: int = 20):
    conn = connect()
    try:
        rows = conn.execute(
            'SELECT s.id, s.title, s.created_at, s.updated_at,'
            ' (SELECT COUNT(*) FROM agent_messages m WHERE m.session_id = s.id) AS messages'
            ' FROM agent_sessions s WHERE s.user_id = ?'
            ' ORDER BY s.updated_at DESC LIMIT ?',
            (str(user_id), int(limit))).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session(session_id: str, user_id: str = None):
    conn = connect()
    try:
        row = conn.execute('SELECT * FROM agent_sessions WHERE id = ?', (session_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if user_id is not None and str(data.get('user_id')) != str(user_id):
            return None
        return data
    finally:
        conn.close()


def delete_session(session_id: str, user_id: str) -> bool:
    conn = connect()
    try:
        row = conn.execute('SELECT user_id FROM agent_sessions WHERE id = ?',
                           (session_id,)).fetchone()
        if not row or str(row['user_id']) != str(user_id):
            return False
        conn.execute('DELETE FROM agent_messages WHERE session_id = ?', (session_id,))
        conn.execute('DELETE FROM agent_sessions WHERE id = ?', (session_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def add_message(session_id: str, role: str, content: str, meta=None) -> None:
    conn = connect()
    try:
        conn.execute('INSERT INTO agent_messages (session_id, role, content, meta_json)'
                     ' VALUES (?,?,?,?)',
                     (session_id, role, content or '',
                      json.dumps(meta or {}, ensure_ascii=False)))
        conn.execute("UPDATE agent_sessions SET updated_at = datetime('now','localtime')"
                     ' WHERE id = ?', (session_id,))
        conn.commit()
    finally:
        conn.close()


def list_messages(session_id: str, limit: int = 40):
    conn = connect()
    try:
        rows = conn.execute(
            'SELECT role, content, meta_json, created_at FROM agent_messages'
            ' WHERE session_id = ? ORDER BY id DESC LIMIT ?',
            (session_id, int(limit))).fetchall()
        items = [dict(r) for r in rows][::-1]
        for item in items:
            try:
                item['meta'] = json.loads(item.get('meta_json') or '{}')
            except ValueError:
                item['meta'] = {}
            item.pop('meta_json', None)
        return items
    finally:
        conn.close()

def update_session_title(session_id: str, title: str) -> None:
    conn = connect()
    try:
        conn.execute('UPDATE agent_sessions SET title = ? WHERE id = ?',
                     ((title or '')[:40], session_id))
        conn.commit()
    finally:
        conn.close()

def session_stats(user_id: str, days: int = 30):
    """当前用户的会话与消息统计。"""
    conn = connect()
    try:
        since = conn.execute(
            "SELECT datetime('now', 'localtime', ?)", ('-%d days' % int(days),)).fetchone()[0]
        sessions_total = conn.execute(
            'SELECT COUNT(*) FROM agent_sessions WHERE user_id = ?', (str(user_id),)).fetchone()[0]
        messages_total = conn.execute(
            'SELECT COUNT(*) FROM agent_messages m JOIN agent_sessions s'
            ' ON s.id = m.session_id WHERE s.user_id = ?', (str(user_id),)).fetchone()[0]
        active_days = conn.execute(
            'SELECT COUNT(DISTINCT date(m.created_at)) FROM agent_messages m'
            ' JOIN agent_sessions s ON s.id = m.session_id WHERE s.user_id = ?',
            (str(user_id),)).fetchone()[0]
        recent = conn.execute(
            'SELECT s.id, s.title, s.updated_at,'
            ' (SELECT COUNT(*) FROM agent_messages m WHERE m.session_id = s.id) AS messages'
            ' FROM agent_sessions s WHERE s.user_id = ?'
            ' ORDER BY s.updated_at DESC LIMIT 5', (str(user_id),)).fetchall()
        last_at = conn.execute(
            'SELECT MAX(m.created_at) FROM agent_messages m JOIN agent_sessions s'
            ' ON s.id = m.session_id WHERE s.user_id = ?', (str(user_id),)).fetchone()[0]
        return {
            'sessions_total': sessions_total,
            'messages_total': messages_total,
            'active_days': active_days,
            'last_message_at': last_at or '-',
            'recent_sessions': [dict(r) for r in recent],
        }
    finally:
        conn.close()

def save_batch(user_id: str, results) -> str:
    import uuid
    batch_id = uuid.uuid4().hex[:16]
    conn = connect()
    try:
        conn.execute('INSERT INTO batch_results (batch_id, user_id, payload_json)'
                     ' VALUES (?,?,?)',
                     (batch_id, str(user_id), json.dumps(results, ensure_ascii=False)))
        conn.commit()
        return batch_id
    finally:
        conn.close()


def get_batch(batch_id: str, user_id: str = None):
    conn = connect()
    try:
        row = conn.execute('SELECT user_id, payload_json FROM batch_results WHERE batch_id = ?',
                           (batch_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    if user_id is not None and str(row['user_id']) != str(user_id):
        return None
    try:
        return json.loads(row['payload_json'])
    except ValueError:
        return None

