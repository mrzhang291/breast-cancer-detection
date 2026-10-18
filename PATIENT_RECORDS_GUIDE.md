# 患者预测记录管理系统使用指南

## 📋 功能概述

本系统基于 Flask + SQLite3 实现了完整的患者预测记录管理功能。所有预测成功后的记录都会自动保存到数据库，用户可以查看、筛选和管理自己的预测历史。

## 🗄️ 数据库结构

### 表名：patient_records

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER (PK) | 主键自增 |
| username | TEXT | 登录用户名 |
| radius_mean 到 fractal_dimension_worst | REAL | 30个肿瘤特征值 |
| result | TEXT | 诊断结果（Benign/Malignant） |
| confidence | REAL | 预测置信度（0-1） |
| predict_time | DATETIME | 预测耗时（秒） |
| created_at | DATETIME | 记录创建时间 |

**自动创建的索引：**
- idx_username：加快用户记录查询
- idx_result：加快诊断结果筛选
- idx_created_at：加快时间排序

## 🚀 核心功能

### 1. 自动保存预测记录
- ✅ 用户完成预测后，系统自动将 30 个特征值、诊断结果、置信度保存到数据库
- ✅ 每条记录都记录了预测的精确时间戳
- ✅ 数据完全隔离，用户只能查看自己的记录

### 2. 历史记录列表（/record）
**功能特性：**
- 📊 统计信息展示：总记录数、良性/恶性数、平均置信度
- 📄 分页显示：每页 10 条记录，支持快速翻页
- 🔍 筛选功能：按诊断结果（全部/良性/恶性）筛选
- ⏰ 按时间倒序排列：最新的记录显示在顶部
- 🎨 美观的表格展示：包含关键特征预览

### 3. 单条记录详情
- 点击「详情」按钮查看完整信息
- 显示诊断结果、置信度、预测时间
- 包含医学安全提示

### 4. 记录删除
**两种删除方式：**

#### 单条删除（/record/delete/<id>）
```javascript
POST /record/delete/<id>
```
- 需要用户登录
- 仅允许删除该用户自己的记录
- 删除后立即刷新页面

#### 清空所有记录（/record/clear）
```javascript
POST /record/clear
Content-Type: application/json

{
  "password": "用户输入的密码"
}
```
- 需要密码验证以防误删
- 删除所有该用户的记录
- 返回删除记录数

### 5. 权限控制
- ✅ 未登录用户无法访问 /record 页面（重定向到登录）
- ✅ 用户只能查看自己的记录
- ✅ 用户只能删除自己的记录
- ✅ 删除需要密码验证

## 📁 文件结构

```
breast-cancer-detection/
├── db_patient.py              # 数据库管理模块（新增）
├── patient_records.db         # SQLite 数据库文件（自动创建）
├── app.py                     # 主应用（已修改）
│   ├── /record                # 历史记录页面路由
│   ├── /record/delete/<id>    # 删除单条记录路由
│   ├── /record/clear          # 清空所有记录路由
│   └── /predict               # 预测路由（已增强）
├── templates/
│   ├── record.html            # 记录管理页面（新增）
│   ├── home.html              # 首页（已修改，添加记录链接）
│   ├── result.html            # 结果页面（无需修改）
│   └── ...
```

## 🔗 集成说明

### 已自动集成的内容：

1. **app.py 改动：**
   ```python
   # 添加了导入
   from db_patient import init_db, add_record, ...
   
   # 初始化数据库
   init_db()
   
   # /predict 路由中自动保存记录
   add_record(username, data, output, confidence)
   
   # 新增三个路由
   @app.route('/record', methods=['GET'])
   @app.route('/record/delete/<int:record_id>', methods=['POST'])
   @app.route('/record/clear', methods=['POST'])
   ```

2. **home.html 改动：**
   - 用户菜单新增「预测记录」链接
   - 链接到 /record 页面

3. **新文件：**
   - db_patient.py：数据库操作模块
   - templates/record.html：记录管理页面

## 🎯 使用流程

### 用户操作流程：

```
1. 登录系统 → 
2. 输入特征值进行预测 →
3. 查看预测结果（自动保存记录）→
4. 点击用户菜单 → 选择「预测记录」 →
5. 在记录页面：
   - 查看统计信息
   - 按诊断结果筛选
   - 查看记录详情
   - 删除单条记录
   - 清空所有记录（需密码）
```

## 📊 API 接口

### GET /record
获取用户的预测记录列表

**参数：**
- `page` (int, optional)：页码，默认为 1
- `result` (str, optional)：筛选诊断结果（Benign/Malignant）

**返回：**
```html
record.html 页面 + 以下数据：
- records：分页的记录列表
- page：当前页码
- total_pages：总页数
- total_records：总记录数
- result_filter：应用的筛选条件
- stats：统计信息对象
```

### POST /record/delete/<id>
删除指定ID的记录

**限制：**
- 必须登录
- 只能删除该用户自己的记录

**响应：**
```json
{
  "success": true,
  "message": "记录删除成功"
}
```

### POST /record/clear
清空用户的所有记录

**请求体：**
```json
{
  "password": "用户登录密码"
}
```

**验证：**
- 密码必须与登录密码匹配

**响应：**
```json
{
  "success": true,
  "message": "已删除 X 条记录"
}
```

## 🔒 安全特性

✅ **数据隔离**
- 用户只能查看/删除自己的记录
- 数据库查询包含 username 过滤

✅ **权限控制**
- 清空所有记录需要密码验证
- 使用 check_password_hash 进行安全验证

✅ **输入验证**
- 所有用户输入都经过验证
- SQL 查询使用参数化防止注入

## 📈 性能优化

✅ **数据库索引**
- username 索引：快速查询用户记录
- result 索引：快速筛选诊断结果
- created_at 索引：快速排序

✅ **分页查询**
- 避免一次加载全部数据
- 每页限制为 10 条记录

## 🧪 测试命令

### 启动应用
```bash
# 设置 API Key
$env:DEEPSEEK_API_KEY = "sk-xxxxxx"

# 运行应用
python app.py
```

### 手动测试数据输入
```python
# Python 交互式测试
from db_patient import *

# 初始化数据库
init_db()

# 添加测试记录
add_record('testuser', [1.0]*30, 'Benign', 0.95)

# 查询用户记录
records = get_user_records('testuser')

# 获取统计信息
stats = get_user_statistics('testuser')
print(stats)
```

## 🔄 数据备份

SQLite 数据库文件：`patient_records.db`
- 位置：项目根目录
- 可直接复制备份
- 使用 SQLite 浏览器查看（推荐 DB Browser for SQLite）

## 📝 常见问题

**Q1：如何导出用户的所有记录？**
```python
import sqlite3
conn = sqlite3.connect('patient_records.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM patient_records WHERE username = ?", ('username',))
records = cursor.fetchall()
# 导出为 CSV 或 Excel
```

**Q2：如何清空整个数据库？**
```python
import os
os.remove('patient_records.db')
# 下次启动时会重新创建
```

**Q3：记录是否会影响预测速度？**
- 否，数据库操作异步进行
- 不会阻塞预测过程

**Q4：如何升级现有数据库？**
```python
# 如果需要修改表结构
from db_patient import init_db
# 删除旧的 patient_records.db
# 运行 init_db() 创建新表
```

## 👨‍💻 开发者信息

**最后更新：** 2026-04-19
**系统版本：** v1.0
**兼容性：** Python 3.6+, Flask 1.1+, SQLite 3

---

如有问题或建议，请提交 Issue！
