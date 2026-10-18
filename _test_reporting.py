import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import reporting

c1 = reporting.chart_confidence(0.9612, 0.9490)
open(r"C:\Users\zcj00\乳腺癌\_chart_conf.png", "wb").write(c1)

feats = [
    {"name": "面积最大值", "value": 0.182},
    {"name": "凹点最大值", "value": 0.141},
    {"name": "半径最大值", "value": 0.097},
    {"name": "纹理标准差", "value": 0.052},
    {"name": "平滑度最大值", "value": -0.031},
    {"name": "对称性标准差", "value": -0.048},
]
c2 = reporting.chart_features(feats)
open(r"C:\Users\zcj00\乳腺癌\_chart_feat.png", "wb").write(c2)

payload = {
    "user_id": "3", "run_id": "testrun-abcdef12", "username": "zcj",
    "record_id": "453", "created_at": "2026-10-18 18:40",
    "prediction": {"output": "恶性", "confidence": 0.9612, "raw_confidence": 0.9490, "time": 0.021},
    "top_features": feats,
    "narrative": "本次判断为恶性，主要依据是面积最大值与凹点最大值偏高，两项合计贡献约 32%。",
    "citations": ["DOC-FEAT-014", "DOC-FEAT-021"],
}
out = reporting.render("single", payload)
print("PDF:", os.path.basename(out["path"]), "%.1f KB" % (out["size"]/1024))
print("图表:", len(c1), "字节 /", len(c2), "字节")
