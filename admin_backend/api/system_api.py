from flask import Blueprint, request, jsonify
from models import db, SystemConfig, OperationLog
from auth import requires_permission, get_jwt_identity
from datetime import datetime

system_api = Blueprint('system_api', __name__)

@system_api.route('/api/system/configs', methods=['GET'])
@requires_permission('system_view')
def get_configs():
    key = request.args.get('key')
    
    if key:
        config = SystemConfig.query.filter_by(key=key).first()
        if not config:
            return jsonify({'code': 404, 'message': '配置不存在', 'data': {}}), 404
        return jsonify({'code': 200, 'message': 'success', 'data': config.to_dict()}), 200
    
    configs = SystemConfig.query.all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [config.to_dict() for config in configs]
    }), 200

@system_api.route('/api/system/configs', methods=['POST'])
@requires_permission('system_edit')
def create_config():
    data = request.get_json()
    
    if not data or 'key' not in data:
        return jsonify({'code': 400, 'message': '缺少配置键', 'data': {}}), 400
    
    if SystemConfig.query.filter_by(key=data['key']).first():
        return jsonify({'code': 400, 'message': '配置键已存在', 'data': {}}), 400
    
    config = SystemConfig(
        key=data['key'],
        value=data.get('value'),
        description=data.get('description')
    )
    
    db.session.add(config)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'创建系统配置: {data["key"]}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': config.to_dict()}), 200

@system_api.route('/api/system/configs/<int:config_id>', methods=['PUT'])
@requires_permission('system_edit')
def update_config(config_id):
    config = SystemConfig.query.get(config_id)
    if not config:
        return jsonify({'code': 404, 'message': '配置不存在', 'data': {}}), 404
    
    data = request.get_json()
    
    if 'value' in data:
        config.value = data['value']
    if 'description' in data:
        config.description = data['description']
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新系统配置: {config.key}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': config.to_dict()}), 200

@system_api.route('/api/system/configs/<int:config_id>', methods=['DELETE'])
@requires_permission('system_edit')
def delete_config(config_id):
    config = SystemConfig.query.get(config_id)
    if not config:
        return jsonify({'code': 404, 'message': '配置不存在', 'data': {}}), 404
    
    db.session.delete(config)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除系统配置: {config.key}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@system_api.route('/api/system/info', methods=['GET'])
@requires_permission('system_view')
def get_system_info():
    info_keys = ['system_name', 'logo', 'contact_email', 'contact_phone']
    configs = SystemConfig.query.filter(SystemConfig.key.in_(info_keys)).all()
    
    result = {}
    for config in configs:
        result[config.key] = config.value
    
    return jsonify({'code': 200, 'message': 'success', 'data': result}), 200

@system_api.route('/api/system/info', methods=['PUT'])
@requires_permission('system_edit')
def update_system_info():
    data = request.get_json()
    
    info_keys = ['system_name', 'logo', 'contact_email', 'contact_phone']
    
    for key in info_keys:
        if key in data:
            config = SystemConfig.query.filter_by(key=key).first()
            if config:
                config.value = data[key]
            else:
                config = SystemConfig(key=key, value=data[key])
                db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), '更新系统基本信息')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@system_api.route('/api/system/language', methods=['GET'])
def get_language():
    config = SystemConfig.query.filter_by(key='default_language').first()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {'language': config.value if config else 'zh'}
    }), 200

@system_api.route('/api/system/language', methods=['PUT'])
@requires_permission('system_edit')
def set_language():
    data = request.get_json()
    if not data or 'language' not in data:
        return jsonify({'code': 400, 'message': '缺少语言参数', 'data': {}}), 400
    
    if data['language'] not in ['zh', 'en']:
        return jsonify({'code': 400, 'message': '无效的语言选项', 'data': {}}), 400
    
    config = SystemConfig.query.filter_by(key='default_language').first()
    if config:
        config.value = data['language']
    else:
        config = SystemConfig(key='default_language', value=data['language'])
        db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'设置系统语言: {data["language"]}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@system_api.route('/api/system/threshold', methods=['GET'])
def get_threshold():
    config = SystemConfig.query.filter_by(key='prediction_threshold').first()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {'threshold': float(config.value) if config else 0.5}
    }), 200

@system_api.route('/api/system/threshold', methods=['PUT'])
@requires_permission('system_edit')
def set_threshold():
    data = request.get_json()
    if not data or 'threshold' not in data:
        return jsonify({'code': 400, 'message': '缺少阈值参数', 'data': {}}), 400
    
    threshold = float(data['threshold'])
    if threshold < 0 or threshold > 1:
        return jsonify({'code': 400, 'message': '阈值必须在0-1之间', 'data': {}}), 400
    
    config = SystemConfig.query.filter_by(key='prediction_threshold').first()
    if config:
        config.value = str(threshold)
    else:
        config = SystemConfig(key='prediction_threshold', value=str(threshold))
        db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'设置预测阈值: {threshold}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@system_api.route('/api/system/maintenance', methods=['GET'])
@requires_permission('system_view')
def get_maintenance_status():
    config = SystemConfig.query.filter_by(key='maintenance_mode').first()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {'maintenance_mode': config.value == 'true' if config else False}
    }), 200

@system_api.route('/api/system/maintenance', methods=['PUT'])
@requires_permission('system_edit')
def set_maintenance_status():
    data = request.get_json()
    if 'maintenance_mode' not in data:
        return jsonify({'code': 400, 'message': '缺少维护模式参数', 'data': {}}), 400
    
    config = SystemConfig.query.filter_by(key='maintenance_mode').first()
    if config:
        config.value = 'true' if data['maintenance_mode'] else 'false'
    else:
        config = SystemConfig(key='maintenance_mode', value='true' if data['maintenance_mode'] else 'false')
        db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'{"开启" if data["maintenance_mode"] else "关闭"}系统维护模式')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

def log_operation(user_id, operation):
    log = OperationLog(
        user_id=user_id,
        operation=operation,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        created_at=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
