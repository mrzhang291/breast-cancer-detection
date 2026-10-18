import os
import sys
import json
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Role, PredictionRecord

def migrate_users():
    old_users_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json')
    
    if not os.path.exists(old_users_file):
        print("旧用户文件不存在")
        return
    
    with open(old_users_file, 'r', encoding='utf-8') as f:
        old_users = json.load(f)
    
    with app.app_context():
        doctor_role = Role.query.filter_by(name='医生用户').first()
        if not doctor_role:
            print("医生用户角色不存在")
            return
        
        for username, password_hash in old_users.items():
            if User.query.filter_by(username=username).first():
                print(f"用户 {username} 已存在，跳过")
                continue
            
            user = User(
                username=username,
                role_id=doctor_role.id,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            user.password_hash = password_hash
            
            db.session.add(user)
            print(f"迁移用户: {username}")
        
        db.session.commit()
        print("用户迁移完成")

def migrate_prediction_records():
    old_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'patient_records.db')
    
    if not os.path.exists(old_db_path):
        print("旧数据库文件不存在")
        return
    
    old_conn = sqlite3.connect(old_db_path)
    old_cursor = old_conn.cursor()
    
    old_cursor.execute('SELECT * FROM patient_records')
    old_records = old_cursor.fetchall()
    
    feature_names = [
        'radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean',
        'smoothness_mean', 'compactness_mean', 'concavity_mean', 'concave_points_mean',
        'symmetry_mean', 'fractal_dimension_mean',
        'radius_se', 'texture_se', 'perimeter_se', 'area_se',
        'smoothness_se', 'compactness_se', 'concavity_se', 'concave_points_se',
        'symmetry_se', 'fractal_dimension_se',
        'radius_worst', 'texture_worst', 'perimeter_worst', 'area_worst',
        'smoothness_worst', 'compactness_worst', 'concavity_worst', 'concave_points_worst',
        'symmetry_worst', 'fractal_dimension_worst'
    ]
    
    with app.app_context():
        for record in old_records:
            record_dict = dict(zip([desc[0] for desc in old_cursor.description], record))
            
            username = record_dict['username']
            user = User.query.filter_by(username=username).first()
            
            if not user:
                print(f"用户 {username} 不存在，跳过记录 {record_dict['id']}")
                continue
            
            features = {}
            for feature_name in feature_names:
                features[feature_name] = record_dict.get(feature_name, 0.0)
            
            features_json = json.dumps(features)
            
            if PredictionRecord.query.filter_by(id=record_dict['id']).first():
                print(f"记录 {record_dict['id']} 已存在，跳过")
                continue
            
            new_record = PredictionRecord(
                id=record_dict['id'],
                user_id=user.id,
                all_30_features_json=features_json,
                prediction_result=record_dict['result'],
                confidence=record_dict['confidence'],
                created_at=datetime.strptime(record_dict['predict_time'], '%Y-%m-%d %H:%M:%S') 
                if isinstance(record_dict['predict_time'], str) else datetime.now(),
                is_deleted=False
            )
            
            db.session.add(new_record)
            print(f"迁移记录: {record_dict['id']}")
        
        db.session.commit()
        print("预测记录迁移完成")
    
    old_conn.close()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        if not Role.query.filter_by(name='超级管理员').first():
            from app import init_roles, init_permissions
            init_permissions()
            init_roles()
        
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
        
        migrate_users()
        migrate_prediction_records()
        
        print("数据迁移全部完成")