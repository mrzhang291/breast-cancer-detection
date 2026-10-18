"""gunicorn 入口。

用法（在项目根目录）：
    gunicorn -c deploy/gunicorn.conf.py deploy.wsgi:application
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app import app as application  # noqa: E402

app = application
