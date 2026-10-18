"""一次性初始化管理后台数据库。

gunicorn 不会执行 admin_backend/app.py 的 __main__ 块，
所以建表、权限、角色、默认管理员要单独跑一次：

    python deploy/init_admin.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ADMIN_DIR = os.path.join(ROOT, 'admin_backend')

sys.path.insert(0, ADMIN_DIR)
os.chdir(ADMIN_DIR)

from app import app, db, init_permissions, init_roles, init_default_model  # noqa: E402
from models import User, Role  # noqa: E402


def main() -> int:
    with app.app_context():
        db.create_all()
        init_permissions()
        init_roles()

        if not User.query.filter_by(username='admin').first():
            role = Role.query.filter_by(name='超级管理员').first()
            admin = User(username='admin', email='admin@example.com',
                         role_id=role.id if role else 1, is_active=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('已创建默认管理员 admin / admin123')

        init_default_model()
    print('管理后台初始化完成:', os.path.join(ADMIN_DIR, 'instance', 'admin.db'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
