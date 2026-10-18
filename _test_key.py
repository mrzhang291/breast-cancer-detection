import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from agent.core import DeepSeekProvider, Completion

p = DeepSeekProvider()
print("可用:", p.available())
t0 = time.time()
c = p.complete([{"role": "user", "content": "只回答两个字：你好"}], max_tokens=20)
print("耗时 %.1fs | 内容: %r | usage: %s" % (time.time()-t0, c.content[:40], c.usage))
