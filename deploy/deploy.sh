#!/usr/bin/env bash
# 一键部署到 Ubuntu / Debian 服务器（root 或 sudo 执行）
#
#   sudo bash deploy/deploy.sh example.com admin.example.com
#
# 前提：项目已上传到 /opt/breast-cancer-detection
set -euo pipefail

APP_DIR=/opt/breast-cancer-detection
DOMAIN=${1:-}
ADMIN_DOMAIN=${2:-}

if [[ -z "$DOMAIN" ]]; then
  echo "用法: sudo bash deploy/deploy.sh <主域名> [后台域名]"
  exit 1
fi

echo "==> 1/8 安装系统依赖"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

echo "==> 2/8 创建虚拟环境并安装依赖"
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/pip install -r admin_backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/pip install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "==> 3/8 生成 .env（若不存在）"
if [[ ! -f .env ]]; then
  SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))")
  TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
  cat > .env <<EOF
APP_SECRET_KEY=$SECRET
INTERNAL_TOKEN=$TOKEN
AGENT_LLM=auto
# DEEPSEEK_API_KEY=
EOF
  chmod 600 .env
  echo "   已生成 .env，请按需填写 DEEPSEEK_API_KEY"
fi

echo "==> 4/8 初始化管理后台数据库"
sudo -u www-data .venv/bin/python deploy/init_admin.py || .venv/bin/python deploy/init_admin.py

echo "==> 5/8 安装 systemd 服务"
sed "s#/opt/breast-cancer-detection#$APP_DIR#g" deploy/breast-cancer.service > /etc/systemd/system/breast-cancer.service
sed "s#/opt/breast-cancer-detection#$APP_DIR#g" deploy/admin-backend.service > /etc/systemd/system/admin-backend.service
systemctl daemon-reload
systemctl enable --now admin-backend
sleep 2
systemctl enable --now breast-cancer

echo "==> 6/8 配置 nginx"
sed "s/example.com/$DOMAIN/g; s/admin.example.com/$ADMIN_DOMAIN/g" deploy/nginx.conf \
  > /etc/nginx/sites-available/breast-cancer
ln -sf /etc/nginx/sites-available/breast-cancer /etc/nginx/sites-enabled/breast-cancer
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> 7/8 申请 HTTPS 证书"
if [[ -n "$ADMIN_DOMAIN" ]]; then
  certbot --nginx -d "$DOMAIN" -d "$ADMIN_DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || true
else
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || true
fi

echo "==> 8/8 权限与状态"
chown -R www-data:www-data "$APP_DIR"
systemctl --no-pager --lines=0 status breast-cancer || true
systemctl --no-pager --lines=0 status admin-backend || true

echo
echo "部署完成："
echo "  用户端  http://$DOMAIN"
echo "  后台    http://${ADMIN_DOMAIN:-$DOMAIN:5001}"
echo
echo "检查：curl -I http://$DOMAIN/login"
