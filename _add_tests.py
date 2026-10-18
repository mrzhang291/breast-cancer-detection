import io, sys
sys.stdout.reconfigure(encoding="utf-8")

# 1) conftest: 让假记录带上 30 维特征，便于多步任务测试
p = r"agent\tests\conftest.py"
s = io.open(p, encoding="utf-8").read()
old = """def _fake_records(user_id, page, size):
    return {'total': 2, 'items': [
        {'id': 1, 'prediction_result': 'Malignant', 'confidence': 0.99,
         'created_at': '2026-05-18 10:00:00'},
        {'id': 2, 'prediction_result': 'Benign', 'confidence': 0.91,
         'created_at': '2026-05-18 11:00:00'},
    ]}"""
new = """def _fake_records(user_id, page, size):
    feats = {'feature_%d' % i: v for i, v in enumerate(FEATURES, start=1)}
    return {'total': 2, 'items': [
        {'id': 1, 'prediction_result': 'Malignant', 'confidence': 0.99,
         'created_at': '2026-05-18 10:00:00', 'features': dict(feats)},
        {'id': 2, 'prediction_result': 'Benign', 'confidence': 0.91,
         'created_at': '2026-05-18 11:00:00', 'features': dict(feats)},
    ]}"""
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("[ok] conftest 假记录已带特征")

# 2) 追加新功能测试
tests = '''


# ---------------------------------------------------------------- 新意图

def test_sql_intent(ctx):
    from agent import orchestrator
    result = orchestrator.run(ctx, '恶性病例的平均面积比良性高多少')
    assert result['intent'] == 'data_query'
    assert 'sql_query' in [s.get('tool') for s in result['steps']]
    assert '```sql' in result['answer_md']


def test_sql_plan_is_readonly():
    from agent.tools import sql
    statement, _ = sql.plan_sql('恶性病例的平均面积')
    validated = sql.validate_sql(statement)
    assert validated.lower().startswith('select')

    import pytest
    with pytest.raises(ValueError):
        sql.validate_sql('DELETE FROM prediction_records')
    with pytest.raises(ValueError):
        sql.validate_sql('SELECT * FROM secret_table')


def test_task_intent_multi_step(ctx):
    from agent import orchestrator
    result = orchestrator.run(ctx, '把最近 2 条记录逐条解释')
    assert result['intent'] == 'multi_step_task'
    assert '任务结果' in result['answer_md']
    tools = [s.get('tool') for s in result['steps']]
    assert tools.count('predict') >= 1


def test_inspect_scans_records(ctx):
    """巡检逻辑本身（不经过 HTTP）。"""
    from agent import uncertainty
    assert uncertainty.calibrate(0.999) > 0.9
'''
p2 = r"agent\tests\test_agent.py"
s2 = io.open(p2, encoding="utf-8").read()
s2 += tests
io.open(p2, "w", encoding="utf-8").write(s2)
print("[ok] 新增测试")
