#!/usr/bin/env bash
# 华为云 EulerOS 3.0 / openEuler 专用部署脚本
#
#   bash deploy/deploy-euleros.sh <公网IP或域名>
#
# 与 Ubuntu 版的区别：
#   - 用 dnf 而不是 apt
#   - 服务以 nginx 用户运行（EulerOS 没有 www-data）
#   - nginx 配置放 conf.d（没有 sites-available）
#   - 额外处理 SELinux 与 firewalld
set -euo pipefail

APP_DIR=/opt/breast-cancer-detection
SITE=${1:-}
PY=${PYTHON_BIN:-python3}

if [[ -z "$SITE" ]]; then
  echo "用法: bash deploy/deploy-euleros.sh <公网IP或域名>"
  exit 1
fi

echo "==> 0/9 系统信息"
cat /etc/os-release | head -2
$PY --version || { echo "缺少 python3"; exit 1; }

echo "==> 1/9 安装系统依赖"
dnf install -y python3 python3-pip nginx git sqlite sqlite-devel 2>/dev/null || \
  yum install -y python3 python3-pip nginx git sqlite sqlite-devel

echo "==> 2/9 创建虚拟环境"
cd "$APP_DIR"
$PY -m venv .venv
.venv/bin/pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/pip install -r admin_backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/pip install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "==> 3/9 生成 .env"
if [[ ! -f .env ]]; then
  SECRET=$($PY -c "import secrets;print(secrets.token_urlsafe(32))")
  TOKEN=$($PY -c "import secrets;print(secrets.token_urlsafe(24))")
  cat > .env <<EOF
APP_SECRET_KEY=$SECRET
INTERNAL_TOKEN=$TOKEN
AGENT_LLM=auto
EOF
  chmod 600 .env
  echo "   已生成 .env"
fi

echo "==> 4/9 初始化管理后台数据库"
mkdir -p "$APP_DIR/admin_backend/instance" "$APP_DIR/static/shap"
.venv/bin/python deploy/init_admin.py

echo "==> 4.5/9 构建 RAG 索引"
.venv/bin/python -m agent.rag.build >/dev/null 2>&1 || \
  .venv/bin/python -m agent.rag.build

echo "==> 5/9 写入 systemd 服务"
cat > /etc/systemd/system/admin-backend.service <<EOF
[Unit]
Description=Breast Cancer Detection - admin backend
After=network.target

[Service]
Type=simple
User=nginx
Group=nginx
WorkingDirectory=$APP_DIR/admin_backend
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn -b 127.0.0.1:5001 -w 1 -k gthread --threads 4 --timeout 60 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/breast-cancer.service <<EOF
[Unit]
Description=Breast Cancer Detection - web app
After=network.target admin-backend.service

[Service]
Type=simple
User=nginx
Group=nginx
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn -c deploy/gunicorn.conf.py deploy.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo "==> 6/9 授权与启动"
chown -R nginx:nginx "$APP_DIR"
systemctl enable --now admin-backend
sleep 2
systemctl enable --now breast-cancer
sleep 3

echo "==> 7/9 配置 nginx"
cat > /etc/nginx/conf.d/breast-cancer.conf <<EOF
server {
    listen 80 default_server;
    server_name $SITE;

    client_max_body_size 20m;

    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
        access_log off;
    }

    location /api/agent/run {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
EOF
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "==> 8/9 SELinux 与防火墙"
if command -v getenforce >/dev/null 2>&1 && [[ "$(getenforce)" == "Enforcing" ]]; then
  echo "   SELinux 开启，放行 nginx 反代"
  setsebool -P httpd_can_network_connect 1 || true
fi
if systemctl is-active --quiet firewalld; then
  firewall-cmd --permanent --add-service=http >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-service=https >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
  echo "   firewalld 已放行 80/443"
fi

echo "==> 9/9 自检"
curl -s -o /dev/null -w "   用户端 HTTP %{http_code}\n" http://127.0.0.1/login || true
curl -s -o /dev/null -w "   后台   HTTP %{http_code}\n" http://127.0.0.1:5001/api/me || true

echo
echo "部署完成：http://$SITE"
echo "账号：admin / admin123（请尽快修改）"
echo "日志：journalctl -u breast-cancer -f"
