"""语义缓存（轻量版）。

不做向量化：把问题归一化（去标点、去空白、小写、同义替换）后取哈希。
对本系统的高频问法（"怎么批量导入""这个结果什么意思"）命中率已经够用，
而且零依赖、可解释、不会串号（key 里带 user 维度隔离）。
"""
import hashlib
import re
from typing import Optional

from . import db

CACHE_VERSION = 'v6'

_PUNCT_RE = re.compile(r'[\s，。、；：？！,.;:?!""\'\'（）()【】\[\]<>《》~`]')
_SYNONYM = [
    ('怎么样', '如何'), ('咋办', '如何'), ('啥意思', '什么意思'),
    ('能做什么', '功能'), ('有什么用', '功能'),
]


def normalize(question: str) -> str:
    text = (question or '').strip().lower()
    for src, dst in _SYNONYM:
        text = text.replace(src, dst)
    return _PUNCT_RE.sub('', text)


def make_key(user_id, lang: str, question: str, intent: str = '') -> str:
    raw = '%s|%s|%s|%s|%s' % (CACHE_VERSION, user_id, lang, intent, normalize(question))
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def get(user_id, lang: str, question: str, intent: str = '', ttl: int = 1800) -> Optional[dict]:
    return db.cache_get(make_key(user_id, lang, question, intent), ttl=ttl)


def put(user_id, lang: str, question: str, answer_md: str,
        citations, intent: str = '') -> None:
    db.cache_put(make_key(user_id, lang, question, intent), question, answer_md, citations)
