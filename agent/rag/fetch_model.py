"""下载/缓存中文嵌入模型（hf-mirror 镜像，避免依赖 HuggingFace 直连）。"""
import os
import sys

import requests

MODEL_REPO = 'Qdrant/bge-small-zh-v1.5'
MIRROR = os.environ.get('RAG_MODEL_MIRROR', 'https://hf-mirror.com')
FILES = ['config.json', 'tokenizer.json', 'tokenizer_config.json',
         'special_tokens_map.json', 'model_optimized.onnx']
CACHE_DIR = os.environ.get(
    'RAG_MODEL_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 '.model_cache', 'bge-small-zh'))


def ensure_model(verbose: bool = False) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    for name in FILES:
        path = os.path.join(CACHE_DIR, name)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            continue
        url = '%s/%s/resolve/main/%s' % (MIRROR, MODEL_REPO, name)
        if verbose:
            print('下载模型文件:', name, flush=True)
        tmp = path + '.part'
        with requests.get(url, stream=True, timeout=120,
                          headers={'User-Agent': 'Mozilla/5.0'}) as resp:
            resp.raise_for_status()
            with open(tmp, 'wb') as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
        os.replace(tmp, path)
        if verbose:
            print('  -> %s (%.1f MB)' % (name, os.path.getsize(path) / 1048576), flush=True)
    return CACHE_DIR


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(ensure_model(verbose=True))
