"""把内部工具契约翻译成模型可用的 function schema。"""
from typing import Dict, List


def to_openai_tool(spec) -> Dict:
    """ToolSpec -> OpenAI function calling 格式。"""
    schema = spec.schema or {'type': 'object', 'properties': {}}
    # OpenAI 要求 root 必须是 object
    if schema.get('type') != 'object':
        schema = {'type': 'object', 'properties': {}}
    return {
        'type': 'function',
        'function': {
            'name': spec.name,
            'description': spec.description or spec.name,
            'parameters': schema,
        },
    }


def build_tools(registry_tools: Dict, allowed: List[str] = None) -> List[Dict]:
    """按白名单生成工具列表；allowed 为 None 表示全部。"""
    tools = []
    for name, spec in registry_tools.items():
        if allowed is not None and name not in allowed:
            continue
        tools.append(to_openai_tool(spec))
    return tools
