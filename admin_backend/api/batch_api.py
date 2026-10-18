from flask import Blueprint, request, jsonify, send_file, current_app
from models import db, BatchTask, OperationLog
from auth import requires_permission, get_jwt_identity
import os
from datetime import datetime

batch_api = Blueprint('batch_api', __name__)

@batch_api.route('/api/batch_tasks', methods=['GET'])
@requires_permission('batch_view')
def get_batch_tasks():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status')
    
    query = BatchTask.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(BatchTask.created_at.desc()).paginate(page=page, per_page=page_size)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [task.to_dict() for task in pagination.items],
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@batch_api.route('/api/batch_tasks/<int:task_id>', methods=['GET'])
@requires_permission('batch_view')
def get_batch_task(task_id):
    task = BatchTask.query.get(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在', 'data': {}}), 404
    
    return jsonify({'code': 200, 'message': 'success', 'data': task.to_dict()}), 200

@batch_api.route('/api/batch_tasks/<int:task_id>', methods=['PUT'])
@requires_permission('batch_edit')
def update_batch_task(task_id):
    task = BatchTask.query.get(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在', 'data': {}}), 404
    
    data = request.get_json()
    
    if 'status' in data:
        task.status = data['status']
    if 'success_count' in data:
        task.success_count = data['success_count']
    if 'fail_count' in data:
        task.fail_count = data['fail_count']
    if 'completed_at' in data:
        task.completed_at = datetime.fromisoformat(data['completed_at'])
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新批量任务状态: {task_id} -> {task.status}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': task.to_dict()}), 200

@batch_api.route('/api/batch_tasks/<int:task_id>', methods=['DELETE'])
@requires_permission('batch_delete')
def delete_batch_task(task_id):
    task = BatchTask.query.get(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在', 'data': {}}), 404
    
    if task.status == 'processing':
        return jsonify({'code': 400, 'message': '不能删除正在处理的任务', 'data': {}}), 400
    
    if os.path.exists(task.file_path):
        os.remove(task.file_path)
    
    db.session.delete(task)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除批量任务: {task_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@batch_api.route('/api/batch_tasks/<int:task_id>/cancel', methods=['POST'])
@requires_permission('batch_edit')
def cancel_batch_task(task_id):
    task = BatchTask.query.get(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在', 'data': {}}), 404
    
    if task.status != 'processing':
        return jsonify({'code': 400, 'message': '只能取消正在处理的任务', 'data': {}}), 400
    
    task.status = 'cancelled'
    task.completed_at = datetime.now()
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'取消批量任务: {task_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': task.to_dict()}), 200

@batch_api.route('/api/batch_tasks/<int:task_id>/download', methods=['GET'])
@requires_permission('batch_view')
def download_batch_result(task_id):
    task = BatchTask.query.get(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在', 'data': {}}), 404
    
    if not os.path.exists(task.file_path):
        return jsonify({'code': 404, 'message': '结果文件不存在', 'data': {}}), 404
    
    return send_file(task.file_path, download_name=task.file_name, as_attachment=True)

@batch_api.route('/api/batch_tasks/statistics', methods=['GET'])
@requires_permission('batch_view')
def get_batch_statistics():
    total_tasks = BatchTask.query.count()
    completed_tasks = BatchTask.query.filter_by(status='completed').count()
    failed_tasks = BatchTask.query.filter_by(status='failed').count()
    
    today_tasks = BatchTask.query.filter(
        BatchTask.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    
    avg_success_rate = db.session.query(
        db.func.avg(BatchTask.success_count.cast(db.Float) / BatchTask.total_count.cast(db.Float))
    ).filter(BatchTask.total_count > 0).scalar()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'today_tasks': today_tasks,
            'avg_success_rate': round(avg_success_rate * 100, 2) if avg_success_rate else 0
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
