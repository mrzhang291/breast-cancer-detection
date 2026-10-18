import sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
from agent import uncertainty
sample = [14.1,20.4,91.0,608.0,0.102,0.091,0.052,0.033,0.181,0.062,
          0.323,1.32,2.28,29.4,0.007,0.04,0.02,0.01,0.19,0.06,
          18.7,25.5,121.0,700.0,0.142,0.21,0.16,0.08,0.28,0.08]
print("示例数据马氏距离:", round(uncertainty.mahalanobis(sample), 2))
import pandas as pd, numpy as np
df = pd.read_csv("Breast Cancer Data.csv")
X = df.iloc[:, 2:32].values
ds = [uncertainty.mahalanobis(list(map(float, row))) for row in X[:200]]
print("数据集前200条距离: 中位 %.2f 最大 %.2f" % (np.median(ds), max(ds)))
cfgo = uncertainty.config()["mahalanobis"]
print("阈值: P98=%.2f P99.5=%.2f" % (cfgo["d_cautious"], cfgo["d_abstain"]))
