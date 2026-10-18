"""子代理：把只读分析子任务交给受限的子循环执行。

参考 DSH 的 subagent 设计：
    - 子代理有独立的系统提示词与工具白名单
    - 步数更少（避免主循环被拖长）
    - 不允许再委派（白名单里没有 delegate），天然防递归
    - 结果收敛成一段文本回给主循环，主循环继续决策
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .loop import AgentLoop
from .provider import DeepSeekProvider
from .session import AgentSession


@dataclass
class SubAgentSpec:
    name: str
    instructions: str
    allowed_tools: List[str] = field(default_factory=list)
    max_steps: int = 3


ANALYST = SubAgentSpec(
    name='analyst',
    instructions=(
        '你是数据分析子代理。只做只读分析：查记录、算统计、检索知识库、解释特征。\n'
        '不要编造数字，所有结论必须来自工具结果。不要生成文件。\n'
        '用中文回答，先给结论，再给 1-3 条依据，总长度不超过 400 字。'
    ),
    allowed_tools=['records', 'statistics', 'search_knowledge', 'predict', 'explain'],
    max_steps=3,
)

SPECS: Dict[str, SubAgentSpec] = {spec.name: spec for spec in (ANALYST,)}


def run_subagent(task: str, ctx, spec: Optional[SubAgentSpec] = None,
                 provider=None, emit: Optional[Callable] = None) -> Dict:
    """执行一次子代理任务，返回 {ok, answer, steps, stopped}。"""
    spec = spec or ANALYST
    provider = provider or DeepSeekProvider()
    if not provider.available():
        return {'ok': False, 'answer': 'LLM 不可用，子代理无法执行', 'steps': [],
                'stopped': 'unavailable'}

    from .. import registry

    session = AgentSession(run_id=getattr(ctx, 'run_id', ''),
                           user_id=getattr(ctx, 'user_id', 0),
                           role_id=getattr(ctx, 'role_id', 3),
                           max_steps=spec.max_steps)
    session.system(spec.instructions)

    loop = AgentLoop(provider, registry.TOOLS, ctx,
                     allowed_tools=spec.allowed_tools,
                     max_steps=spec.max_steps, emit=emit)
    result = loop.run(session, task)
    return {'ok': result.stopped == 'answer',
            'answer': result.answer,
            'steps': result.steps,
            'stopped': result.stopped,
            'usage': result.usage,
            'spec': spec.name}
