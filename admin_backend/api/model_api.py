from flask import Blueprint, request, jsonify, current_app
from models import db, Model, OperationLog
from auth import requires_permission, get_jwt_identity
import os
import pickle
from datetime import datetime
from sklearn.metrics import accuracy_score, recall_score, f1_score
import numpy as np

model_api = Blueprint('model_api', __name__)

@model_api.route('/api/models', methods=['POST'])
@requires_permission('model_upload')
def upload_model():
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '缺少文件', 'data': {}}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 400, 'message': '文件名不能为空', 'data': {}}), 400
    
    if not file.filename.endswith('.pkl'):
        return jsonify({'code': 400, 'message': '只支持.pkl格式文件', 'data': {}}), 400
    
    data = request.form
    name = data.get('name')
    version = data.get('version')
    
    if not name or not version:
        return jsonify({'code': 400, 'message': '缺少模型名称或版本', 'data': {}}), 400
    
    model_dir = os.path.join(current_app.root_path, 'models')
    os.makedirs(model_dir, exist_ok=True)
    
    filename = f"{name}_{version}.pkl"
    file_path = os.path.join(model_dir, filename)
    file.save(file_path)
    
    accuracy = None
    recall = None
    f1 = None
    
    try:
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
            if isinstance(model_data, dict) and 'model' in model_data:
                model = model_data['model']
                if hasattr(model, 'score'):
                    accuracy = float(model_data.get('accuracy', 0))
                    recall = float(model_data.get('recall', 0))
                    f1 = float(model_data.get('f1_score', 0))
            else:
                model = model_data
                if hasattr(model, 'score'):
                    accuracy = float(data.get('accuracy', 0))
                    recall = float(data.get('recall', 0))
                    f1 = float(data.get('f1_score', 0))
    except Exception as e:
        accuracy = float(data.get('accuracy', 0))
        recall = float(data.get('recall', 0))
        f1 = float(data.get('f1_score', 0))
    
    new_model = Model(
        name=name,
        version=version,
        file_path=file_path,
        accuracy=accuracy,
        recall=recall,
        f1_score=f1,
        is_active=False,
        uploaded_by=get_jwt_identity(),
        description=data.get('description')
    )
    
    db.session.add(new_model)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'上传模型: {name} v{version}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': new_model.to_dict()}), 200

@model_api.route('/api/models', methods=['GET'])
@requires_permission('model_view')
def get_models():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    name = request.args.get('name')
    is_active = request.args.get('is_active')
    
    query = Model.query
    
    if name:
        query = query.filter(Model.name.like(f'%{name}%'))
    if is_active is not None:
        query = query.filter_by(is_active=(is_active == 'true'))
    
    pagination = query.order_by(Model.uploaded_at.desc()).paginate(page=page, per_page=page_size)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [model.to_dict() for model in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@model_api.route('/api/models/<int:model_id>', methods=['GET'])
@requires_permission('model_view')
def get_model(model_id):
    model = Model.query.get(model_id)
    if not model:
        return jsonify({'code': 404, 'message': '模型不存在', 'data': {}}), 404
    
    return jsonify({'code': 200, 'message': 'success', 'data': model.to_dict()}), 200

@model_api.route('/api/models/<int:model_id>/activate', methods=['PUT'])
@requires_permission('model_activate')
def activate_model(model_id):
    model = Model.query.get(model_id)
    if not model:
        return jsonify({'code': 404, 'message': '模型不存在', 'data': {}}), 404
    
    Model.query.update({'is_active': False})
    model.is_active = True
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'激活模型: {model.name} v{model.version}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': model.to_dict()}), 200

@model_api.route('/api/models/<int:model_id>', methods=['PUT'])
@requires_permission('model_edit')
def update_model(model_id):
    model = Model.query.get(model_id)
    if not model:
        return jsonify({'code': 404, 'message': '模型不存在', 'data': {}}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        model.name = data['name']
    if 'version' in data:
        model.version = data['version']
    if 'accuracy' in data:
        model.accuracy = data['accuracy']
    if 'recall' in data:
        model.recall = data['recall']
    if 'f1_score' in data:
        model.f1_score = data['f1_score']
    if 'description' in data:
        model.description = data['description']
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新模型: {model.name} v{model.version}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': model.to_dict()}), 200

@model_api.route('/api/models/<int:model_id>', methods=['DELETE'])
@requires_permission('model_delete')
def delete_model(model_id):
    model = Model.query.get(model_id)
    if not model:
        return jsonify({'code': 404, 'message': '模型不存在', 'data': {}}), 404
    
    if model.is_active:
        return jsonify({'code': 400, 'message': '不能删除正在使用的模型', 'data': {}}), 400
    
    if os.path.exists(model.file_path):
        os.remove(model.file_path)
    
    db.session.delete(model)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除模型: {model.name} v{model.version}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@model_api.route('/api/models/rollback', methods=['POST'])
@requires_permission('model_activate')
def rollback_model():
    data = request.get_json()
    if not data or 'model_id' not in data:
        return jsonify({'code': 400, 'message': '缺少模型ID', 'data': {}}), 400
    
    target_model = Model.query.get(data['model_id'])
    if not target_model:
        return jsonify({'code': 404, 'message': '目标模型不存在', 'data': {}}), 404
    
    Model.query.update({'is_active': False})
    target_model.is_active = True
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'回滚模型到: {target_model.name} v{target_model.version}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': target_model.to_dict()}), 200

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
