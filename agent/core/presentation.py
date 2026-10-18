"""工具调用在界面上的呈现：标签、图标、结果摘要。"""
from typing import Dict

TOOL_PRESENTATION: Dict[str, Dict] = {
    'predict': {'label': '运行模型', 'icon': 'activity'},
    'explain': {'label': '特征归因', 'icon': 'bar-chart'},
    'records': {'label': '查询记录', 'icon': 'list'},
    'statistics': {'label': '统计汇总', 'icon': 'pie-chart'},
    'similar_cases': {'label': '检索相似病例', 'icon': 'users'},
    'search_knowledge': {'label': '检索知识库', 'icon': 'book'},
    'sql_query': {'label': '查询数据库', 'icon': 'database'},
    'compare_records': {'label': '对比两次记录', 'icon': 'git-compare'},
    'export_report': {'label': '生成报告', 'icon': 'file-text'},
    'export_data': {'label': '导出数据', 'icon': 'download'},
}


def describe(tool_name: str) -> Dict:
    meta = TOOL_PRESENTATION.get(tool_name) or {}
    return {'name': tool_name,
            'label': meta.get('label') or tool_name,
            'icon': meta.get('icon') or 'tool'}


def summarize(step: Dict) -> str:
    """一句话说明这步干了什么，用于侧栏时间线。"""
    name = step.get('tool') or ''
    label = describe(name)['label']
    if not step.get('ok', True):
        return '%s：失败（%s）' % (label, step.get('verdict') or 'error')
    latency = step.get('latency_ms')
    suffix = '（%d ms）' % latency if isinstance(latency, int) else ''
    return '%s%s' % (label, suffix)
