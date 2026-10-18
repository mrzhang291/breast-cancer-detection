"""gunicorn 配置：面向单机小流量部署。

    gunicorn -c deploy/gunicorn.conf.py deploy.wsgi:application
"""
import multiprocessing
import os

bind = '127.0.0.1:5000'          # 只监听本机，由 nginx 对外
workers = 1
threads = 4
worker_class = 'gthread'
timeout = 180                    # 多步任务 / 报告生成可能较慢
graceful_timeout = 30
keepalive = 5

preload_app = True               # 模型只加载一次再 fork，省内存

accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# 上传批量 CSV 时的临时目录
worker_tmp_dir = '/dev/shm'
