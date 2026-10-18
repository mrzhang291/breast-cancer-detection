import os
import json
import sys
import signal
import subprocess
import jwt
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, User, Role, Permission, LoginLog, Model
from auth import requires_permission
from api.user_api import user_api
from api.prediction_api import prediction_api
from api.model_api import model_api
from api.system_api import system_api
from api.statistics_api import statistics_api
from api.log_api import log_api
from api.permission_api import permission_api
from api.ai_api import ai_api
from api.batch_api import batch_api
from api.coze_api import coze_api
from api.knowledge_api import knowledge_api

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret')
app.config['JWT_DECODE_LEEWAY'] = 0
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret')
basedir = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', f'sqlite:///{os.path.join(basedir, "instance", "admin.db")}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True, origins=['http://127.0.0.1:5000', 'http://127.0.0.1:5001', 'http://127.0.0.1:8000', 'http://localhost:5000', 'http://localhost:5001', 'http://localhost:8000'], expose_headers=['Set-Cookie'])

app.register_blueprint(user_api)
app.register_blueprint(prediction_api)
app.register_blueprint(model_api)
app.register_blueprint(system_api)
app.register_blueprint(statistics_api)
app.register_blueprint(log_api)
app.register_blueprint(permission_api)
app.register_blueprint(ai_api)
app.register_blueprint(batch_api)
app.register_blueprint(coze_api)
app.register_blueprint(knowledge_api)


@app.route('/console/static/<path:filename>')
def console_static(filename):
    """本地开发时兼容生产 /console/static 前缀；生产由 nginx 直接处理。"""
    return app.send_static_file(filename)


@app.route('/console/admin/login')
def console_login_alias():
    return redirect('/admin/login')


@app.route('/console/admin')
def console_admin_alias():
    return redirect('/admin')

def init_permissions():
    permissions = [
        {'name': '用户创建', 'code': 'user_create'},
        {'name': '用户查看', 'code': 'user_view'},
        {'name': '用户编辑', 'code': 'user_edit'},
        {'name': '用户删除', 'code': 'user_delete'},
        
        {'name': '预测记录查看', 'code': 'prediction_view'},
        {'name': '预测记录删除', 'code': 'prediction_delete'},
        {'name': '预测记录导出', 'code': 'prediction_export'},
        
        {'name': '模型上传', 'code': 'model_upload'},
        {'name': '模型查看', 'code': 'model_view'},
        {'name': '模型编辑', 'code': 'model_edit'},
        {'name': '模型删除', 'code': 'model_delete'},
        {'name': '模型激活', 'code': 'model_activate'},
        
        {'name': '系统查看', 'code': 'system_view'},
        {'name': '系统编辑', 'code': 'system_edit'},
        
        {'name': '统计查看', 'code': 'statistics_view'},
        {'name': '统计导出', 'code': 'statistics_export'},
        
        {'name': '日志查看', 'code': 'log_view'},
        {'name': '日志编辑', 'code': 'log_edit'},
        
        {'name': '角色创建', 'code': 'role_create'},
        {'name': '角色查看', 'code': 'role_view'},
        {'name': '角色编辑', 'code': 'role_edit'},
        {'name': '角色删除', 'code': 'role_delete'},
        
        {'name': '权限创建', 'code': 'permission_create'},
        {'name': '权限查看', 'code': 'permission_view'},
        {'name': '权限编辑', 'code': 'permission_edit'},
        {'name': '权限删除', 'code': 'permission_delete'},
        
        {'name': 'AI查看', 'code': 'ai_view'},
        {'name': 'AI编辑', 'code': 'ai_edit'},
        
        {'name': '批量任务查看', 'code': 'batch_view'},
        {'name': '批量任务编辑', 'code': 'batch_edit'},
        {'name': '批量任务删除', 'code': 'batch_delete'}
    ]
    
    for perm in permissions:
        if not Permission.query.filter_by(code=perm['code']).first():
            permission = Permission(**perm)
            db.session.add(permission)
    
    db.session.commit()

def init_roles():
    roles = [
        {'name': '超级管理员', 'description': '拥有所有权限'},
        {'name': '普通管理员', 'description': '拥有大部分管理权限'},
        {'name': '医生用户', 'description': '仅能查看和使用预测功能'}
    ]
    
    for role_data in roles:
        if not Role.query.filter_by(name=role_data['name']).first():
            role = Role(**role_data)
            db.session.add(role)
    
    db.session.commit()

    super_admin = Role.query.filter_by(name='超级管理员').first()
    if super_admin:
        all_permissions = Permission.query.all()
        existing_permission_ids = [p.id for p in super_admin.permissions]
        for perm in all_permissions:
            if perm.id not in existing_permission_ids:
                super_admin.permissions.append(perm)
    
    db.session.commit()

@app.route('/api/login', methods=['POST'])
def login():
    from flask import make_response
    data = request.get_json(silent=True) or {}
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'code': 400, 'message': '缺少用户名或密码', 'data': {}}), 400

    username = data['username']
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(data['password']):
        if not user.is_active:
            log_login(user.id, request.remote_addr, request.user_agent.string, 'failed')
            return jsonify({'code': 401, 'message': '用户已被禁用', 'data': {}}), 401
        
        payload = {
            'sub': str(user.id),
            'iat': int(time.time()),
            'exp': int(time.time()) + timedelta(hours=1).total_seconds(),
            'fresh': False,
            'type': 'access'
        }
        access_token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        log_login(user.id, request.remote_addr, request.user_agent.string, 'success')
        
        # 创建响应
        response = make_response(jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'token': access_token,
                'user': user.to_dict()
            }
        }))
        
        # 设置Cookie
        response.set_cookie(
            'access_token',
            value=access_token,
            httponly=True,
            secure=False,
            samesite='Strict',
            max_age=3600,
            path='/'
        )
        
        return response
    
    log_login(None, request.remote_addr, request.user_agent.string, 'failed')
    return jsonify({'code': 401, 'message': '用户名或密码错误', 'data': {}}), 401

def log_login(user_id, ip_address, user_agent, status):
    login_log = LoginLog(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        login_time=datetime.now(),
        status=status
    )
    db.session.add(login_log)
    db.session.commit()

@app.route('/api/refresh', methods=['POST'])
def refresh():
    from auth import get_token_from_request
    
    token = get_token_from_request()
    if not token:
        return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
    
    try:
        decoded_token = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = decoded_token.get('sub')
        if user_id is None:
            return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
    except Exception as e:
        return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
    
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
    
    payload = {
        'sub': str(user.id),
        'iat': int(time.time()),
        'exp': int(time.time()) + timedelta(hours=1).total_seconds(),
        'fresh': False,
        'type': 'access'
    }
    access_token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {'access_token': access_token}}), 200

@app.route('/', methods=['GET'])
def root_redirect():
    return redirect('/admin/login')

@app.route('/admin/login', methods=['GET'])
def admin_login_page():
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    return render_template('admin.html')

@app.route('/coze', methods=['GET'])
def coze_page():
    return render_template('coze_chat.html')

@app.route('/api/me', methods=['GET'])
def get_current_user():
    from auth import get_token_from_request
    
    # 尝试从多个来源获取token
    token = get_token_from_request()
    
    if not token:
        return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401
    
    try:
        # 使用 PyJWT 解码token
        decoded_token = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = decoded_token.get('sub')
        if user_id is None:
            return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
    except Exception as e:
        return jsonify({'code': 401, 'message': '无效的token', 'data': {}}), 401
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在', 'data': {}}), 404
    
    return jsonify({'code': 200, 'message': 'success', 'data': user.to_dict()}), 200

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'code': 400, 'message': '请求参数错误', 'data': {}}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'code': 403, 'message': '权限不足', 'data': {}}), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'message': '资源不存在', 'data': {}}), 404

@app.errorhandler(500)
def internal_error(error):
    import traceback
    error_msg = str(error) if str(error) else '服务器内部错误'
    print(f"500错误: {error_msg}")
    print(traceback.format_exc())
    return jsonify({'code': 500, 'message': error_msg, 'data': {}}), 500

def init_default_model():
    if not Model.query.first():
        default_model = Model(
            name='乳腺癌检测模型',
            version='1.0.0',
            file_path='models/default_model.pkl',
            accuracy=0.925,
            recall=0.912,
            f1_score=0.918,
            is_active=True,
            uploaded_by=1,
            description='基于机器学习的乳腺癌检测模型，使用特征提取算法进行分类。'
        )
        db.session.add(default_model)
        db.session.commit()

def stop_all_servers():
    """停止所有相关服务器进程"""
    print("\n正在停止所有服务器进程...")
    
    ports_to_stop = [5000, 5001]
    
    for port in ports_to_stop:
        try:
            result = subprocess.run(
                ['netstat', '-ano', '-p', 'TCP'],
                capture_output=True,
                text=True
            )
            
            pids = []
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        pids.append(pid)
            
            if pids:
                print(f"找到占用端口 {port} 的进程: {pids}")
                for pid in pids:
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/PID', pid],
                            capture_output=True,
                            text=True
                        )
                        print(f"已终止进程 {pid}")
                    except Exception as e:
                        print(f"终止进程 {pid} 失败: {e}")
        except Exception as e:
            print(f"处理端口 {port} 时出错: {e}")
    
    print("所有服务器进程已停止")

def signal_handler(sig, frame):
    """处理终止信号"""
    print(f"\n收到终止信号 {sig}")
    stop_all_servers()
    sys.exit(0)

if __name__ == '__main__':
    print("正在初始化应用...")
    try:
        with app.app_context():
            print("创建数据库表...")
            db.create_all()
            print("初始化权限...")
            init_permissions()
            print("初始化角色...")
            init_roles()
            
            print("检查管理员用户...")
            if not User.query.filter_by(username='admin').first():
                admin_role = Role.query.filter_by(name='超级管理员').first()
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    role_id=admin_role.id,
                    is_active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("创建管理员用户成功")
            
            print("初始化默认模型...")
            init_default_model()
        
        print("初始化完成")
    except Exception as e:
        print(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    # 注册信号处理函数
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 检查是否从主程序启动
    from_subprocess = os.environ.get('FROM_SUBPROCESS', 'false') == 'true'
    
    host = '127.0.0.1'
    port = 5001
    
    if not from_subprocess:
        print('\n' + '='*60)
        print('乳腺癌检测系统管理后台启动成功！')
        print('访问地址: http://127.0.0.1:{}'.format(port))
        print('='*60 + '\n')
    
    try:
        print(f"启动Flask服务器: {host}:{port}")
        app.run(host=host, port=port, debug=False, use_reloader=False)
        print("服务器已退出")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()

