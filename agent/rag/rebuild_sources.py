"""重建网络语料：重新切块、去噪、打域标签、生成中文摘要。

用法：
    python -m agent.rag.rebuild_sources          # 抓取 + 切块（不翻译）
    python -m agent.rag.rebuild_sources --translate
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, 'agent', 'knowledge', 'web')

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/120 Safari/537.36'}

# doc_id, url, 站点, 标题, 语言, 域, 来源级别, 许可
SOURCES = [
    ('WEB-WHO', 'https://www.who.int/zh/news-room/fact-sheets/detail/breast-cancer',
     'WHO 世界卫生组织', '乳腺癌实况报道', 'zh', 'MED-DISEASE', 2, 'WHO 版权声明'),
    ('WEB-WIKI-BC', 'https://zh.wikipedia.org/wiki/%E4%B9%B3%E8%85%BA%E7%99%8C',
     '维基百科', '乳腺癌', 'zh', 'MED-DISEASE', 1, 'CC BY-SA 4.0'),
    ('WEB-WIKI-HYPER', 'https://zh.wikipedia.org/wiki/%E4%B9%B3%E8%85%BA%E5%A2%9E%E7%94%9F',
     '维基百科', '乳腺增生', 'zh', 'MED-DISEASE', 1, 'CC BY-SA 4.0'),
    ('WEB-WIKI-DISCHARGE', 'https://zh.wikipedia.org/wiki/%E4%B9%B3%E5%A4%B4%E6%BA%A2%E6%B6%B2',
     '维基百科', '乳头溢液', 'zh', 'MED-DISEASE', 1, 'CC BY-SA 4.0'),
    ('WEB-WIKI-MASTITIS', 'https://zh.wikipedia.org/wiki/%E4%B9%B3%E8%85%BA%E7%82%8E',
     '维基百科', '乳腺炎', 'zh', 'MED-DISEASE', 1, 'CC BY-SA 4.0'),
    ('WEB-WIKI-TAMOX', 'https://zh.wikipedia.org/wiki/%E4%BB%96%E8%8E%AB%E6%98%94%E8%8A%AC',
     '维基百科', '他莫昔芬', 'zh', 'MED-DRUG', 1, 'CC BY-SA 4.0'),
    ('WEB-NCI-TREAT', 'https://www.cancer.gov/types/breast/hp/breast-treatment-pdq',
     '美国国家癌症研究所 NCI', 'Breast Cancer Treatment (PDQ)', 'en', 'MED-DISEASE', 3,
     '美国联邦政府作品（公有领域）'),
    ('WEB-NCI-PREV', 'https://www.cancer.gov/types/breast/hp/breast-prevention-pdq',
     '美国国家癌症研究所 NCI', 'Breast Cancer Prevention (PDQ)', 'en', 'MED-DISEASE', 3,
     '美国联邦政府作品（公有领域）'),
    ('WEB-NCI-SCREEN', 'https://www.cancer.gov/types/breast/hp/breast-screening-pdq',
     '美国国家癌症研究所 NCI', 'Breast Cancer Screening (PDQ)', 'en', 'MED-DISEASE', 3,
     '美国联邦政府作品（公有领域）'),
    ('WEB-CJCR-GUIDE',
     'http://article.cjcrcn.org/article/app/id/b2703deb-d100-4f5d-982f-423c1988572e/flg?pageType=en',
     '中国抗癌协会 / Chin J Cancer Res', '中国乳腺癌诊疗指南（2022 英文版）', 'en',
     'MED-DISEASE', 4, '开放获取（CC BY-NC）'),
    ('WEB-NHS-PAIN', 'https://www.nhs.uk/conditions/breast-pain/',
     '英国 NHS', 'Breast pain', 'en', 'MED-DISEASE', 2, 'Open Government Licence v3.0'),
    ('WEB-MLP-BC', 'https://medlineplus.gov/breastcancer.html',
     'MedlinePlus（美国国家医学图书馆）', 'Breast Cancer', 'en', 'MED-DISEASE', 2,
     '美国联邦政府作品（公有领域）'),
    ('WEB-MLP-MAMMO', 'https://medlineplus.gov/mammography.html',
     'MedlinePlus（美国国家医学图书馆）', 'Mammography', 'en', 'MED-DISEASE', 2,
     '美国联邦政府作品（公有领域）'),
]

# 噪声章节：统计、参考文献、历史人文等，对问答无用
NOISE_TITLE = re.compile(
    r'(发病率|死亡率|统计|研究|参考文献|外部链接|参见|参见|歷史|历史|文化|流行|'
    r'Incidence and Mortality|Statistics|References|See Also|History|Culture|'
    r'Journal Articles|Research|Clinical Trials)', re.I)

NOISE_BODY = re.compile(r'(参考文献|外部链接|医学主题词|MeSH|PMID|doi:)', re.I)

MIN_CHUNK = 260
MAX_CHUNK = 900


def fetch(url: str) -> str:
    resp = requests.get(url, timeout=45, headers=HEADERS)
    resp.raise_for_status()
    if resp.encoding in (None, 'ISO-8859-1'):
        resp.encoding = resp.apparent_encoding
    return resp.text


def sections_from_html(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form',
                     'iframe', 'table', 'sup', 'figure']):
        tag.decompose()
    main = (soup.find('article') or soup.find('main')
            or soup.find(id='main-content') or soup.body or soup)

    sections = []
    current = {'title': '概述', 'lines': []}
    for node in main.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'blockquote']):
        text = node.get_text(' ', strip=True)
        if not text:
            continue
        if node.name in ('h1', 'h2', 'h3', 'h4'):
            if current['lines']:
                sections.append(current)
            current = {'title': text[:80], 'lines': []}
        elif len(text) >= 20:
            current['lines'].append(text)
    if current['lines']:
        sections.append(current)
    return [s for s in sections if not NOISE_TITLE.search(s['title'])]


SENT_RE = re.compile(r'(?<=[。！？!?；;])|(?<=\.\s)')


def split_sentences(text: str) -> List[str]:
    parts = [p.strip() for p in SENT_RE.split(text) if p.strip()]
    return [p for p in parts if len(p) >= 8]


def chunk_section(text: str) -> List[str]:
    sentences = split_sentences(text)
    chunks, buf, size = [], [], 0
    for sentence in sentences:
        if size + len(sentence) > MAX_CHUNK and len(buf) >= 2:
            body = ''.join(buf).strip()
            if len(body) >= MIN_CHUNK:
                chunks.append(body)
            buf, size = [sentence], len(sentence)
        else:
            buf.append(sentence)
            size += len(sentence)
    body = ''.join(buf).strip()
    if len(body) >= MIN_CHUNK:
        chunks.append(body)
    return chunks


def build() -> Dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(OUT_DIR, '*.json')):
        os.remove(old)

    total, kept, dropped = 0, 0, 0
    seen = set()
    report = []
    for doc_id, url, site, title, lang, domain, level, license_ in SOURCES:
        try:
            html = fetch(url)
            sections = sections_from_html(html)
            draft = []
            seq = 0
            for sec in sections:
                body = '\n'.join(sec['lines']).strip()
                if NOISE_BODY.search(body[:200]):
                    continue
                for piece in chunk_section(body):
                    total += 1
                    digest = hashlib.sha1(piece[:240].encode('utf-8')).hexdigest()
                    if digest in seen:
                        dropped += 1
                        continue
                    seen.add(digest)
                    seq += 1
                    draft.append({
                        'clause_id': '%s-%03d' % (doc_id, seq),
                        'doc_id': doc_id, 'section': sec['title'], 'text': piece,
                        'source': site, 'url': url, 'title': title, 'lang': lang,
                        'domain': domain, 'level': level, 'license': license_,
                        'retrieved_at': time.strftime('%Y-%m-%d'),
                    })
            if draft:
                path = os.path.join(OUT_DIR, doc_id + '.json')
                json.dump(draft, io.open(path, 'w', encoding='utf-8'),
                          ensure_ascii=False, indent=1)
                kept += len(draft)
                report.append((doc_id, len(draft), sum(len(c['text']) for c in draft)))
                print('%-20s 块 %3d  %7d 字' % (doc_id, len(draft),
                                                sum(len(c['text']) for c in draft)))
        except Exception as exc:  # noqa: BLE001
            print('%-20s 失败 %s: %s' % (doc_id, type(exc).__name__, str(exc)[:60]))
    print('\n生成 %d 块，保留 %d，去重丢弃 %d' % (total, kept, dropped))
    return {'total': total, 'kept': kept, 'dropped': dropped}


def translate_all() -> None:
    from .translate import translate_docs
    translate_docs(OUT_DIR)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--translate', action='store_true')
    args = parser.parse_args()
    build()
    if args.translate:
        translate_all()
