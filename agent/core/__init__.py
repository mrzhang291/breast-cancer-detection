"""Agent 基础设施：会话、工具 schema、模型提供方、执行循环、工具呈现。

分层参考 DeepSeek Harness 的插件划分：
    session      —— 一次对话的状态（消息、预算、元数据）
    schemas      —— 把内部工具契约翻译成模型能理解的 function schema
    provider     —— 模型适配层（DeepSeek / 测试用假模型）
    loop         —— 模型 ↔ 工具 的执行循环，带步数/权限/超时约束
    presentation —— 工具调用在界面上的呈现（标签、图标、结果摘要）

设计原则与主项目一致：模型只负责"决定调什么"，执行走确定性代码；
任何模型输出都经过校验，失败可回退。
"""
from .session import AgentSession
from .provider import Completion, DeepSeekProvider, FakeProvider, ToolCall
from .loop import AgentLoop, LoopResult

__all__ = [
    'AgentSession', 'Completion', 'DeepSeekProvider', 'FakeProvider',
    'ToolCall', 'AgentLoop', 'LoopResult',
]
