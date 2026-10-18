from flask import Blueprint, request, jsonify
from models import db, AIChatRecord, SystemConfig, OperationLog
from auth import requires_permission, get_jwt_identity
from datetime import datetime

ai_api = Blueprint('ai_api', __name__)

@ai_api.route('/api/ai/chat_records', methods=['GET'])
@requires_permission('ai_view')
def get_chat_records():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_id = request.args.get('user_id', type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    query = AIChatRecord.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_time:
        query = query.filter(AIChatRecord.created_at >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(AIChatRecord.created_at <= datetime.fromisoformat(end_time))
    
    pagination = query.order_by(AIChatRecord.created_at.desc()).paginate(page=page, per_page=page_size)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [record.to_dict() for record in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@ai_api.route('/api/ai/chat_records/<int:record_id>', methods=['GET'])
@requires_permission('ai_view')
def get_chat_record(record_id):
    record = AIChatRecord.query.get(record_id)
    if not record:
        return jsonify({'code': 404, 'message': '聊天记录不存在', 'data': {}}), 404
    
    return jsonify({'code': 200, 'message': 'success', 'data': record.to_dict()}), 200

@ai_api.route('/api/ai/chat_records/<int:record_id>', methods=['DELETE'])
@requires_permission('ai_edit')
def delete_chat_record(record_id):
    record = AIChatRecord.query.get(record_id)
    if not record:
        return jsonify({'code': 404, 'message': '聊天记录不存在', 'data': {}}), 404
    
    db.session.delete(record)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除AI聊天记录: {record_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@ai_api.route('/api/ai/chat_records/batch_delete', methods=['POST'])
@requires_permission('ai_edit')
def batch_delete_chat_records():
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({'code': 400, 'message': '缺少ID列表', 'data': {}}), 400
    
    AIChatRecord.query.filter(AIChatRecord.id.in_(data['ids'])).delete(synchronize_session=False)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'批量删除AI聊天记录: {len(data["ids"])}条')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@ai_api.route('/api/ai/faq', methods=['GET'])
@requires_permission('ai_view')
def get_faq_list():
    config = SystemConfig.query.filter_by(key='faq_list').first()
    if config:
        import json
        faq_list = json.loads(config.value)
    else:
        faq_list = []
    
    return jsonify({'code': 200, 'message': 'success', 'data': faq_list}), 200

@ai_api.route('/api/ai/faq', methods=['POST'])
@requires_permission('ai_edit')
def add_faq():
    data = request.get_json()
    
    if not data or 'question' not in data or 'answer' not in data:
        return jsonify({'code': 400, 'message': '缺少问题或答案', 'data': {}}), 400
    
    config = SystemConfig.query.filter_by(key='faq_list').first()
    if config:
        import json
        faq_list = json.loads(config.value)
    else:
        faq_list = []
    
    faq_list.append({
        'id': len(faq_list) + 1,
        'question': data['question'],
        'answer': data['answer'],
        'created_at': datetime.now().isoformat()
    })
    
    import json
    if config:
        config.value = json.dumps(faq_list)
    else:
        config = SystemConfig(key='faq_list', value=json.dumps(faq_list))
        db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), '添加FAQ')
    
    return jsonify({'code': 200, 'message': 'success', 'data': faq_list}), 200

@ai_api.route('/api/ai/faq/<int:faq_id>', methods=['PUT'])
@requires_permission('ai_edit')
def update_faq(faq_id):
    data = request.get_json()
    
    config = SystemConfig.query.filter_by(key='faq_list').first()
    if not config:
        return jsonify({'code': 404, 'message': 'FAQ列表不存在', 'data': {}}), 404
    
    import json
    faq_list = json.loads(config.value)
    
    for faq in faq_list:
        if faq['id'] == faq_id:
            if 'question' in data:
                faq['question'] = data['question']
            if 'answer' in data:
                faq['answer'] = data['answer']
            faq['updated_at'] = datetime.now().isoformat()
            break
    else:
        return jsonify({'code': 404, 'message': 'FAQ不存在', 'data': {}}), 404
    
    config.value = json.dumps(faq_list)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新FAQ: {faq_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': faq_list}), 200

@ai_api.route('/api/ai/faq/<int:faq_id>', methods=['DELETE'])
@requires_permission('ai_edit')
def delete_faq(faq_id):
    config = SystemConfig.query.filter_by(key='faq_list').first()
    if not config:
        return jsonify({'code': 404, 'message': 'FAQ列表不存在', 'data': {}}), 404
    
    import json
    faq_list = json.loads(config.value)
    
    faq_list = [faq for faq in faq_list if faq['id'] != faq_id]
    
    config.value = json.dumps(faq_list)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除FAQ: {faq_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': faq_list}), 200

@ai_api.route('/api/ai/templates', methods=['GET'])
@requires_permission('ai_view')
def get_templates():
    config = SystemConfig.query.filter_by(key='response_templates').first()
    if config:
        import json
        templates = json.loads(config.value)
    else:
        templates = []
    
    return jsonify({'code': 200, 'message': 'success', 'data': templates}), 200

@ai_api.route('/api/ai/templates', methods=['POST'])
@requires_permission('ai_edit')
def add_template():
    data = request.get_json()
    
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'code': 400, 'message': '缺少模板名称或内容', 'data': {}}), 400
    
    config = SystemConfig.query.filter_by(key='response_templates').first()
    if config:
        import json
        templates = json.loads(config.value)
    else:
        templates = []
    
    templates.append({
        'id': len(templates) + 1,
        'name': data['name'],
        'content': data['content'],
        'created_at': datetime.now().isoformat()
    })
    
    import json
    if config:
        config.value = json.dumps(templates)
    else:
        config = SystemConfig(key='response_templates', value=json.dumps(templates))
        db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'添加回复模板: {data["name"]}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': templates}), 200

@ai_api.route('/api/ai/templates/<int:template_id>', methods=['PUT'])
@requires_permission('ai_edit')
def update_template(template_id):
    data = request.get_json()
    
    config = SystemConfig.query.filter_by(key='response_templates').first()
    if not config:
        return jsonify({'code': 404, 'message': '模板列表不存在', 'data': {}}), 404
    
    import json
    templates = json.loads(config.value)
    
    for template in templates:
        if template['id'] == template_id:
            if 'name' in data:
                template['name'] = data['name']
            if 'content' in data:
                template['content'] = data['content']
            template['updated_at'] = datetime.now().isoformat()
            break
    else:
        return jsonify({'code': 404, 'message': '模板不存在', 'data': {}}), 404
    
    config.value = json.dumps(templates)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新回复模板: {template_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': templates}), 200

@ai_api.route('/api/ai/templates/<int:template_id>', methods=['DELETE'])
@requires_permission('ai_edit')
def delete_template(template_id):
    config = SystemConfig.query.filter_by(key='response_templates').first()
    if not config:
        return jsonify({'code': 404, 'message': '模板列表不存在', 'data': {}}), 404
    
    import json
    templates = json.loads(config.value)
    
    templates = [t for t in templates if t['id'] != template_id]
    
    config.value = json.dumps(templates)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除回复模板: {template_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': templates}), 200

@ai_api.route('/api/ai/sensitive_words', methods=['GET'])
@requires_permission('ai_view')
def get_sensitive_words():
    config = SystemConfig.query.filter_by(key='sensitive_words').first()
    if config:
        import json
        words = json.loads(config.value)
    else:
        words = []
    
    return jsonify({'code': 200, 'message': 'success', 'data': words}), 200

@ai_api.route('/api/ai/sensitive_words', methods=['PUT'])
@requires_permission('ai_edit')
def update_sensitive_words():
    data = request.get_json()
    if not data or 'words' not in data:
        return jsonify({'code': 400, 'message': '缺少敏感词列表', 'data': {}}), 400
    
    import json
    config = SystemConfig.query.filter_by(key='sensitive_words').first()
    if config:
        config.value = json.dumps(data['words'])
    else:
        config = SystemConfig(key='sensitive_words', value=json.dumps(data['words']))
        db.session.add(config)
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), '更新敏感词列表')
    
    return jsonify({'code': 200, 'message': 'success', 'data': data['words']}), 200

@ai_api.route('/api/ai/statistics', methods=['GET'])
@requires_permission('ai_view')
def get_ai_statistics():
    total_records = AIChatRecord.query.count()
    
    today_records = AIChatRecord.query.filter(
        AIChatRecord.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    
    unique_users = db.session.query(AIChatRecord.user_id).distinct().count()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total_questions': total_records,
            'today_questions': today_records,
            'unique_users': unique_users
        }
    }), 200

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
