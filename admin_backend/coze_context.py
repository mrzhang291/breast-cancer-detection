# -*- coding: utf-8 -*-
"""把后台数据库的实时运营数据整理成 Coze 可用的上下文。"""
from __future__ import annotations

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
