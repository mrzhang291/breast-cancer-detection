"""语料装载与切分。

两类语料：
    1. features.json   —— 30 条特征词典（含真实统计量）
    2. docs/*.md       —— 系统文档，按 markdown 标题切成条款
"""
import io
import json
import os
import re
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOWLEDGE_DIR = os.path.join(ROOT, 'agent', 'knowledge')
FEATURES_FILE = os.path.join(KNOWLEDGE_DIR, 'features.json')

# 参与索引的文档（存在才收录）
DOC_FILES = [
    ('STARTUP_GUIDE.md', 'DOC-STARTUP', '系统启动与功能说明'),
    ('乳腺癌检测系统 API.md', 'DOC-API', '系统接口文档'),
    ('SHAP_GUIDE.md', 'DOC-SHAP', 'SHAP 可解释性说明'),
]


def _slug(text: str, idx: int) -> str:
    cleaned = re.sub(r'\s+', '', text)[:12]
    return cleaned or str(idx)


def load_feature_chunks() -> List[Dict]:
    """特征词典 -> 条款。每条都是能独立成立的说明。"""
    if not os.path.exists(FEATURES_FILE):
        return []
    with io.open(FEATURES_FILE, encoding='utf-8') as f:
        data = json.load(f)

    chunks = []
    for item in data.get('items', []):
        st = item.get('stats', {})
        direction = ('数值越高通常越提示细胞异型性明显（统计关联，非诊断阈值）'
                     if item.get('higher_means_more_suspicious')
                     else '该特征与异型性的关联较弱，需结合其他特征判断')
        text = (
            '%s（%s）：%s。在数据集中，良性组均值约 %.4g，恶性组均值约 %.4g；'
            '良性组 5%%~95%% 区间 %.4g ~ %.4g，恶性组 %.4g ~ %.4g。%s。%s'
            % (item['name_zh'], item['feature'], item.get('meaning') or '',
               st.get('benign_mean', 0), st.get('malignant_mean', 0),
               st.get('benign_p05', 0), st.get('benign_p95', 0),
               st.get('malignant_p05', 0), st.get('malignant_p95', 0),
               direction, item.get('note', ''))
        )
        chunks.append({
            'clause_id': item['clause_id'],
            'doc_id': 'FEATURES',
            'source': item.get('source', 'features.json'),
            'version': item.get('version', ''),
            'section': item['name_zh'],
            'text': text,
            'meta': {'feature': item['feature'], 'index': item['index'],
                     'name_zh': item['name_zh']},
        })
    return chunks


def load_doc_chunks() -> List[Dict]:
    """文档 -> 按二级标题切条款。"""
    chunks: List[Dict] = []
    for filename, prefix, title in DOC_FILES:
        path = os.path.join(ROOT, filename)
        if not os.path.exists(path):
            continue
        content = io.open(path, encoding='utf-8', errors='ignore').read()
        lines = content.splitlines()

        current_title = title
        buffer: List[str] = []
        seq = 0

        def flush(section_title: str, buf: List[str]) -> None:
            nonlocal seq
            body = '\n'.join(buf).strip()
            if len(body) < 20:
                return
            seq += 1
            chunks.append({
                'clause_id': '%s-%03d' % (prefix, seq),
                'doc_id': prefix,
                'source': filename,
                'version': '2026-05',
                'section': section_title,
                'text': body[:1800],
                'meta': {'title': title},
            })

        for line in lines:
            if re.match(r'^#{2,3}\s+', line):
                flush(current_title, buffer)
                buffer = []
                current_title = re.sub(r'^#{2,3}\s+', '', line).strip()
            else:
                buffer.append(line)
        flush(current_title, buffer)
    return chunks


def all_chunks() -> List[Dict]:
    return load_feature_chunks() + load_doc_chunks()
