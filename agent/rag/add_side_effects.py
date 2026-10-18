"""补充副作用语料（只新增，不动已有文件）。"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.stdout.reconfigure(encoding='utf-8')

from agent.rag import rebuild_sources as rb  # noqa: E402

EXTRA = [
    ('WEB-NCI-SIDE', 'https://www.cancer.gov/about-cancer/treatment/side-effects',
     '美国国家癌症研究所 NCI', 'Cancer Treatment Side Effects', 'en',
     'MED-DISEASE', 3, '美国联邦政府作品（公有领域）'),
    ('WEB-MLP-CHEMO', 'https://medlineplus.gov/cancerchemotherapy.html',
     'MedlinePlus（美国国家医学图书馆）', 'Cancer Chemotherapy', 'en',
     'MED-DISEASE', 2, '美国联邦政府作品（公有领域）'),
    ('WEB-NHS-CHEMO-SE', 'https://www.nhs.uk/conditions/chemotherapy/side-effects/',
     '英国 NHS', 'Side effects of chemotherapy', 'en',
     'MED-DISEASE', 2, 'Open Government Licence v3.0'),
]

OUT = rb.OUT_DIR
for doc_id, url, site, title, lang, domain, level, license_ in EXTRA:
    path = os.path.join(OUT, doc_id + '.json')
    if os.path.exists(path):
        print('%-18s 已存在' % doc_id)
        continue
    try:
        html = rb.fetch(url)
        sections = rb.sections_from_html(html)
        draft, seq = [], 0
        for sec in sections:
            body = '\n'.join(sec['lines']).strip()
            if rb.NOISE_BODY.search(body[:200]):
                continue
            for piece in rb.chunk_section(body):
                seq += 1
                draft.append({
                    'clause_id': '%s-%03d' % (doc_id, seq), 'doc_id': doc_id,
                    'section': sec['title'], 'text': piece, 'source': site,
                    'url': url, 'title': title, 'lang': lang, 'domain': domain,
                    'level': level, 'license': license_,
                    'retrieved_at': time.strftime('%Y-%m-%d'),
                })
        json.dump(draft, io.open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('%-18s 块 %3d  %6d 字' % (doc_id, len(draft),
                                        sum(len(c['text']) for c in draft)))
    except Exception as exc:  # noqa: BLE001
        print('%-18s 失败 %s: %s' % (doc_id, type(exc).__name__, str(exc)[:60]))
