from flask import Blueprint, request, jsonify, send_file
from models import db, PredictionRecord, User, Model, OperationLog
from auth import requires_permission
from datetime import datetime, timedelta
import pandas as pd
import io
from fpdf import FPDF
import json
from sqlalchemy import or_

statistics_api = Blueprint('statistics_api', __name__)

# 预测结果转换映射
RESULT_MAP = {
    '良性': '良性',
    '恶性': '恶性',
    'Benign': '良性',
    'Malignant': '恶性',
    'benign': '良性',
    'malignant': '恶性',
    'BENIGN': '良性',
    'MALIGNANT': '恶性'
}

@statistics_api.route('/api/statistics/prediction_count', methods=['GET'])
@requires_permission('statistics_view')
def get_prediction_count():
    total = PredictionRecord.query.count()
    benign = PredictionRecord.query.filter(
        or_(
            PredictionRecord.prediction_result == '良性',
            PredictionRecord.prediction_result == 'Benign',
            PredictionRecord.prediction_result == 'benign',
            PredictionRecord.prediction_result == 'BENIGN'
        )
    ).count()
    malignant = PredictionRecord.query.filter(
        or_(
            PredictionRecord.prediction_result == '恶性',
            PredictionRecord.prediction_result == 'Malignant',
            PredictionRecord.prediction_result == 'malignant',
            PredictionRecord.prediction_result == 'MALIGNANT'
        )
    ).count()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'benign': benign,
            'malignant': malignant,
            'benign_ratio': benign / total if total > 0 else 0,
            'malignant_ratio': malignant / total if total > 0 else 0
        }
    }), 200

@statistics_api.route('/api/statistics/trend', methods=['GET'])
@requires_permission('statistics_view')
def get_prediction_trend():
    period = request.args.get('period', 'week')
    
    now = datetime.now()
    if period == 'day':
        intervals = 24
        delta = timedelta(hours=1)
        format_str = '%H:00'
    elif period == 'week':
        intervals = 7
        delta = timedelta(days=1)
        format_str = '%m-%d'
    elif period == 'month':
        intervals = 30
        delta = timedelta(days=1)
        format_str = '%m-%d'
    elif period == 'year':
        intervals = 12
        delta = timedelta(days=30)
        format_str = '%Y-%m'
    else:
        return jsonify({'code': 400, 'message': '无效的时间周期', 'data': {}}), 400
    
    start_time = now - delta * intervals
    data = []
    
    for i in range(intervals):
        interval_start = start_time + delta * i
        interval_end = interval_start + delta
        
        count = PredictionRecord.query.filter(
            PredictionRecord.created_at >= interval_start,
            PredictionRecord.created_at < interval_end
        ).count()
        
        benign_count = PredictionRecord.query.filter(
            PredictionRecord.prediction_result == '良性',
            PredictionRecord.created_at >= interval_start,
            PredictionRecord.created_at < interval_end
        ).count()
        
        malignant_count = PredictionRecord.query.filter(
            PredictionRecord.prediction_result == '恶性',
            PredictionRecord.created_at >= interval_start,
            PredictionRecord.created_at < interval_end
        ).count()
        
        data.append({
            'time': interval_start.strftime(format_str),
            'total': count,
            'benign': benign_count,
            'malignant': malignant_count
        })
    
    return jsonify({'code': 200, 'message': 'success', 'data': data}), 200

@statistics_api.route('/api/statistics/user_activity', methods=['GET'])
@requires_permission('statistics_view')
def get_user_activity():
    days = request.args.get('days', 30, type=int)
    
    start_time = datetime.now() - timedelta(days=days)
    
    users = User.query.all()
    activity_data = []
    
    for user in users:
        record_count = PredictionRecord.query.filter(
            PredictionRecord.user_id == user.id,
            PredictionRecord.created_at >= start_time
        ).count()
        
        if record_count > 0:
            activity_data.append({
                'user_id': user.id,
                'username': user.username,
                'role': user.role.name,
                'record_count': record_count
            })
    
    activity_data.sort(key=lambda x: x['record_count'], reverse=True)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': activity_data
    }), 200

@statistics_api.route('/api/statistics/model_performance', methods=['GET'])
@requires_permission('statistics_view')
def get_model_performance():
    models = Model.query.all()
    
    performance_data = []
    for model in models:
        performance_data.append({
            'model_id': model.id,
            'name': model.name,
            'version': model.version,
            'accuracy': model.accuracy,
            'recall': model.recall,
            'f1_score': model.f1_score,
            'is_active': model.is_active,
            'uploaded_at': model.uploaded_at.isoformat() if model.uploaded_at else None
        })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': performance_data
    }), 200

@statistics_api.route('/api/statistics/report', methods=['GET'])
@requires_permission('statistics_export')
def generate_report():
    format_type = request.args.get('format', 'pdf')
    
    total_count = PredictionRecord.query.count()
    benign_count = PredictionRecord.query.filter(
        or_(
            PredictionRecord.prediction_result == '良性',
            PredictionRecord.prediction_result == 'Benign',
            PredictionRecord.prediction_result == 'benign',
            PredictionRecord.prediction_result == 'BENIGN'
        )
    ).count()
    malignant_count = PredictionRecord.query.filter(
        or_(
            PredictionRecord.prediction_result == '恶性',
            PredictionRecord.prediction_result == 'Malignant',
            PredictionRecord.prediction_result == 'malignant',
            PredictionRecord.prediction_result == 'MALIGNANT'
        )
    ).count()
    
    active_users = User.query.filter_by(is_active=True).count()
    active_model = Model.query.filter_by(is_active=True).first()
    
    report_data = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_predictions': total_count,
        'benign_count': benign_count,
        'malignant_count': malignant_count,
        'benign_ratio': round(benign_count / total_count * 100, 2) if total_count > 0 else 0,
        'malignant_ratio': round(malignant_count / total_count * 100, 2) if total_count > 0 else 0,
        'active_users': active_users,
        'active_model': active_model.name if active_model else '无',
        'active_model_version': active_model.version if active_model else ''
    }
    
    if format_type == 'pdf':
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, '乳腺癌检测系统统计报表', 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.ln(10)
        pdf.cell(0, 10, f'生成时间: {report_data["generated_at"]}', 0, 1)
        pdf.ln(5)
        pdf.cell(0, 10, '一、预测统计', 0, 1)
        pdf.cell(0, 8, f'  总预测次数: {report_data["total_predictions"]}', 0, 1)
        pdf.cell(0, 8, f'  良性预测: {report_data["benign_count"]} ({report_data["benign_ratio"]}%)', 0, 1)
        pdf.cell(0, 8, f'  恶性预测: {report_data["malignant_count"]} ({report_data["malignant_ratio"]}%)', 0, 1)
        pdf.ln(5)
        pdf.cell(0, 10, '二、系统信息', 0, 1)
        pdf.cell(0, 8, f'  活跃用户数: {report_data["active_users"]}', 0, 1)
        pdf.cell(0, 8, f'  当前模型: {report_data["active_model"]} v{report_data["active_model_version"]}', 0, 1)
        
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        
        return send_file(output, download_name='statistics_report.pdf', mimetype='application/pdf')
    else:
        return jsonify({'code': 200, 'message': 'success', 'data': report_data}), 200

@statistics_api.route('/api/statistics/dashboard', methods=['GET'])
@requires_permission('statistics_view')
def get_dashboard_data():
    total_predictions = PredictionRecord.query.count()
    benign_count = PredictionRecord.query.filter(
        or_(
            PredictionRecord.prediction_result == '良性',
            PredictionRecord.prediction_result == 'Benign',
            PredictionRecord.prediction_result == 'benign',
            PredictionRecord.prediction_result == 'BENIGN'
        )
    ).count()
    malignant_count = PredictionRecord.query.filter(
        or_(
            PredictionRecord.prediction_result == '恶性',
            PredictionRecord.prediction_result == 'Malignant',
            PredictionRecord.prediction_result == 'malignant',
            PredictionRecord.prediction_result == 'MALIGNANT'
        )
    ).count()
    active_users = User.query.filter_by(is_active=True).count()
    active_model = Model.query.filter_by(is_active=True).first()
    
    today_predictions = PredictionRecord.query.filter(
        PredictionRecord.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    
    avg_confidence = db.session.query(db.func.avg(PredictionRecord.confidence)).scalar()
    
    data = {
        'total_predictions': total_predictions,
        'benign_count': benign_count,
        'malignant_count': malignant_count,
        'active_users': active_users,
        'today_predictions': today_predictions,
        'avg_confidence': round(avg_confidence * 100, 2) if avg_confidence else 0,
        'active_model': {
            'name': active_model.name,
            'version': active_model.version,
            'accuracy': active_model.accuracy
        } if active_model else None,
        'generated_at': datetime.now().isoformat()
    }
    
    return jsonify({'code': 200, 'message': 'success', 'data': data}), 200