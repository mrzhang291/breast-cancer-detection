---
title: 乳腺癌检测系统 API
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - ruby: Ruby
  - python: Python
  - php: PHP
  - java: Java
  - go: Go
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.30"

---

# 乳腺癌检测系统 API

乳腺癌检测系统后端API文档

Base URLs:

# Authentication

- HTTP Authentication, scheme: bearer

# Default

## POST 用户登录

POST /api/login

用户登录获取JWT Token

> Body 请求参数

```json
{
  "username": "string",
  "password": "string"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» username|body|string| 是 |none|
|» password|body|string| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|登录成功|None|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|登录失败|None|

## GET 获取预测记录列表

GET /api/predictions

分页获取所有预测记录（管理端）

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|integer| 否 |none|
|page_size|query|integer| 否 |none|
|user_id|query|integer| 否 |none|
|search|query|string| 否 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST 添加预测记录

POST /api/predictions

接收用户端预测数据并保存

> Body 请求参数

```json
{
  "user_id": 0,
  "all_30_features_json": "string",
  "prediction_result": "string",
  "confidence": 0
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» user_id|body|integer| 是 |none|
|» all_30_features_json|body|string| 是 |none|
|» prediction_result|body|string| 是 |none|
|» confidence|body|number| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取单条预测记录

GET /api/predictions/{record_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|record_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|记录不存在|None|

## DELETE 删除预测记录

DELETE /api/predictions/{record_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|record_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|None|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|记录不存在|None|

## POST 批量删除预测记录

POST /api/predictions/batch_delete

> Body 请求参数

```json
{
  "ids": [
    0
  ]
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» ids|body|[integer]| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取用户列表

GET /api/users

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|integer| 否 |none|
|page_size|query|integer| 否 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST 创建用户

POST /api/users

> Body 请求参数

```json
{
    "username": "牢梓晨",
    "password": "P6joglIV7XLLrGP",
    "role_id": 1
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» username|body|string| 是 |none|
|» password|body|string| 是 |none|
|» role_id|body|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取用户详情

GET /api/users/{user_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|user_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|用户不存在|None|

## PUT 更新用户

PUT /api/users/{user_id}

> Body 请求参数

```json
{}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|user_id|path|integer| 是 |none|
|body|body|object| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## DELETE 删除用户

DELETE /api/users/{user_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|user_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|None|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|用户不存在|None|

## GET 获取模型列表

GET /api/models

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST 上传模型

POST /api/models

> Body 请求参数

```yaml
{}

```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|上传成功|None|

## GET 获取模型详情

GET /api/models/{model_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|model_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## PUT 更新模型

PUT /api/models/{model_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|model_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## DELETE 删除模型

DELETE /api/models/{model_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|model_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|None|

## GET 获取角色列表

GET /api/roles

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST 创建角色

POST /api/roles

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取角色详情

GET /api/roles/{role_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|role_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## PUT 更新角色

PUT /api/roles/{role_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|role_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## DELETE 删除角色

DELETE /api/roles/{role_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|role_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|None|

## GET 获取权限列表

GET /api/permissions

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST 创建权限

POST /api/permissions

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## PUT 更新权限

PUT /api/permissions/{permission_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|permission_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## DELETE 删除权限

DELETE /api/permissions/{permission_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|permission_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|None|

## GET 获取预测统计

GET /api/statistics/prediction_count

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取预测趋势

GET /api/statistics/trend

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|period|query|string| 否 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取用户活跃度

GET /api/statistics/user_activity

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取模型性能

GET /api/statistics/model_performance

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取仪表板数据

GET /api/statistics/dashboard

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST AI预测

POST /api/ai/predict

> Body 请求参数

```json
{
  "features": {}
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» features|body|object| 否 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|预测成功|None|

## POST AI聊天

POST /api/ai/chat

> Body 请求参数

```json
{
  "question": "string"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» question|body|string| 否 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## GET 获取系统配置

GET /api/system/configs

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## POST 创建系统配置

POST /api/system/configs

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## PUT 更新系统配置

PUT /api/system/configs/{config_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|config_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## DELETE 删除系统配置

DELETE /api/system/configs/{config_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|config_id|path|integer| 是 |none|

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|None|

## GET 获取系统信息

GET /api/system/info

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

## PUT 更新系统信息

PUT /api/system/info

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|None|

# 数据模型

<h2 id="tocS_PredictionRecord">PredictionRecord</h2>

<a id="schemapredictionrecord"></a>
<a id="schema_PredictionRecord"></a>
<a id="tocSpredictionrecord"></a>
<a id="tocspredictionrecord"></a>

```json
{
  "id": 0,
  "user_id": 0,
  "username": "string",
  "all_30_features_json": "string",
  "prediction_result": "string",
  "confidence": 0,
  "created_at": "2019-08-24T14:15:22Z"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|integer|false|none||none|
|user_id|integer|false|none||none|
|username|string|false|none||none|
|all_30_features_json|string|false|none||none|
|prediction_result|string|false|none||none|
|confidence|number|false|none||none|
|created_at|string(date-time)|false|none||none|

<h2 id="tocS_User">User</h2>

<a id="schemauser"></a>
<a id="schema_User"></a>
<a id="tocSuser"></a>
<a id="tocsuser"></a>

```json
{
  "id": 0,
  "username": "string",
  "email": "string",
  "role_id": 0,
  "role_name": "string",
  "is_active": true,
  "created_at": "2019-08-24T14:15:22Z"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|integer|false|none||none|
|username|string|false|none||none|
|email|string|false|none||none|
|role_id|integer|false|none||none|
|role_name|string|false|none||none|
|is_active|boolean|false|none||none|
|created_at|string(date-time)|false|none||none|

<h2 id="tocS_Model">Model</h2>

<a id="schemamodel"></a>
<a id="schema_Model"></a>
<a id="tocSmodel"></a>
<a id="tocsmodel"></a>

```json
{
  "id": 0,
  "name": "string",
  "version": "string",
  "file_path": "string",
  "accuracy": 0,
  "recall": 0,
  "f1_score": 0,
  "is_active": true,
  "uploaded_by": 0,
  "uploaded_at": "2019-08-24T14:15:22Z"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|integer|false|none||none|
|name|string|false|none||none|
|version|string|false|none||none|
|file_path|string|false|none||none|
|accuracy|number|false|none||none|
|recall|number|false|none||none|
|f1_score|number|false|none||none|
|is_active|boolean|false|none||none|
|uploaded_by|integer|false|none||none|
|uploaded_at|string(date-time)|false|none||none|

<h2 id="tocS_Role">Role</h2>

<a id="schemarole"></a>
<a id="schema_Role"></a>
<a id="tocSrole"></a>
<a id="tocsrole"></a>

```json
{
  "id": 0,
  "name": "string",
  "description": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|integer|false|none||none|
|name|string|false|none||none|
|description|string|false|none||none|

<h2 id="tocS_Permission">Permission</h2>

<a id="schemapermission"></a>
<a id="schema_Permission"></a>
<a id="tocSpermission"></a>
<a id="tocspermission"></a>

```json
{
  "id": 0,
  "name": "string",
  "code": "string",
  "description": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|integer|false|none||none|
|name|string|false|none||none|
|code|string|false|none||none|
|description|string|false|none||none|

<h2 id="tocS_ErrorResponse">ErrorResponse</h2>

<a id="schemaerrorresponse"></a>
<a id="schema_ErrorResponse"></a>
<a id="tocSerrorresponse"></a>
<a id="tocserrorresponse"></a>

```json
{
  "code": 0,
  "message": "string",
  "data": {}
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none||none|
|message|string|false|none||none|
|data|object|false|none||none|

<h2 id="tocS_SuccessResponse">SuccessResponse</h2>

<a id="schemasuccessresponse"></a>
<a id="schema_SuccessResponse"></a>
<a id="tocSsuccessresponse"></a>
<a id="tocssuccessresponse"></a>

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none||none|
|message|string|false|none||none|
|data|object|false|none||none|

<h2 id="tocS_PaginatedResponse">PaginatedResponse</h2>

<a id="schemapaginatedresponse"></a>
<a id="schema_PaginatedResponse"></a>
<a id="tocSpaginatedresponse"></a>
<a id="tocspaginatedresponse"></a>

```json
{
  "code": 0,
  "message": "string",
  "data": {
    "items": [
      {}
    ],
    "total": 0,
    "page": 0,
    "page_size": 0
  }
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none||none|
|message|string|false|none||none|
|data|object|false|none||none|
|» items|[object]|false|none||none|
|» total|integer|false|none||none|
|» page|integer|false|none||none|
|» page_size|integer|false|none||none|

