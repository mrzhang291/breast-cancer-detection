from functools import wraps
from flask import request, jsonify
import jwt as pyjwt
import time
from datetime import timedelta
from models import User, Role, Permission, role_permissions
from sqlalchemy import or_

# 自定义token获取函数，支持从多个来源获取token
def get_token_from_request():
    from flask import request
    
    # 首先尝试从Authorization header获取token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # 如果没有，尝试从Cookie获取token
    token = request.cookies.get('access_token')
    if token:
        return token
    
    # 如果没有，尝试从URL参数获取token
    token = request.args.get('token')
    if token:
        return token
    
    return None

# 兼容 Flask-JWT-Extended 的 get_jwt_identity 函数
def get_jwt_identity():
    token = get_token_from_request()
    if not token:
        return None
    
    try:
        from flask import current_app
        secret = current_app.config['JWT_SECRET_KEY']
        decoded_token = pyjwt.decode(token, secret, algorithms=['HS256'])
        return decoded_token.get('sub')
    except Exception:
        return None

def login(username, password):
    from flask import current_app
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password) and user.is_active:
        secret = current_app.config['JWT_SECRET_KEY']
        
        # 创建access token
        access_payload = {
            'sub': str(user.id),
            'iat': int(time.time()),
            'exp': int(time.time()) + timedelta(hours=1).total_seconds(),
            'fresh': False,
            'type': 'access'
        }
        access_token = pyjwt.encode(access_payload, secret, algorithm='HS256')
        
        # 创建refresh token
        refresh_payload = {
            'sub': str(user.id),
            'iat': int(time.time()),
            'exp': int(time.time()) + timedelta(days=7).total_seconds(),
            'fresh': False,
            'type': 'refresh'
        }
        refresh_token = pyjwt.encode(refresh_payload, secret, algorithm='HS256')
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }, 200
    return None, 401

def requires_permission(permission_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 尝试从多个来源获取token
            token = get_token_from_request()
            
            if not token:
                return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
            
            try:
                from flask import current_app
                secret = current_app.config['JWT_SECRET_KEY']
                decoded_token = pyjwt.decode(token, secret, algorithms=['HS256'])
                user_id = decoded_token.get('sub')
                if user_id is None:
                    return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
            except Exception as e:
                return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
            
            user = User.query.get(int(user_id))
            
            if not user or not user.is_active:
                return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
            
            if user.role.name == '超级管理员':
                return f(*args, **kwargs)
            
            permission = Permission.query.filter_by(code=permission_code).first()
            if not permission:
                return jsonify({'code': 403, 'message': '权限不存在', 'data': {}}), 403
            
            has_permission = role_permissions.join(Role).filter(
                role_permissions.c.permission_id == permission.id,
                Role.id == user.role_id
            ).first()
            
            if not has_permission:
                return jsonify({'code': 403, 'message': '权限不足', 'data': {}}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_role(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 尝试从多个来源获取token
            token = get_token_from_request()
            
            if not token:
                return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
            
            try:
                from flask import current_app
                secret = current_app.config['JWT_SECRET_KEY']
                decoded_token = pyjwt.decode(token, secret, algorithms=['HS256'])
                user_id = decoded_token.get('sub')
                if user_id is None:
                    return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
            except Exception as e:
                return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
            
            user = User.query.get(int(user_id))
            
            if not user or not user.is_active:
                return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
            
            if user.role.name == '超级管理员' or user.role.name == role_name:
                return f(*args, **kwargs)
            
            return jsonify({'code': 403, 'message': '权限不足', 'data': {}}), 403
        return decorated_function
    return decorator
