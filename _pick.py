import sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
from agent import uncertainty
df = pd.read_csv("Breast Cancer Data.csv")
rows = []
for _, r in df.iterrows():
    vals = [float(v) for v in r.iloc[2:32]]
    rows.append((uncertainty.mahalanobis(vals), str(r.iloc[1]).strip(), vals))
benign = sorted([x for x in rows if x[1] == "B"])[:1]
malig = sorted([x for x in rows if x[1] == "M"])[:1]
for d, label, vals in benign + malig:
    print("%s 距离 %.2f: %s" % (label, d, [round(v, 4) for v in vals]))
