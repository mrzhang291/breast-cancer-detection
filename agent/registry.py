"""工具契约层。

每个工具声明：名称、参数 schema、所需权限、超时、是否幂等。
调用方只能通过 call_tool() 进入，保证：
    - 参数先校验，非法参数不会进入模型上下文
    - 权限先判定，越权调用直接拒绝
    - 超时与异常都有确定语义（retryable / fatal）
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import policy


@dataclass
class ToolSpec:
    name: str
    fn: Callable
    description: str = ''
    schema: Dict = field(default_factory=dict)
    permission: str = 'read'
    timeout: float = 8.0
    idempotent: bool = True


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    facts: List[Dict] = field(default_factory=list)
    error: str = ''
    error_type: str = ''          # validation / permission / timeout / runtime
    latency_ms: int = 0
    artifacts: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'ok': self.ok, 'data': self.data, 'facts': self.facts,
            'error': self.error, 'error_type': self.error_type,
            'latency_ms': self.latency_ms,
            'artifacts': self.artifacts,
        }


TOOLS: Dict[str, ToolSpec] = {}


def tool(name: str, *, description: str = '', schema: Optional[Dict] = None,
         permission: str = 'read', timeout: float = 8.0, idempotent: bool = True):
    """注册一个工具。"""

    def deco(fn: Callable) -> Callable:
        TOOLS[name] = ToolSpec(
            name=name, fn=fn, description=description,
            schema=schema or {'type': 'object', 'properties': {}},
            permission=permission, timeout=timeout, idempotent=idempotent,
        )
        return fn

    return deco


# ------------------------------------------------------------ 极简 schema 校验

_TYPE_MAP = {
    'number': (int, float),
    'integer': int,
    'string': str,
    'boolean': bool,
    'array': (list, tuple),
    'object': dict,
}


def validate_schema(schema: Dict, value: Any, path: str = '$') -> List[str]:
    """返回错误列表；空列表代表通过。只支持本项目需要的子集。"""
    errors: List[str] = []
    if not schema:
        return errors

    stype = schema.get('type')
    if stype:
        expected = _TYPE_MAP.get(stype)
        if expected and not isinstance(value, expected):
            errors.append('%s: 期望 %s，实际 %s' % (path, stype, type(value).__name__))
            return errors
        if stype == 'number' and isinstance(value, bool):
            errors.append('%s: 布尔值不是数字' % path)
            return errors

    if 'enum' in schema and value not in schema['enum']:
        errors.append('%s: 必须是 %s 之一' % (path, schema['enum']))

    if stype in ('number', 'integer'):
        if 'minimum' in schema and value < schema['minimum']:
            errors.append('%s: 不能小于 %s' % (path, schema['minimum']))
        if 'maximum' in schema and value > schema['maximum']:
            errors.append('%s: 不能大于 %s' % (path, schema['maximum']))

    if stype == 'array':
        items = schema.get('items')
        if 'minItems' in schema and len(value) < schema['minItems']:
            errors.append('%s: 至少 %s 项，实际 %s 项' % (path, schema['minItems'], len(value)))
        if 'maxItems' in schema and len(value) > schema['maxItems']:
            errors.append('%s: 至多 %s 项，实际 %s 项' % (path, schema['maxItems'], len(value)))
        if items:
            for idx, item in enumerate(value):
                errors.extend(validate_schema(items, item, '%s[%d]' % (path, idx)))

    if stype == 'object':
        props = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                errors.append('%s: 缺少必填字段 %s' % (path, key))
        for key, sub in props.items():
            if key in value:
                errors.extend(validate_schema(sub, value[key], '%s.%s' % (path, key)))
    return errors


def call_tool(ctx, name: str, args: Optional[Dict] = None) -> ToolResult:
    """统一的工具调用入口。"""
    spec = TOOLS.get(name)
    if spec is None:
        return ToolResult(ok=False, error='未注册的工具: %s' % name, error_type='validation')

    args = args or {}
    errors = validate_schema(spec.schema, args)
    if errors:
        return ToolResult(ok=False, error='; '.join(errors), error_type='validation')

    if not policy.can_use_tool(ctx, spec.permission):
        return ToolResult(ok=False, error='当前角色无权调用 %s' % name, error_type='permission')

    started = time.time()
    try:
        result = spec.fn(ctx, **args)
        if isinstance(result, ToolResult):
            result.latency_ms = int((time.time() - started) * 1000)
            return result
        return ToolResult(ok=True, data=result, latency_ms=int((time.time() - started) * 1000))
    except TimeoutError:
        return ToolResult(ok=False, error='%s 执行超时' % name, error_type='timeout',
                          latency_ms=int((time.time() - started) * 1000))
    except Exception as exc:  # noqa: BLE001 - 工具内部异常必须转成确定语义
        return ToolResult(ok=False, error=str(exc), error_type='runtime',
                          latency_ms=int((time.time() - started) * 1000))


def describe_tools() -> List[Dict]:
    """给前端/调试页用的工具清单。"""
    return [
        {'name': s.name, 'description': s.description,
         'permission': s.permission, 'idempotent': s.idempotent}
        for s in TOOLS.values()
    ]


def make_fact(kind: str, payload: Dict, tool: str, run_id: str = '',
              ident: str = '') -> Dict:
    """构造统一的事实对象（唯一允许进入生成层的数据形态）。"""
    return {
        'kind': kind,
        'id': ident or '%s_%d' % (kind, int(time.time() * 1000) % 100000),
        'payload': payload,
        'provenance': {'tool': tool, 'run_id': run_id},
    }


def digest(obj: Any) -> str:
    """稳定的简短摘要，用于 trace 里标识结果。"""
    try:
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        raw = str(obj)
    import hashlib
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]
