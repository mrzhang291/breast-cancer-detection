"""一次 agent run 的上下文对象。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentContext:
    """贯穿一次 run 的上下文。

    user_id / role_id 用于行级权限；facts 收集所有工具返回值；
    steps 记录每一步，便于落库与回放。
    """

    user_id: Any = 0
    role_id: int = 3
    lang: str = 'zh'
    run_id: str = ''
    question: str = ''
    intent: str = ''
    facts: List[Dict] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    steps: List[Dict] = field(default_factory=list)

    def add_fact(self, fact: Dict) -> Dict:
        self.facts.append(fact)
        return fact

    def add_citation(self, clause_id: str) -> None:
        if clause_id and clause_id not in self.citations:
            self.citations.append(clause_id)

    def add_step(self, **kwargs) -> Dict:
        kwargs.setdefault('seq', len(self.steps) + 1)
        self.steps.append(kwargs)
        return kwargs
