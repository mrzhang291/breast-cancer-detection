# -*- coding: utf-8 -*-
"""把后台数据库的实时运营数据整理成 Coze 可用的上下文。"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func

from models import ErrorLog, Model, PredictionRecord, User, db

BENIGN = {"良性", "Benign", "benign", "BENIGN", "B"}
MALIGNANT = {"恶性", "Malignant", "malignant", "MALIGNANT", "M"}


def _label(value: Any) -> str:
    if value in BENIGN:
        return "良性"
    if value in MALIGNANT:
        return "恶性"
    return str(value or "未知")



def _agent_db_stats() -> Dict[str, Any]:
    """读取用户端 agent.db 里的会话数据（只读，库不存在时返回空）。"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agent.db')
    if not os.path.exists(path):
        return {}
    try:
        conn = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True)
        conn.row_factory = sqlite3.Row
        today = datetime.now().strftime('%Y-%m-%d')
        week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        row = {
            'sessions_total': conn.execute('SELECT COUNT(*) FROM agent_sessions').fetchone()[0],
            'sessions_7d': conn.execute(
                'SELECT COUNT(*) FROM agent_sessions WHERE created_at >= ?', (week,)).fetchone()[0],
            'messages_total': conn.execute('SELECT COUNT(*) FROM agent_messages').fetchone()[0],
            'messages_today': conn.execute(
                'SELECT COUNT(*) FROM agent_messages WHERE created_at >= ?', (today,)).fetchone()[0],
            'active_sessions_7d': conn.execute(
                'SELECT COUNT(DISTINCT session_id) FROM agent_messages WHERE created_at >= ?',
                (week,)).fetchone()[0],
        }
        avg = conn.execute(
            'SELECT AVG(c) FROM (SELECT COUNT(*) AS c FROM agent_messages GROUP BY session_id)'
        ).fetchone()[0]
        row['avg_messages_per_session'] = round(float(avg or 0), 1)
        last = conn.execute('SELECT MAX(created_at) FROM agent_messages').fetchone()[0]
        row['last_message_at'] = last or '-'
        conn.close()
        return row
    except Exception:  # noqa: BLE001
        return {}


def snapshot() -> Dict[str, Any]:
    rows = (
        db.session.query(PredictionRecord.prediction_result, func.count(PredictionRecord.id))
        .group_by(PredictionRecord.prediction_result)
        .all()
    )
    benign = malignant = other = 0
    for value, count in rows:
        label = _label(value)
        if label == "良性":
            benign += count
        elif label == "恶性":
            malignant += count
        else:
            other += count
    total = benign + malignant + other

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = PredictionRecord.query.filter(PredictionRecord.created_at >= today).count()
    avg_conf = db.session.query(func.avg(PredictionRecord.confidence)).scalar() or 0
    active_model = Model.query.filter_by(is_active=True).order_by(Model.uploaded_at.desc()).first()

    recent = PredictionRecord.query.order_by(PredictionRecord.created_at.desc()).limit(6).all()
    recent_items = [{
        "id": r.id,
        "username": r.user.username if r.user else str(r.user_id),
        "result": _label(r.prediction_result),
        "confidence": round(float(r.confidence or 0) * 100, 2),
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "-",
    } for r in recent]

    role_rows = (
        db.session.query(User.role_id, func.count(User.id))
        .group_by(User.role_id)
        .all()
    )
    week_ago = datetime.now() - timedelta(days=7)
    active_users_today = (
        db.session.query(func.count(func.distinct(PredictionRecord.user_id)))
        .filter(PredictionRecord.created_at >= today).scalar() or 0
    )
    active_users_7d = (
        db.session.query(func.count(func.distinct(PredictionRecord.user_id)))
        .filter(PredictionRecord.created_at >= week_ago).scalar() or 0
    )
    predictions_7d = PredictionRecord.query.filter(
        PredictionRecord.created_at >= week_ago).count()
    new_users_today = User.query.filter(User.created_at >= today).count()
    new_users_7d = User.query.filter(User.created_at >= week_ago).count()

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "users_total": User.query.count(),
        "users_active": User.query.filter_by(is_active=True).count(),
        "role_counts": {str(role): count for role, count in role_rows},
        "predictions_total": total,
        "predictions_today": today_count,
        "benign": benign,
        "malignant": malignant,
        "avg_confidence": round(float(avg_conf) * 100, 2),
        "malignant_ratio": round(malignant / total * 100, 1) if total else 0,
        "active_model": (f"{active_model.name} {active_model.version}" if active_model else "未配置"),
        "errors_24h": ErrorLog.query.filter(
            ErrorLog.created_at >= datetime.now() - timedelta(hours=24)).count(),
        "recent_predictions": recent_items,
        "active_users_today": int(active_users_today),
        "active_users_7d": int(active_users_7d),
        "predictions_7d": int(predictions_7d),
        "new_users_today": int(new_users_today),
        "new_users_7d": int(new_users_7d),
        "avg_predictions_per_active_user_7d": round(
            predictions_7d / active_users_7d, 2) if active_users_7d else 0,
        "assistant": _agent_db_stats(),
    }


def prompt_context() -> str:
    data = snapshot()
    lines = [
        "【本系统后台数据库实时快照】",
        f"生成时间：{data['generated_at']}",
        f"用户：总数 {data['users_total']}，启用 {data['users_active']}，角色分布 {data['role_counts']}",
        f"预测：累计 {data['predictions_total']} 条，今日新增 {data['predictions_today']} 条；"
        f"恶性 {data['malignant']} 条，良性 {data['benign']} 条，恶性占比 {data['malignant_ratio']}%；"
        f"平均置信度 {data['avg_confidence']}%",
        f"当前模型：{data['active_model']}；近 24 小时错误日志：{data['errors_24h']} 条",
        f"用户活跃度：今日活跃用户（有预测）{data['active_users_today']} 人，"
        f"近 7 天活跃 {data['active_users_7d']} 人；今日新增用户 {data['new_users_today']}，"
        f"近 7 天新增 {data['new_users_7d']}；近 7 天预测 {data['predictions_7d']} 条，"
        f"人均 {data['avg_predictions_per_active_user_7d']} 条",
        f"AI 助手会话：累计 {data['assistant'].get('sessions_total', 0)} 个会话、"
        f"{data['assistant'].get('messages_total', 0)} 条消息；近 7 天新增 "
        f"{data['assistant'].get('sessions_7d', 0)} 个会话、活跃会话 "
        f"{data['assistant'].get('active_sessions_7d', 0)} 个；今日消息 "
        f"{data['assistant'].get('messages_today', 0)} 条；平均每会话 "
        f"{data['assistant'].get('avg_messages_per_session', 0)} 条；"
        f"最近消息时间 {data['assistant'].get('last_message_at', '-')}",
        "最近预测记录：",
    ]
    for item in data["recent_predictions"]:
        lines.append(
            f"- #{item['id']} 用户 {item['username']}，结果 {item['result']}，"
            f"置信度 {item['confidence']}%，时间 {item['created_at']}"
        )
    if not data["recent_predictions"]:
        lines.append("- 暂无预测记录")
    lines += [
        "",
        "回答要求：只能依据以上快照和本系统数据回答；快照没有的信息不要编造；"
        "用中文简洁回答，必要时用列表；不要声称执行了写操作。",
    ]
    return "\n".join(lines)
