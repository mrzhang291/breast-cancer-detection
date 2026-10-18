import io, sys
sys.stdout.reconfigure(encoding="utf-8")

# 1) admin 依赖补 flask-cors
p = "admin_backend/requirements.txt"
s = io.open(p, encoding="utf-8").read()
if "Flask-Cors" not in s:
    s = s.rstrip() + "\nFlask-Cors>=4.0.0\n"
    io.open(p, "w", encoding="utf-8").write(s)
    print("requirements 已补 Flask-Cors")

# 2) gunicorn 降为 1 worker（2G 内存）
g = "deploy/gunicorn.conf.py"
t = io.open(g, encoding="utf-8").read()
t = t.replace("workers = min(2, multiprocessing.cpu_count())", "workers = 1")
io.open(g, "w", encoding="utf-8").write(t)
print("gunicorn workers=1")

# 3) 部署脚本：建 instance 目录 + admin 单 worker
d = "deploy/deploy-euleros.sh"
u = io.open(d, encoding="utf-8").read()
if 'mkdir -p "$APP_DIR/admin_backend/instance"' not in u:
    u = u.replace('echo "==> 4/9 初始化管理后台数据库"',
                  'echo "==> 4/9 初始化管理后台数据库"\nmkdir -p "$APP_DIR/admin_backend/instance" "$APP_DIR/static/shap"', 1)
u = u.replace("-w 2 -k gthread", "-w 1 -k gthread")
io.open(d, "w", encoding="utf-8").write(u)
print("deploy-euleros.sh 已修正")
