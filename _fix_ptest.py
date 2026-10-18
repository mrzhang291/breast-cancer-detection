import io
p = r"agent\tests\test_params.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""def test_negative_rejected():
    result = params.parse_rules('最近 -3 次')
    assert not result['ok']""",
"""def test_negative_rejected():
    result = params.parse_range('最近 -3 次')
    assert result.get('ok') is False and result.get('needs_clarify')""")
io.open(p, "w", encoding="utf-8").write(s)
print("测试已修正")
