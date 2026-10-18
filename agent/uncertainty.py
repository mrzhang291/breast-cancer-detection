"""不确定性量化：校准置信度 + 分布距离 + 证据强度 -> 三档决策。

配置由 agent/knowledge/build_uncertainty.py 生成（保序回归 + 马氏距离 + 风险-覆盖率曲线）。
"""
import io
import json
import math
import os
from typing import Dict, List, Optional

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'knowledge', 'uncertainty.json')

_CACHE: Dict = {'config': None}

DEFAULT_CONFIG = {
    'calibration': {'method': 'none', 'x': [0.0, 1.0], 'y': [0.0, 1.0]},
    'thresholds': {'confident': 0.90, 'cautious': 0.60, 'malignant_margin': 0.02},
    'mahalanobis': {'mean': None, 'inv_cov': None, 'd_cautious': 1e9, 'd_abstain': 1e9},
    'risk_coverage': [],
}


def config() -> Dict:
    if _CACHE['config'] is not None:
        return _CACHE['config']
    try:
        with io.open(CONFIG_PATH, encoding='utf-8') as f:
            _CACHE['config'] = json.load(f)
    except Exception:
        _CACHE['config'] = dict(DEFAULT_CONFIG)
    return _CACHE['config']


def calibrate(raw_confidence: float) -> float:
    """保序回归校准：把模型输出映射成经验正确率。"""
    cfg = config().get('calibration') or {}
    xs, ys = cfg.get('x') or [], cfg.get('y') or []
    if len(xs) < 2:
        return float(raw_confidence)
    value = float(raw_confidence)
    if value <= xs[0]:
        return float(ys[0])
    if value >= xs[-1]:
        return float(ys[-1])
    for i in range(1, len(xs)):
        if value <= xs[i]:
            span = xs[i] - xs[i - 1]
            if span <= 0:
                return float(ys[i])
            ratio = (value - xs[i - 1]) / span
            return float(ys[i - 1] + ratio * (ys[i] - ys[i - 1]))
    return float(ys[-1])


def mahalanobis(values: List[float]) -> float:
    cfg = (config().get('mahalanobis') or {})
    mean = cfg.get('mean')
    inv_cov = cfg.get('inv_cov')
    if not mean or not inv_cov or len(values) != len(mean):
        return 0.0
    diff = [float(v) - m for v, m in zip(values, mean)]
    total = 0.0
    for i, row in enumerate(inv_cov):
        acc = 0.0
        for j, w in enumerate(row):
            acc += w * diff[j]
        total += diff[i] * acc
    return float(math.sqrt(max(total, 0.0)))


def assess(values: Optional[List[float]], confidence: float, output: str,
           evidence_score: float = 1.0) -> Dict:
    """返回三档判定与给前端画三根条用的数值。"""
    cfg = config()
    thresholds = cfg.get('thresholds') or {}
    t_conf = float(thresholds.get('confident', 0.9))
    t_caut = float(thresholds.get('cautious', 0.6))
    margin = float(thresholds.get('malignant_margin', 0.02))

    calibrated = calibrate(confidence)
    distance = mahalanobis(values) if values else 0.0
    d_caut = float((cfg.get('mahalanobis') or {}).get('d_cautious', 1e9))
    d_abst = float((cfg.get('mahalanobis') or {}).get('d_abstain', 1e9))
    distance_ratio = distance / d_abst if d_abst else 0.0

    reasons: List[str] = []
    tier = 'confident'

    if distance > d_abst:
        reasons.append('输入特征明显偏离训练分布（马氏距离 %.1f > %.1f）' % (distance, d_abst))
    if calibrated < t_caut:
        reasons.append('校准后置信度 %.3f 低于最低阈值 %.3f' % (calibrated, t_caut))
    if evidence_score < 0.05:
        reasons.append('知识库中没有可引用的依据')

    if reasons:
        tier = 'abstain'
    else:
        if distance > d_caut:
            reasons.append('输入轻度偏离训练分布（马氏距离 %.1f > %.1f）' % (distance, d_caut))
        if calibrated < t_conf:
            reasons.append('校准后置信度 %.3f 未达置信线 %.3f' % (calibrated, t_conf))
        if output == '恶性' and calibrated < t_conf + margin:
            reasons.append('恶性结论需要更高证据强度（额外 +%.2f）' % margin)
        if evidence_score < 0.15:
            reasons.append('可引用依据偏少')
        if reasons:
            tier = 'cautious'

    bars = {
        'model': round(max(0.0, min(calibrated, 1.0)), 4),
        'distribution': round(max(0.0, min(1.0 - distance_ratio, 1.0)), 4),
        'evidence': round(max(0.0, min(evidence_score, 1.0)), 4),
    }

    return {
        'tier': tier,
        'raw_confidence': round(float(confidence), 6),
        'calibrated': round(calibrated, 6),
        'mahalanobis': round(distance, 4),
        'distance_ratio': round(distance_ratio, 4),
        'evidence_score': round(float(evidence_score), 4),
        'thresholds': {'confident': t_conf, 'cautious': t_caut, 'd_cautious': d_caut,
                       'd_abstain': d_abst},
        'bars': bars,
        'reasons': reasons,
        'reason': '；'.join(reasons),
    }


TIER_LABEL = {
    'confident': '证据充分',
    'cautious': '证据有限',
    'abstain': '证据不足',
}
