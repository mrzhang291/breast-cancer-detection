import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent import registry
from agent.core import AgentLoop, AgentSession, Completion, FakeProvider, ToolCall

class Ctx:
    run_id='t'; user_id='3'; role_id=3; lang='zh'

c = Completion(tool_calls=[ToolCall(id='c1', name='statistics', arguments={})])
print("wants_tools:", c.wants_tools, "| calls:", c.tool_calls)
p = FakeProvider([c, Completion(content='ok')])
loop = AgentLoop(p, registry.TOOLS, Ctx(), allowed_tools=['statistics'], max_steps=3)
print("tools built:", [t["function"]["name"] for t in loop.tools])
try:
    r = loop.run(AgentSession(), "q")
    print("stopped:", r.stopped, "| steps:", r.steps, "| answer:", r.answer[:40])
except Exception as exc:
    print("异常:", type(exc).__name__, exc)
