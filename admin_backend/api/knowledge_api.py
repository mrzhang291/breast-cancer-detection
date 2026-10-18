"""管理端：上传 RAG 知识库文件 → 切片 → 重建索引。"""
import io
import json
import os
import re
import sys
import time
from typing import Dict, List

import jwt as pyjwt
from flask import Blueprint, current_app, jsonify, render_template, request

from auth import get_token_from_request

knowledge_api = Blueprint('knowledge_api', __name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_DIR = os.path.join(ROOT, 'agent', 'knowledge', 'web')
ALLOWED_DOMAIN = {'MED-DISEASE', 'MED-DRUG', 'SYS', 'FEAT'}
MIN_CHUNK = 120
MAX_CHUNK = 240


def _auth_ok() -> bool:
    token = get_token_from_request()
    if not token:
        return False
    try:
        decoded = pyjwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return decoded.get('sub') is not None
    except Exception:  # noqa: BLE001
        return False


def _extract(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith('.pdf'):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return '\n'.join((page.extract_text() or '') for page in reader.pages)
    if lower.endswith(('.txt', '.md')):
        for enc in ('utf-8', 'gb18030'):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode('utf-8', 'ignore')
    raise ValueError('只支持 PDF / TXT / Markdown')


SENT_RE = re.compile(r'(?<=[。！？!?；;])|(?<=\.\s)')


def _chunk(text: str) -> List[str]:
    text = re.sub(r'[ \t]+', ' ', text)
    paragraphs = [p.strip() for p in text.splitlines() if len(p.strip()) >= 12]
    sentences = []
    for para in paragraphs:
        sentences.extend(s for s in SENT_RE.split(para) if s.strip())
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


def _save(title: str, source: str, domain: str, text: str) -> Dict:
    stamp = time.strftime('%Y%m%d%H%M%S')
    doc_id = 'UPLOAD-%s' % stamp
    pieces = _chunk(text)
    if not pieces:
        raise ValueError('没有解析到足够正文（可能 PDF 是扫描件）')
    items = []
    for i, piece in enumerate(pieces, 1):
        items.append({
            'clause_id': '%s-%03d' % (doc_id, i),
            'doc_id': doc_id, 'section': title, 'text': piece,
            'source': source or '管理端上传', 'url': '', 'title': title,
            'lang': 'zh' if len(re.findall(r'[\u4e00-\u9fff]', piece)) > 10 else 'en',
            'domain': domain, 'level': 2, 'license': '内部上传',
            'retrieved_at': time.strftime('%Y-%m-%d'),
        })
    os.makedirs(WEB_DIR, exist_ok=True)
    path = os.path.join(WEB_DIR, doc_id + '.json')
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(items, fh, ensure_ascii=False, indent=1)
    return {'doc_id': doc_id, 'chunks': len(items), 'path': path}


@knowledge_api.route('/knowledge')
def knowledge_page():
    return render_template('admin_knowledge.html')


@knowledge_api.route('/api/knowledge/upload', methods=['POST'])
def upload_knowledge():
    if not _auth_ok():
        return jsonify({'ok': False, 'error': '请先登录'}), 401
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({'ok': False, 'error': '缺少文件'}), 400
    data = upload.read()
    if len(data) > 20 * 1024 * 1024:
        return jsonify({'ok': False, 'error': '文件不能超过 20MB'}), 400

    title = (request.form.get('title') or os.path.splitext(upload.filename)[0]).strip()[:80]
    domain = (request.form.get('domain') or 'MED-DISEASE').strip()
    if domain not in ALLOWED_DOMAIN:
        return jsonify({'ok': False, 'error': '域不合法'}), 400
    source = (request.form.get('source') or '管理端上传').strip()[:60]

    try:
        text = _extract(upload.filename, data)
        saved = _save(title, source, domain, text)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': '解析失败：%s' % str(exc)[:120]}), 500

    try:
        sys.path.insert(0, ROOT)
        from agent.rag import index
        stats = index.rebuild()
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': '已保存，但索引重建失败：%s' % str(exc)[:120],
                        'doc_id': saved['doc_id'], 'chunks': saved['chunks']}), 500

    return jsonify({'ok': True, 'doc_id': saved['doc_id'], 'chunks': saved['chunks'],
                    'total': stats.get('chunks'), 'terms': stats.get('terms'),
                    'domain': domain, 'title': title})


@knowledge_api.route('/api/knowledge/uploads', methods=['GET'])
def list_uploads():
    if not _auth_ok():
        return jsonify({'ok': False, 'error': '请先登录'}), 401
    docs = []
    if os.path.isdir(WEB_DIR):
        for name in sorted(os.listdir(WEB_DIR), reverse=True):
            if not (name.startswith('UPLOAD-') and name.endswith('.json')):
                continue
            path = os.path.join(WEB_DIR, name)
            try:
                data = json.load(io.open(path, encoding='utf-8'))
            except Exception:  # noqa: BLE001
                continue
            if not data:
                continue
            docs.append({
                'doc_id': data[0].get('doc_id', name[:-5]),
                'title': data[0].get('title', ''),
                'domain': data[0].get('domain', ''),
                'chunks': len(data),
                'retrieved_at': data[0].get('retrieved_at', ''),
            })
    return jsonify({'ok': True, 'uploads': docs})


@knowledge_api.route('/api/knowledge/rebuild', methods=['POST'])
def rebuild_index():
    if not _auth_ok():
        return jsonify({'ok': False, 'error': '请先登录'}), 401
    try:
        sys.path.insert(0, ROOT)
        from agent.rag import index
        stats = index.rebuild()
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(exc)[:160]}), 500
    return jsonify({'ok': True, 'total': stats.get('chunks'), 'terms': stats.get('terms')})
