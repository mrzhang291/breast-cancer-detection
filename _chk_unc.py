import io, json, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
cfg = json.load(io.open(r"agent\knowledge\uncertainty.json", encoding="utf-8"))
x = np.array(cfg["calibration"]["x"]); y = np.array(cfg["calibration"]["y"])
print("校准曲线点数:", len(x))
print("x 范围: %.4f ~ %.4f" % (x.min(), x.max()))
for probe in [0.6, 0.8, 0.9, 0.95, 0.99, 0.999]:
    print("  raw %.3f -> calibrated %.4f" % (probe, float(np.interp(probe, x, y))))
print("阈值:", cfg["thresholds"])
print("马氏:", cfg["mahalanobis"]["d_cautious"], cfg["mahalanobis"]["d_abstain"])
