from flask import Blueprint, request, jsonify
from models import db, Role, Permission, role_permissions, OperationLog
from auth import requires_permission, get_jwt_identity
from datetime import datetime

permission_api = Blueprint('permission_api', __name__)

@permission_api.route('/api/roles', methods=['POST'])
@requires_permission('role_create')
def create_role():
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'code': 400, 'message': '缺少角色名称', 'data': {}}), 400
    
    if Role.query.filter_by(name=data['name']).first():
        return jsonify({'code': 400, 'message': '角色名称已存在', 'data': {}}), 400
    
    role = Role(
        name=data['name'],
        description=data.get('description')
    )
    
    db.session.add(role)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'创建角色: {role.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': role.to_dict()}), 200

@permission_api.route('/api/roles', methods=['GET'])
@requires_permission('role_view')
def get_roles():
    roles = Role.query.all()
    
    roles_with_permissions = []
    for role in roles:
        role_dict = role.to_dict()
        permissions = Permission.query.join(role_permissions).filter(
            role_permissions.c.role_id == role.id
        ).all()
        role_dict['permissions'] = [p.to_dict() for p in permissions]
        roles_with_permissions.append(role_dict)
    
    return jsonify({'code': 200, 'message': 'success', 'data': roles_with_permissions}), 200

@permission_api.route('/api/roles/<int:role_id>', methods=['GET'])
@requires_permission('role_view')
def get_role(role_id):
    role = Role.query.get(role_id)
    if not role:
        return jsonify({'code': 404, 'message': '角色不存在', 'data': {}}), 404
    
    role_dict = role.to_dict()
    permissions = Permission.query.join(role_permissions).filter(
        role_permissions.c.role_id == role.id
    ).all()
    role_dict['permissions'] = [p.to_dict() for p in permissions]
    
    return jsonify({'code': 200, 'message': 'success', 'data': role_dict}), 200

@permission_api.route('/api/roles/<int:role_id>', methods=['PUT'])
@requires_permission('role_edit')
def update_role(role_id):
    role = Role.query.get(role_id)
    if not role:
        return jsonify({'code': 404, 'message': '角色不存在', 'data': {}}), 404
    
    data = request.get_json()
    
    if 'name' in data and data['name'] != role.name:
        if Role.query.filter_by(name=data['name']).first():
            return jsonify({'code': 400, 'message': '角色名称已存在', 'data': {}}), 400
        role.name = data['name']
    
    if 'description' in data:
        role.description = data['description']
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新角色: {role.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': role.to_dict()}), 200

@permission_api.route('/api/roles/<int:role_id>', methods=['DELETE'])
@requires_permission('role_delete')
def delete_role(role_id):
    role = Role.query.get(role_id)
    if not role:
        return jsonify({'code': 404, 'message': '角色不存在', 'data': {}}), 404
    
    if role.users:
        return jsonify({'code': 400, 'message': '该角色下存在用户，无法删除', 'data': {}}), 400
    
    db.session.delete(role)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除角色: {role.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@permission_api.route('/api/permissions', methods=['GET'])
@requires_permission('permission_view')
def get_permissions():
    permissions = Permission.query.all()
    return jsonify({'code': 200, 'message': 'success', 'data': [p.to_dict() for p in permissions]}), 200

@permission_api.route('/api/permissions', methods=['POST'])
@requires_permission('permission_create')
def create_permission():
    data = request.get_json()
    
    if not data or 'name' not in data or 'code' not in data:
        return jsonify({'code': 400, 'message': '缺少权限名称或代码', 'data': {}}), 400
    
    if Permission.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '权限代码已存在', 'data': {}}), 400
    
    permission = Permission(
        name=data['name'],
        code=data['code'],
        description=data.get('description')
    )
    
    db.session.add(permission)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'创建权限: {permission.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': permission.to_dict()}), 200

@permission_api.route('/api/permissions/<int:permission_id>', methods=['PUT'])
@requires_permission('permission_edit')
def update_permission(permission_id):
    permission = Permission.query.get(permission_id)
    if not permission:
        return jsonify({'code': 404, 'message': '权限不存在', 'data': {}}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        permission.name = data['name']
    if 'code' in data and data['code'] != permission.code:
        if Permission.query.filter_by(code=data['code']).first():
            return jsonify({'code': 400, 'message': '权限代码已存在', 'data': {}}), 400
        permission.code = data['code']
    if 'description' in data:
        permission.description = data['description']
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新权限: {permission.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': permission.to_dict()}), 200

@permission_api.route('/api/permissions/<int:permission_id>', methods=['DELETE'])
@requires_permission('permission_delete')
def delete_permission(permission_id):
    permission = Permission.query.get(permission_id)
    if not permission:
        return jsonify({'code': 404, 'message': '权限不存在', 'data': {}}), 404
    
    db.session.delete(permission)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除权限: {permission.name}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@permission_api.route('/api/roles/<int:role_id>/permissions', methods=['PUT'])
@requires_permission('role_edit')
def assign_permissions(role_id):
    role = Role.query.get(role_id)
    if not role:
        return jsonify({'code': 404, 'message': '角色不存在', 'data': {}}), 404
    
    data = request.get_json()
    if not data or 'permission_ids' not in data:
        return jsonify({'code': 400, 'message': '缺少权限ID列表', 'data': {}}), 400
    
    existing_permissions = db.session.query(role_permissions.c.permission_id).filter(
        role_permissions.c.role_id == role_id
    ).all()
    existing_ids = [p[0] for p in existing_permissions]
    
    new_permission_ids = data['permission_ids']
    
    for perm_id in existing_ids:
        if perm_id not in new_permission_ids:
            db.session.execute(
                role_permissions.delete().where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == perm_id
                )
            )
    
    for perm_id in new_permission_ids:
        if perm_id not in existing_ids:
            if not Permission.query.get(perm_id):
                return jsonify({'code': 400, 'message': f'权限ID {perm_id}不存在', 'data': {}}), 400
            db.session.execute(
                role_permissions.insert().values(role_id=role_id, permission_id=perm_id)
            )
    
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'更新角色权限: {role.name}')
    
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
