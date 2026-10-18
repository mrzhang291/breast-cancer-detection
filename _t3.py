import os, sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
os.chdir(r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
os.environ["AGENT_LLM"] = "off"
import numpy as np
from agent import runtime as rt, orchestrator
from agent.context import AgentContext

def _records(user_id, page, size):
    feats = {"feature_%d" % i: v for i, v in enumerate([
        17.99,10.38,122.8,1001.0,0.1184,0.2776,0.3001,0.1471,0.2419,0.07871,
        1.095,0.9053,8.589,153.4,0.006399,0.04904,0.05373,0.01587,0.03003,0.006193,
        25.38,17.33,184.6,2019.0,0.1622,0.6656,0.7119,0.2654,0.4601,0.1189], start=1)}
    return {"total": 3, "items": [
        {"id": 101, "prediction_result": "恶性", "confidence": 0.999, "created_at": "2026-05-18", "features": feats},
        {"id": 102, "prediction_result": "恶性", "confidence": 0.999, "created_at": "2026-05-18", "features": feats},
        {"id": 103, "prediction_result": "良性", "confidence": 0.999, "created_at": "2026-05-18", "features": feats},
    ]}

def _predict(features):
    arr = np.asarray(features, dtype=float).reshape(1, -1)
    return {"output": "恶性", "raw_output": 1, "confidence": 0.998, "time": 0.01, "model_type": "fake"}

def _explain(features, prediction, confidence):
    return {"prediction": prediction, "confidence": confidence,
            "top_features": [{"name": "area_mean", "value": features[3], "shap_value": 0.4,
                              "importance": 0.4, "direction": "推向恶性"}]}

def _stats(uid):
    return {"total": 3, "benign": 1, "malignant": 2, "avg_confidence": 0.999}

rt.get().bind(predict=_predict, explain=_explain, fetch_records=_records, fetch_stats=_stats)

for q in ["恶性病例的平均面积比良性高多少", "把最近 3 条恶性记录逐条解释"]:
    ctx = AgentContext(user_id=3, role_id=3, lang="zh")
    res = orchestrator.run(ctx, q)
    print("=" * 70)
    print("Q:", q)
    print("intent:", res["intent"], "| status:", res["status"], "| tier:", res["tier"])
    print(res["answer_md"][:420])
