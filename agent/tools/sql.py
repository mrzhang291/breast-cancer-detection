"""只读 SQL 工具：让 agent 自己构造查询。

安全边界：
    - 只允许单条 SELECT
    - 表白名单
    - 强制 LIMIT
    - 只读连接（mode=ro）
"""
import json
import os
import re
import sqlite3
from typing import Dict, List, Tuple

from .. import registry

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADMIN_DB = os.path.join(ROOT, 'admin_backend', 'instance', 'admin.db')

ALLOWED_TABLES = {'prediction_records', 'users', 'models', 'ai_chat_records', 'roles'}
FORBIDDEN = re.compile(r'\b(insert|update|delete|drop|alter|attach|pragma|create|replace|vacuum)\b', re.I)
MAX_ROWS = 50

FEATURE_COLUMNS = {
    '半径': 'feature_1', '纹理': 'feature_2', '周长': 'feature_3', '面积': 'feature_4',
    'radius': 'feature_1', 'texture': 'feature_2', 'perimeter': 'feature_3', 'area': 'feature_4',
}


def _connect_ro() -> sqlite3.Connection:
    uri = 'file:%s?mode=ro' % ADMIN_DB.replace('\\', '/')
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def plan_sql(question: str) -> Tuple[str, str]:
    """把自然语言问题翻译成 SQL（离线模板；有模型时由模型生成）。"""
    text = (question or '').lower()

    # 选列：默认看预测结果分布
    feature = None
    for key, column in FEATURE_COLUMNS.items():
        if key in text:
            feature = column
            break

    label_col = 'prediction_result'

    if any(word in text for word in ('平均', '均值', 'avg')):
        if feature:
            sql = ("SELECT prediction_result, COUNT(*) AS 数量, "
                   "ROUND(AVG(json_extract(all_30_features_json, '$.%s')), 2) AS 平均值 "
                   "FROM prediction_records WHERE is_deleted = 0 AND prediction_result IN ('良性','恶性','Benign','Malignant') "
                   "GROUP BY prediction_result" % feature)
            return sql, '按预测结果分组，统计该特征的平均值'

    if any(word in text for word in ('最高', '最大', 'max')):
        if feature:
            sql = ("SELECT prediction_result, "
                   "ROUND(MAX(json_extract(all_30_features_json, '$.%s')), 2) AS 最大值 "
                   "FROM prediction_records WHERE is_deleted = 0 AND prediction_result IN ('良性','恶性','Benign','Malignant') "
                   "GROUP BY prediction_result" % feature)
            return sql, '按预测结果分组，统计该特征的最大值'

    if any(word in text for word in ('多少', '几条', '数量', 'count', '分布', '占比')):
        sql = ("SELECT %s AS 结果, COUNT(*) AS 数量 "
               "FROM prediction_records WHERE is_deleted = 0 AND prediction_result IN ('良性','恶性','Benign','Malignant') "
               "GROUP BY %s ORDER BY 数量 DESC" % (label_col, label_col))
        return sql, '按预测结果统计记录数量'

    # 兜底：最近记录概览
    sql = ("SELECT id, prediction_result AS 结果, ROUND(confidence, 4) AS 置信度, created_at "
           "FROM prediction_records WHERE is_deleted = 0 AND prediction_result IN ('良性','恶性','Benign','Malignant') ORDER BY id DESC LIMIT 5")
    return sql, '最近 5 条预测记录（未识别到具体统计意图，给出概览）'


def validate_sql(sql: str) -> str:
    text = (sql or '').strip().rstrip(';')
    if not text:
        raise ValueError('SQL 为空')
    if FORBIDDEN.search(text):
        raise ValueError('SQL 只允许 SELECT')
    if not text.lower().startswith('select'):
        raise ValueError('SQL 必须以 SELECT 开头')
    if '--' in text or ';' in text:
        raise ValueError('SQL 不允许注释或多语句')

    tables = set(re.findall(r'\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)', text, re.I))
    tables |= set(re.findall(r'\bjoin\s+([a-zA-Z_][a-zA-Z0-9_]*)', text, re.I))
    unknown = tables - ALLOWED_TABLES
    if unknown:
        raise ValueError('不允许查询这些表: %s' % ', '.join(sorted(unknown)))

    if 'limit' not in text.lower():
        text += ' LIMIT %d' % MAX_ROWS
    return text


def run_sql(sql: str) -> List[Dict]:
    conn = _connect_ro()
    try:
        cursor = conn.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@registry.tool(
    'sql_query',
    description='把数据统计类问题翻译成只读 SQL 并在预测库上执行，返回结果表',
    schema={
        'type': 'object',
        'properties': {'question': {'type': 'string'}},
        'required': ['question'],
    },
    permission='stats:read',
    timeout=10.0,
    idempotent=True,
)
def sql_query(ctx, question):
    sql, explanation = plan_sql(question)
    sql = validate_sql(sql)

    try:
        rows = run_sql(sql)
    except sqlite3.Error as exc:
        raise RuntimeError('SQL 执行失败: %s' % exc)

    payload = {
        'question': question,
        'sql': sql,
        'explanation': explanation,
        'columns': list(rows[0].keys()) if rows else [],
        'rows': rows,
        'row_count': len(rows),
    }
    fact = registry.make_fact('sql', payload, tool='sql_query',
                              run_id=ctx.run_id, ident='sql_%s' % ctx.run_id[:8])
    ctx.add_fact(fact)
    return registry.ToolResult(ok=True, data=payload, facts=[fact])
