"""生成 agent/knowledge/features.json。

数据来源：Breast Cancer Data.csv 的实际统计量（良性组/恶性组均值与分位区间）。
这样"这个值算不算高"就有客观依据，而不是让模型瞎猜。
"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(ROOT, 'Breast Cancer Data.csv')
OUT_DIR = os.path.join(ROOT, 'agent', 'knowledge')
OUT = os.path.join(OUT_DIR, 'features.json')

ZH = {
    'radius_mean': ('半径平均值', '细胞核半径的平均值'),
    'texture_mean': ('纹理平均值', '细胞核灰度纹理的标准差，反映纹理粗糙程度'),
    'perimeter_mean': ('周长平均值', '细胞核周长的平均值'),
    'area_mean': ('面积平均值', '细胞核面积的平均值'),
    'smoothness_mean': ('平滑度平均值', '半径长度的局部变化，值越小越平滑'),
    'compactness_mean': ('紧凑度平均值', '周长平方与面积之比，反映形状不规则程度'),
    'concavity_mean': ('凹度平均值', '轮廓凹陷部分的严重程度'),
    'concave points_mean': ('凹点平均值', '轮廓凹陷点的数量'),
    'symmetry_mean': ('对称性平均值', '细胞核形状的对称程度'),
    'fractal_dimension_mean': ('分形维数平均值', '轮廓的分形维数，反映边界复杂度'),
    'radius_se': ('半径标准差', '半径的标准误差'),
    'texture_se': ('纹理标准差', '灰度纹理的标准误差'),
    'perimeter_se': ('周长标准差', '周长的标准误差'),
    'area_se': ('面积标准差', '面积的标准误差'),
    'smoothness_se': ('平滑度标准差', '平滑度的标准误差'),
    'compactness_se': ('紧凑度标准差', '紧凑度的标准误差'),
    'concavity_se': ('凹度标准差', '凹度的标准误差'),
    'concave points_se': ('凹点标准差', '凹点的标准误差'),
    'symmetry_se': ('对称性标准差', '对称性的标准误差'),
    'fractal_dimension_se': ('分形维数标准差', '分形维数的标准误差'),
    'radius_worst': ('半径最大值', '最大半径（最差/最大细胞核）'),
    'texture_worst': ('纹理最大值', '最大纹理值'),
    'perimeter_worst': ('周长最大值', '最大周长'),
    'area_worst': ('面积最大值', '最大面积'),
    'smoothness_worst': ('平滑度最大值', '最大平滑度'),
    'compactness_worst': ('紧凑度最大值', '最大紧凑度'),
    'concavity_worst': ('凹度最大值', '最大凹度'),
    'concave points_worst': ('凹点最大值', '最大凹点数'),
    'symmetry_worst': ('对称性最大值', '最大对称性'),
    'fractal_dimension_worst': ('分形维数最大值', '最大分形维数'),
}

# 高值通常提示细胞异型性更明显（仅统计关联，非诊断阈值）
HIGHER_IS_MORE_SUSPICIOUS = {
    'radius_mean', 'perimeter_mean', 'area_mean', 'concavity_mean',
    'concave points_mean', 'compactness_mean', 'radius_worst', 'perimeter_worst',
    'area_worst', 'concavity_worst', 'concave points_worst', 'compactness_worst',
    'radius_se', 'perimeter_se', 'area_se', 'concavity_se',
    'concave points_se', 'compactness_se',
}


def main() -> None:
    df = pd.read_csv(CSV)
    cols = list(df.columns)
    feature_cols = cols[2:32]
    diagnosis = df.iloc[:, 1].astype(str).str.strip()

    benign = df[diagnosis == 'B']
    malignant = df[diagnosis == 'M']

    print('样本: 总 %d / 良性 %d / 恶性 %d' % (len(df), len(benign), len(malignant)))

    items = []
    for idx, name in enumerate(feature_cols, start=1):
        zh_name, meaning = ZH.get(name, (name, ''))
        b_vals = benign[name].astype(float)
        m_vals = malignant[name].astype(float)
        all_vals = df[name].astype(float)

        higher = name in HIGHER_IS_MORE_SUSPICIOUS
        items.append({
            'clause_id': 'FEAT-%03d' % idx,
            'index': idx,
            'feature': name,
            'name_zh': zh_name,
            'name_en': name.replace('_', ' '),
            'meaning': meaning,
            'higher_means_more_suspicious': higher,
            'stats': {
                'benign_mean': round(float(b_vals.mean()), 4),
                'malignant_mean': round(float(m_vals.mean()), 4),
                'benign_p05': round(float(np.percentile(b_vals, 5)), 4),
                'benign_p95': round(float(np.percentile(b_vals, 95)), 4),
                'malignant_p05': round(float(np.percentile(m_vals, 5)), 4),
                'malignant_p95': round(float(np.percentile(m_vals, 95)), 4),
                'overall_min': round(float(all_vals.min()), 4),
                'overall_max': round(float(all_vals.max()), 4),
            },
            'source': 'Breast Cancer Data.csv（Wisconsin 诊断数据集）统计',
            'version': '2026-10',
            'note': '区间为该组 5%~95% 分位范围，属统计描述，不是诊断阈值。',
        })

    os.makedirs(OUT_DIR, exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'items': items, 'count': len(items),
                   'generated_from': 'Breast Cancer Data.csv'}, f,
                  ensure_ascii=False, indent=2)
    print('已写出:', OUT, '共', len(items), '条')


if __name__ == '__main__':
    main()
