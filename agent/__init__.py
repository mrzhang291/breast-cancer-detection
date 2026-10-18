"""Agent 层。

结构：
    context.py     AgentContext —— 一次 run 的上下文
    db.py          agent.db（run / step / 语料 / 缓存 / 反馈）
    registry.py    工具契约（@tool 装饰器、参数校验、权限、超时）
    runtime.py     由 app.py 注入的底层能力（预测/解释/记录/统计）
    tools/         具体工具
    rag/           语料切分与检索
    orchestrator.py 状态机
    policy.py      医疗护栏
    verify.py      claim ↔ fact 对账
    llm.py         大模型适配（可离线降级）
"""

__version__ = '1.0.0'
