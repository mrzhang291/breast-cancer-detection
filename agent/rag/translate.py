"""给英文语料生成中文标题与摘要，供中文检索使用。"""
import json
import os
from typing import Dict, List

import requests

API = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
BATCH = 20

SYSTEM = ('你是医学语料整理助手。给定英文乳腺癌资料的章节片段，输出中文标题与 60 字以内中文摘要。'
          '只输出 JSON 数组，不要解释。格式：[{"id":"...","title_zh":"...","summary_zh":"..."}]')


def _key() -> str:
    return os.environ.get('DEEPSEEK_API_KEY', '').strip()


def _translate(batch: List[Dict]) -> List[Dict]:
    payload = [{'id': c['clause_id'], 'title': c['section'], 'text': c['text'][:700]}
               for c in batch]
    resp = requests.post(API, headers={'Authorization': 'Bearer ' + _key(),
                                       'Content-Type': 'application/json'},
                         json={'model': MODEL, 'temperature': 0.1, 'max_tokens': 2200,
                               'messages': [
                                   {'role': 'system', 'content': SYSTEM},
                                   {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
                               ]}, timeout=120)
    resp.raise_for_status()
    content = resp.json()['choices'][0]['message']['content']
    start, end = content.find('['), content.rfind(']')
    if start < 0 or end < start:
        raise ValueError('no json array')
    return json.loads(content[start:end + 1])


def translate_docs(out_dir: str) -> None:
    if not _key():
        print('!! 未设置 DEEPSEEK_API_KEY，跳过翻译')
        return
    for name in sorted(os.listdir(out_dir)):
        if not name.endswith('.json'):
            continue
        path = os.path.join(out_dir, name)
        data = json.load(open(path, encoding='utf-8'))
        if not data or data[0].get('lang') != 'en':
            continue
        pending = [c for c in data if not c.get('summary_zh')]
        if not pending:
            continue
        print('翻译 %-22s %d 块' % (name, len(pending)))
        for i in range(0, len(pending), BATCH):
            batch = pending[i:i + BATCH]
            for attempt in range(3):
                try:
                    result = _translate(batch)
                    mapping = {item['id']: item for item in result if item.get('id')}
                    for chunk in batch:
                        item = mapping.get(chunk['clause_id'], {})
                        chunk['section_zh'] = (item.get('title_zh') or chunk['section'])[:60]
                        chunk['summary_zh'] = (item.get('summary_zh') or '')[:160]
                    break
                except Exception as exc:  # noqa: BLE001
                    print('   批次失败(%d/3): %s' % (attempt + 1, str(exc)[:60]))
                    time_sleep(2)
            json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('  进度 %d/%d' % (min(i + BATCH, len(pending)), len(pending)))


def time_sleep(seconds: float) -> None:
    import time
    time.sleep(seconds)
