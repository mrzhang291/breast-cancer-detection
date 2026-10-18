import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import reporting
payload = {
    "user_id": "3", "run_id": "testrun12345678", "username": "zcj",
    "record_id": "470", "created_at": "2026-10-18 19:58",
    "prediction": {"output": "良性", "confidence": 0.9977, "raw_confidence": 0.9973, "time": 0.02},
    "top_features": [{"name": "凹点最大值", "value": 0.09}, {"name": "面积最大值", "value": 0.08}],
    "input_features": [{"name": "半径平均值", "value": 11.84}, {"name": "纹理平均值", "value": 18.94}],
    "narrative": "本次判断为良性。",
    "citations": ["DOC-MODEL-003"],
}
out = reporting.render("single", payload)
print("PDF:", os.path.basename(out["path"]), "%.1f KB" % (out["size"]/1024))
