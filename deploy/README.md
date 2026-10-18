# 部署说明（华为云 / Ubuntu）

> 目标：把项目跑在服务器上，用域名访问，并且**不把毛病一起暴露到公网**。

---

## 0. 两个硬前提（先确认，不然会白折腾）

### ① ICP 备案

服务器在**中国大陆**（华为云 华北/华东/华南）时，域名解析过去**必须完成 ICP 备案**，否则运营商侧直接拦截，表现为"域名打不开、IP 能访问"。

- 备案在**华为云控制台 → 备案**里提交，需要域名实名 + 服务器（需购买满 3 个月的弹性云服务器）
- 没备案之前，只能用 `http://<公网IP>:端口` 访问，或者先换香港/海外节点

### ② 这台机器不能裸奔上线

当前代码里还有几个必须处理的地方：

| 问题 | 处理 |
|---|---|
| 管理后台 5001 端口 | **绝不能**对公网开放，只走 nginx 反代 + IP 白名单 |
| 默认密码 `admin123` | 上线第一件事改掉 |
| `APP_SECRET_KEY` / `INTERNAL_TOKEN` | 用 `deploy/.env.example` 生成随机值 |
| Flask debug | 生产走 gunicorn，不执行 `app.run(debug=True)` |
| 明文密码存储 | 这是已知技术债，公网部署前至少要改成哈希 |

---

## 1. 上传项目

本地打包（排除虚拟环境、缓存、git）：

```powershell
# 在项目上一级目录执行
tar -czf breast-cancer.tar.gz `
  --exclude=myenv310 --exclude=.git --exclude=__pycache__ `
  --exclude=*.pyc --exclude=agent.db `
  breast-cancer-detection
```

上传并解压：

```bash
scp -P 32222 breast-cancer.tar.gz root@8.133.196.107:/tmp/
ssh -p 32222 root@8.133.196.107
mkdir -p /opt && tar -xzf /tmp/breast-cancer.tar.gz -C /opt
```

## 2. 一键部署

```bash
cd /opt/breast-cancer-detection
sudo bash deploy/deploy.sh your-domain.com admin.your-domain.com
```

脚本会做：装依赖 → 建 venv → 装 Python 包 → 生成 `.env` → 初始化数据库 →
装 systemd 服务 → 配 nginx → 申请证书。

## 3. 域名解析

在域名服务商（阿里云/腾讯云/华为云 DNS）添加两条 A 记录：

| 主机记录 | 记录类型 | 记录值 |
|---|---|---|
| `@` | A | 8.133.196.107 |
| `admin` | A | 8.133.196.107 |

生效后用 `ping your-domain.com` 确认指向。

## 4. 华为云安全组

只放行这三个端口，**5000 / 5001 不要开放**：

| 端口 | 用途 |
|---|---|
| 22（或 32222） | SSH，建议限制来源 IP |
| 80 | HTTP（跳转 HTTPS / 证书校验） |
| 443 | HTTPS |

## 5. 上线检查清单

```bash
curl -I https://your-domain.com/login          # 应 200
curl -I https://admin.your-domain.com/         # 应 200（且仅你的 IP 可访问）
sudo systemctl status breast-cancer admin-backend
sudo journalctl -u breast-cancer -n 50
```

页面里逐项确认：

- [ ] 登录成功（admin 密码已改）
- [ ] 提交一次预测，结果页正常
- [ ] 「解读这次结果」能出流式结果（验证 SSE 没被 nginx 缓冲）
- [ ] 批量上传一个 CSV 成功
- [ ] 「系统巡检」有返回

## 6. 日常运维

```bash
sudo systemctl restart breast-cancer        # 重启用户端
sudo journalctl -u breast-cancer -f         # 看日志
sudo bash deploy/backup.sh                  # 手工备份（建议加 crontab）
```

crontab 每天 3 点备份：

```cron
0 3 * * * /opt/breast-cancer-detection/deploy/backup.sh >> /var/log/bc-backup.log 2>&1
```

---

## 常见问题

**502 Bad Gateway**
`systemctl status breast-cancer` 看进程是否在；再看 `journalctl` 里是否有依赖缺失。

**SSE 不是流式，攒到最后才出**
nginx 里 `/api/agent/run` 的 `proxy_buffering off` 没生效，检查是否被别的 location 覆盖。

**`database is locked`**
SQLite 并发写冲突。这个项目写少读多，正常不会；若出现，把 gunicorn `workers` 降到 1。

**中文乱码 / PDF 导出失败**
服务器没装中文字体：

```bash
apt-get install -y fonts-wqy-zenhei fonts-wqy-microhei
```
