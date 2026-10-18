import io, sys
sys.stdout.reconfigure(encoding="utf-8")
p = r"agent\tests\test_streaming.py"
s = io.open(p, encoding="utf-8").read()
if "test_extract_sub_steps" not in s:
    s += '''

def test_extract_sub_steps():
    from agent.core.streaming import _extract_sub_steps

    output = '{"answer": "ok", "steps": [{"tool": "statistics", "ok": true, "latency_ms": 12}]}'
    steps = _extract_sub_steps(output)
    assert steps and steps[0]["tool"] == "statistics"
    assert steps[0]["label"] == "statistics"
    assert _extract_sub_steps("not json") == []
'''
    io.open(p, "w", encoding="utf-8").write(s)
print("测试已补充")
