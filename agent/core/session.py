"""会话状态：消息历史、预算与元数据。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentSession:
    """一次 agent 对话。消息格式与 OpenAI chat 兼容。"""

    run_id: str = ''
    user_id: Any = 0
    role_id: int = 3
    lang: str = 'zh'
    messages: List[Dict] = field(default_factory=list)
    max_steps: int = 6
    max_tokens: int = 1200
    meta: Dict = field(default_factory=dict)

    def system(self, text: str) -> 'AgentSession':
        if not self.messages or self.messages[0].get('role') != 'system':
            self.messages.insert(0, {'role': 'system', 'content': text})
        else:
            self.messages[0]['content'] = text
        return self

    def user(self, text: str) -> 'AgentSession':
        self.messages.append({'role': 'user', 'content': text})
        return self

    def assistant(self, content: str = '', tool_calls=None) -> 'AgentSession':
        message = {'role': 'assistant', 'content': content or ''}
        if tool_calls:
            message['tool_calls'] = [call.to_message() for call in tool_calls]
        self.messages.append(message)
        return self

    def tool(self, call_id: str, name: str, content: str) -> 'AgentSession':
        self.messages.append({
            'role': 'tool',
            'tool_call_id': call_id,
            'name': name,
            'content': content,
        })
        return self

    def tail(self, limit: int = 12) -> List[Dict]:
        return self.messages[-limit:]
