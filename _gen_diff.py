import sys
sys.stdout.reconfigure(encoding="utf-8")
import reporting
items = [
    {"name": "凹点平均值", "change_pct": -91.0},
    {"name": "面积最大值", "change_pct": 62.0},
    {"name": "半径最大值", "change_pct": 48.0},
    {"name": "纹理标准差", "change_pct": 21.0},
    {"name": "对称性标准差", "change_pct": -14.0},
]
open(r"C:\Users\zcj00\乳腺癌\_chart_diff.png", "wb").write(reporting.chart_diff(items))
print("chart saved")
