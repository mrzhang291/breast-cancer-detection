from flask import Blueprint, request, jsonify
from models import db, OperationLog, LoginLog, ErrorLog, SystemConfig
from auth import requires_permission
from datetime import datetime, timedelta

log_api = Blueprint('log_api', __name__)

@log_api.route('/api/logs/operations', methods=['GET'])
@requires_permission('log_view')
def get_operation_logs():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_id = request.args.get('user_id', type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    query = OperationLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_time:
        query = query.filter(OperationLog.created_at >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(OperationLog.created_at <= datetime.fromisoformat(end_time))
    
    pagination = query.order_by(OperationLog.created_at.desc()).paginate(page=page, per_page=page_size)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@log_api.route('/api/logs/logins', methods=['GET'])
@requires_permission('log_view')
def get_login_logs():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_id = request.args.get('user_id', type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    status = request.args.get('status')
    
    query = LoginLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_time:
        query = query.filter(LoginLog.login_time >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(LoginLog.login_time <= datetime.fromisoformat(end_time))
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(LoginLog.login_time.desc()).paginate(page=page, per_page=page_size)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@log_api.route('/api/logs/errors', methods=['GET'])
@requires_permission('log_view')
def get_error_logs():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    error_type = request.args.get('error_type')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    query = ErrorLog.query
    
    if error_type:
        query = query.filter(ErrorLog.error_type.like(f'%{error_type}%'))
    if start_time:
        query = query.filter(ErrorLog.created_at >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(ErrorLog.created_at <= datetime.fromisoformat(end_time))
    
    pagination = query.order_by(ErrorLog.created_at.desc()).paginate(page=page, per_page=page_size)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@log_api.route('/api/logs/errors', methods=['POST'])
def add_error_log():
    data = request.get_json()
    
    if not data or 'error_type' not in data or 'error_message' not in data:
        return jsonify({'code': 400, 'message': '缺少必要参数', 'data': {}}), 400
    
    error_log = ErrorLog(
        error_type=data['error_type'],
        error_message=data['error_message'],
        traceback=data.get('traceback'),
        created_at=datetime.now()
    )
    
    db.session.add(error_log)
    db.session.commit()
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@log_api.route('/api/logs/cleanup', methods=['POST'])
@requires_permission('log_edit')
def cleanup_logs():
    data = request.get_json()
    days = data.get('days', 30)
    
    cutoff_time = datetime.now() - timedelta(days=days)
    
    OperationLog.query.filter(OperationLog.created_at < cutoff_time).delete()
    LoginLog.query.filter(LoginLog.login_time < cutoff_time).delete()
    ErrorLog.query.filter(ErrorLog.created_at < cutoff_time).delete()
    
    db.session.commit()
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@log_api.route('/api/logs/level', methods=['GET'])
@requires_permission('log_view')
def get_log_level():
    config = SystemConfig.query.filter_by(key='log_level').first()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {'log_level': config.value if config else 'INFO'}
    }), 200

@log_api.route('/api/logs/level', methods=['PUT'])
@requires_permission('log_edit')
def set_log_level():
    data = request.get_json()
    if not data or 'log_level' not in data:
        return jsonify({'code': 400, 'message': '缺少日志级别参数', 'data': {}}), 400
    
    level = data['log_level'].upper()
    if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        return jsonify({'code': 400, 'message': '无效的日志级别', 'data': {}}), 400
    
    config = SystemConfig.query.filter_by(key='log_level').first()
    if config:
        config.value = level
    else:
        config = SystemConfig(key='log_level', value=level)
        db.session.add(config)
    
    db.session.commit()
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200