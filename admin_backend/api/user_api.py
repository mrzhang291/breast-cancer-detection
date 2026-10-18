from flask import Blueprint, request, jsonify
from models import db, User, Role, OperationLog
from auth import requires_permission, get_jwt_identity
from datetime import datetime

user_api = Blueprint('user_api', __name__)

@user_api.route('/api/register', methods=['POST'])
def register_user():
    """公开的用户注册接口 - 允许普通用户注册"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'code': 400, 'message': '缺少用户名或密码', 'data': {}}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'code': 400, 'message': '用户名已存在', 'data': {}}), 400
    
    # 获取"医生用户"角色（ID=3）
    doctor_role = Role.query.filter_by(name='医生用户').first()
    if not doctor_role:
        return jsonify({'code': 500, 'message': '系统角色未初始化', 'data': {}}), 500
    
    user = User(
        username=data['username'],
        email=data.get('email'),
        role_id=doctor_role.id,
        is_active=True
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'code': 200, 'message': 'success', 'data': user.to_dict()}), 200

@user_api.route('/api/users', methods=['POST'])
def create_user():
    try:
        # 先检查请求体是否为空
        if not request.data:
            return jsonify({'code': 400, 'message': '请求体为空', 'data': {}}), 400
        
        data = request.get_json()
        
        if data is None:
            return jsonify({'code': 400, 'message': '请求体为空或格式无效', 'data': {}}), 400
        
        if not data or 'username' not in data or 'password' not in data or 'role_id' not in data:
            missing_fields = []
            if 'username' not in data:
                missing_fields.append('username')
            if 'password' not in data:
                missing_fields.append('password')
            if 'role_id' not in data:
                missing_fields.append('role_id')
            return jsonify({'code': 400, 'message': f"缺少必要参数: {', '.join(missing_fields)}", 'data': {}}), 400
        
        # 验证字段类型
        if not isinstance(data['username'], str):
            return jsonify({'code': 400, 'message': 'username字段类型错误，应为字符串', 'data': {}}), 400
        if not isinstance(data['password'], str):
            return jsonify({'code': 400, 'message': 'password字段类型错误，应为字符串', 'data': {}}), 400
        if not isinstance(data['role_id'], int):
            return jsonify({'code': 400, 'message': 'role_id字段类型错误，应为整数', 'data': {}}), 400
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'code': 400, 'message': f'用户名 {data["username"]} 已存在', 'data': {}}), 400
        
        if not Role.query.get(data['role_id']):
            return jsonify({'code': 400, 'message': '角色不存在', 'data': {}}), 400
        
        # 处理email：如果为空字符串则设为None，避免唯一约束冲突
        email = data.get('email')
        if email is not None and email.strip() == '':
            email = None
        
        user = User(
            username=data['username'],
            email=email,
            role_id=data['role_id'],
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # 只有在有认证用户时才记录操作日志
        current_user_id = get_jwt_identity()
        if current_user_id:
            log_operation(current_user_id, f'创建用户: {user.username}')
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'password': user.password_hash,
            'role_id': user.role_id,
            'role_name': user.role.name if user.role else None,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        }
        
        return jsonify({'code': 200, 'message': 'success', 'data': user_data}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'创建用户失败: {str(e)}', 'data': {}}), 500

@user_api.route('/api/users', methods=['GET'])
@requires_permission('user_view')
def get_users():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    username = request.args.get('username')
    role_id = request.args.get('role_id')
    is_active = request.args.get('is_active')
    
    query = User.query
    
    if username:
        query = query.filter(User.username.like(f'%{username}%'))
    if role_id:
        # 支持多个role_id，用逗号分隔
        role_ids = role_id.split(',')
        if len(role_ids) > 1:
            query = query.filter(User.role_id.in_([int(r) for r in role_ids]))
        else:
            query = query.filter_by(role_id=int(role_id))
    if is_active and is_active != '':
        query = query.filter_by(is_active=(is_active == '1' or is_active == 'true'))
    
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=page_size)
    
    user_list = []
    for user in pagination.items:
        user_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'password': user.password_hash,
            'role_id': user.role_id,
            'role_name': user.role.name if user.role else None,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': user_list,
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@user_api.route('/api/users/<int:user_id>', methods=['GET'])
@requires_permission('user_view')
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
    
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'password': user.password_hash,
        'role_id': user.role_id,
        'role_name': user.role.name if user.role else None,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None
    }
    
    return jsonify({'code': 200, 'message': 'success', 'data': user_data}), 200

@user_api.route('/api/users/<int:user_id>', methods=['PUT'])
@requires_permission('user_edit')
def update_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
        
        data = request.get_json()
        password_changed = False
        
        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'code': 400, 'message': '用户名已存在', 'data': {}}), 400
            user.username = data['username']
        
        if 'email' in data:
            # 处理email：如果为空字符串则设为None，避免唯一约束冲突
            email = data['email']
            if email is not None and email.strip() == '':
                email = None
            user.email = email
        if 'password' in data and data['password']:
            user.set_password(data['password'])
            # 只有当管理员修改自己的密码时才需要强制重新登录
            current_user_id = get_jwt_identity()
            password_changed = (current_user_id == user_id)
        if 'role_id' in data:
            if not Role.query.get(data['role_id']):
                return jsonify({'code': 400, 'message': '角色不存在', 'data': {}}), 400
            user.role_id = data['role_id']
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        db.session.commit()
    
        log_operation(get_jwt_identity(), f'更新用户: {user.username}')
    
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'password': user.password_hash,
            'role_id': user.role_id,
            'role_name': user.role.name if user.role else None,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        }
    
        result = {'code': 200, 'message': 'success', 'data': user_data}
        if password_changed:
            result['password_changed'] = True
            result['message'] = '密码已修改，请重新登录'
    
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'更新用户失败: {str(e)}', 'data': {}}), 500

@user_api.route('/api/users/<int:user_id>', methods=['DELETE'])
@requires_permission('user_delete')
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
        
        # 删除相关记录（级联删除）
        from models import PredictionRecord, OperationLog, LoginLog, AIChatRecord, BatchTask
        
        PredictionRecord.query.filter_by(user_id=user_id).delete()
        OperationLog.query.filter_by(user_id=user_id).delete()
        LoginLog.query.filter_by(user_id=user_id).delete()
        AIChatRecord.query.filter_by(user_id=user_id).delete()
        BatchTask.query.filter_by(user_id=user_id).delete()
        
        db.session.delete(user)
        db.session.commit()
        
        log_operation(get_jwt_identity(), f'删除用户: {user.username}')
        
        return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}', 'data': {}}), 500

@user_api.route('/api/users/<int:user_id>/status', methods=['PUT'])
@requires_permission('user_edit')
def toggle_user_status(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
    
    user.is_active = not user.is_active
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'{"启用" if user.is_active else "禁用"}用户: {user.username}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': user.to_dict()}), 200

@user_api.route('/api/users/<int:user_id>/password', methods=['PUT'])
@requires_permission('user_edit')
def reset_password(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
    
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'code': 400, 'message': '缺少密码参数', 'data': {}}), 400
    
    user.set_password(data['password'])
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'重置用户密码: {user.username}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@user_api.route('/api/users/<int:user_id>/role', methods=['PUT'])
@requires_permission('user_edit')
def update_user_role(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
    
    data = request.get_json()
    if not data or 'role_id' not in data:
        return jsonify({'code': 400, 'message': '缺少角色ID参数', 'data': {}}), 400
    
    if not Role.query.get(data['role_id']):
        return jsonify({'code': 400, 'message': '角色不存在', 'data': {}}), 400
    
    user.role_id = data['role_id']
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新用户角色: {user.username} -> {user.role.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': user.to_dict()}), 200

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