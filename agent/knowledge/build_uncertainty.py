"""生成不确定性配置：保序回归校准 + 马氏距离阈值 + 风险-覆盖率曲线。

产物：agent/knowledge/uncertainty.json
"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(ROOT, 'Breast Cancer Data.csv')
OUT = os.path.join(ROOT, 'agent', 'knowledge', 'uncertainty.json')


def main() -> None:
    df = pd.read_csv(CSV)
    X = df.iloc[:, 2:32].values.astype(float)
    y = (df.iloc[:, 1].astype(str).str.strip() == 'M').astype(int).values

    # ---- 1. 5 折 OOF 置信度 ----
    raw_conf = np.zeros(len(y))
    correct = np.zeros(len(y))
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for train_idx, val_idx in skf.split(X, y):
        clf = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42, n_jobs=1)
        clf.fit(X[train_idx], y[train_idx])
        proba = clf.predict_proba(X[val_idx])
        pred = proba.argmax(axis=1)
        raw_conf[val_idx] = proba.max(axis=1)
        correct[val_idx] = (pred == y[val_idx]).astype(int)

    # ---- 2. 保序回归校准 ----
    iso = IsotonicRegression(out_of_bounds='clip', y_min=0.0, y_max=1.0)
    iso.fit(raw_conf, correct)
    cal_conf = iso.predict(raw_conf)

    # ---- 3. 风险-覆盖率曲线 ----
    order = np.argsort(-cal_conf)
    sorted_conf = cal_conf[order]
    sorted_correct = correct[order]
    curve = []
    for coverage in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0):
        k = max(1, int(len(y) * coverage))
        acc = float(sorted_correct[:k].mean())
        curve.append({'coverage': coverage, 'accuracy': round(acc, 4),
                      'threshold': round(float(sorted_conf[k - 1]), 4)})

    def threshold_for(target_acc: float) -> float:
        # 取「仍能满足目标准确率」的最大覆盖点，即最宽松的那个阈值
        best = None
        for k in range(10, len(y) + 1, 10):
            if float(sorted_correct[:k].mean()) >= target_acc:
                best = float(sorted_conf[k - 1])
        return best if best is not None else 0.9

    t_confident = threshold_for(0.98)
    t_cautious = threshold_for(0.95)
    # 保证两档有序，且 cautious 明显更宽松
    if t_cautious >= t_confident:
        t_cautious = max(0.30, t_confident - 0.25)

    # ---- 4. 马氏距离 ----
    mu = X.mean(axis=0)
    cov = np.cov(X.T)
    inv_cov = np.linalg.pinv(cov)
    diff = X - mu
    d2 = np.einsum('ij,jk,ik->i', diff, inv_cov, diff)
    dist = np.sqrt(np.maximum(d2, 0))
    d_caution = float(np.percentile(dist, 98))
    d_abstain = float(np.percentile(dist, 99.5))

    payload = {
        'version': '2026-10',
        'source': 'Breast Cancer Data.csv (OOF 5-fold)',
        'calibration': {
            'method': 'isotonic',
            'x': [round(float(v), 6) for v in iso.X_thresholds_],
            'y': [round(float(v), 6) for v in iso.y_thresholds_],
        },
        'thresholds': {
            'confident': round(t_confident, 4),
            'cautious': round(t_cautious, 4),
            'malignant_margin': 0.02,
        },
        'mahalanobis': {
            'mean': [round(float(v), 6) for v in mu],
            'inv_cov': [[round(float(v), 10) for v in row] for row in inv_cov],
            'd_cautious': round(d_caution, 4),
            'd_abstain': round(d_abstain, 4),
        },
        'risk_coverage': curve,
        'oof_accuracy': round(float(correct.mean()), 4),
        'oof_mean_confidence_raw': round(float(raw_conf.mean()), 4),
        'oof_mean_confidence_calibrated': round(float(cal_conf.mean()), 4),
    }

    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print('OOF 准确率        : %.4f' % payload['oof_accuracy'])
    print('原始平均置信度    : %.4f' % payload['oof_mean_confidence_raw'])
    print('校准后平均置信度  : %.4f' % payload['oof_mean_confidence_calibrated'])
    print('confident 阈值    : %.4f' % t_confident)
    print('cautious 阈值     : %.4f' % t_cautious)
    print('马氏距离 P95/P99  : %.2f / %.2f' % (d_caution, d_abstain))
    print('风险-覆盖率曲线   :')
    for point in curve:
        print('   覆盖 %.0f%% -> 准确率 %.4f (阈值 %.4f)' % (
            point['coverage'] * 100, point['accuracy'], point['threshold']))
    print('已写出:', OUT)


if __name__ == '__main__':
    main()
