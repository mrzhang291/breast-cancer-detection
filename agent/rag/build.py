"""建索引：python -m agent.rag.build"""
import os
import sys

from . import index


def main() -> int:
    result = index.rebuild()
    if os.environ.get('RAG_BUILD_VECTORS') == '1':
        try:
            from . import embed
            vec = embed.build()
            print('向量索引: %d 条（%s）' % (vec['vectors'], vec['model']))
        except Exception as exc:  # noqa: BLE001
            print('向量索引失败（降级为词法检索）:', str(exc)[:120])
    st = index.stats()
    print('索引重建完成: 条款 %d 条, 倒排词条 %d 行' % (result['chunks'], result['terms']))

    probes = ['半径平均值', '怎么批量导入', 'SHAP 是什么', '置信度', '乳腺']
    for probe in probes:
        hits = index.search(probe, k=3)
        print('\n[%s] -> %d 条' % (probe, len(hits)))
        for hit in hits:
            print('   %-14s %-24s %.3f  %s' % (
                hit['clause_id'], hit['section'][:20], hit['score'],
                hit['text'][:46].replace('\n', ' ')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
