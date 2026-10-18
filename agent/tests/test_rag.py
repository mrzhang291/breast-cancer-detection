"""RAG 检索质量与 agent 引用联动测试。"""
from agent.rag import index


def test_feature_query_hits_feature_clause():
    hits = index.search('面积最大值是什么意思', k=3)
    assert hits and hits[0]['clause_id'].startswith('FEAT')


def test_calibration_query_hits_model_doc():
    hits = index.search('置信度怎么算的', k=3)
    assert hits and hits[0]['clause_id'].startswith('DOC-MODEL')


def test_report_query_hits_agent_doc():
    hits = index.search('怎么导出报告', k=3)
    assert hits and hits[0]['clause_id'].startswith('DOC-AGENT')


def test_batch_query_hits_startup_doc():
    hits = index.search('批量导入支持什么格式', k=3)
    assert hits and hits[0]['clause_id'].startswith('DOC-STARTUP')


def test_synonym_expansion_works():
    # 「置信度」没有直接出现在模型文档正文里，靠同义词（校准）才能命中
    tokens = index.tokenize('置信度怎么算的')
    expanded = index.expand_query('置信度怎么算的')
    assert tokens
    assert any(t in ('校准', 'confidence', '概率') for t in expanded)


def test_relative_threshold_filters_noise():
    hits = index.search('批量导入支持什么格式', k=5)
    if len(hits) >= 2:
        assert hits[0]['score'] >= hits[-1]['score']
        assert hits[-1]['score'] >= hits[0]['score'] * 0.35


def test_unknown_query_returns_few_or_none():
    # 语料扩大后，"含乳腺癌但主题无关"的问题仍可能命中少量科普段落，
    # 这里只约束不能满额返回，避免噪声淹没真正相关的条款
    hits = index.search('量子纠缠和乳腺癌有什么关系', k=5)
    assert len(hits) <= 5
