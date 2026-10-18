# agent 层说明

把主站的预测/归因/记录能力封装成**可校验的工具**，用**确定性状态机**编排，
再叠一层 **RAG 检索 + 引用 + 护栏**。数值永远来自工具，模型只负责措辞。

---

## 目录

```
agent/
├── context.py      一次 run 的上下文（user/role/facts/citations/steps）
├── db.py           agent.db：runs / steps / 语料 / 缓存 / 反馈
├── registry.py     @tool 契约：schema 校验 + 权限 + 超时 + 统一 ToolResult
├── runtime.py      由 app.py 注入的底层能力（predict/explain/records/stats/rag）
├── policy.py       医疗护栏 + 权限矩阵 + 免责声明注入
├── verify.py       claim ↔ fact 对账（回答里的数字必须能在 facts 找到）
├── cache.py        语义缓存（归一化哈希，按用户隔离）
├── tracing.py      每步落库，支持回放
├── llm.py          DeepSeek 适配（不可用则自动降级为模板）
├── orchestrator.py 状态机：route → act → compose → verify → guard
├── tools/          predict / explain / records / statistics / similar_cases
│                   / search_knowledge / get_clause
├── rag/            corpus 切分、倒排索引、建索引 CLI
├── knowledge/      features.json（30 条特征词典，含真实统计量）
├── eval/           cases.jsonl（20 条 golden set）+ run_eval.py（门禁）
└── tests/          pytest（23 条）
```

---

## 七个工具

| 工具 | 权限 | 作用 |
|---|---|---|
| `predict` | predict | 30 维特征 → 良恶性 + 置信度 |
| `explain` | explain | 特征归因（SHAP），**展示原始量纲** |
| `records` | records:read | 历史记录，带行级权限 |
| `statistics` | stats:read | 总数/良恶性分布/平均置信度 |
| `similar_cases` | cases:read | 数据集里的近邻样本对照 |
| `search_knowledge` | knowledge:read | 检索文档/词典条款（IDF 加权） |
| `get_clause` | knowledge:read | 按 clause_id 精确取条款 |

统一入口 `registry.call_tool(ctx, name, args)`：非法参数、越权、超时、内部异常
都有确定语义，不会把脏数据放进模型上下文。

---

## 五个节点

```
route ──▶ act ──▶ compose ──▶ verify ──▶ guard
 │        │         │           │          │
意图分类  调工具    模板生成    数字对账   护栏+免责
```

- **compose 先模板**：数值型回答完全由模板渲染，天然可对账；
- **模型只润色**：仅 `usage/general` 类叙述型问题会走 LLM，且必须通过 verify；
- **verify 不通过**：丢弃模型输出，回退模板（不是重试到通过为止）。

---

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/agent/run` | 主入口，SSE（step / token / done） |
| POST | `/api/agent/run-sync` | 同步版，调试与评测用 |
| GET | `/api/agent/runs` | 我的 run 列表 |
| GET | `/api/agent/runs/<id>` | 完整轨迹（可回放） |
| GET | `/api/agent/tools` | 工具/LLM/RAG 状态 |
| GET | `/api/rag/search?q=` | 直接看检索命中 |
| POST | `/api/cases/similar` | 相似病例 |

`/ai-query` 与 `/generate-summary` 已改造为走编排器（前者兼容旧响应格式）。

---

## RAG 的两条工程取舍

1. **不引向量库**：语料 217 条、倒排 1.3 万行，SQLite 倒排 + IDF 已经够用；
   5000 条以内暴力检索比 FAISS 更快且零运维。
2. **中文切"单字 + 二元词"**：FTS5 的 `unicode61` 不分中文，`trigram` 对
   两字词（"半径"）召回不了；自建倒排反而更稳。

```bash
python -m agent.rag.build     # 重建索引（改语料后执行）
```

---

## 开关

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `AGENT_LLM` | `auto` | `off` 纯模板；`auto` 探测可用才用；`api` 强制 |
| `DEEPSEEK_API_KEY` | 空 | 不设置则全程离线，功能不受影响 |

> 刻意不读取代码里那个硬编码 key —— 泄露过的密钥不应该再被使用。

---

## 自测

```bash
python -m pytest agent/tests -q          # 23 条单元测试
python -m agent.eval.run_eval            # 20 条评测 + 六项指标门禁
python -m agent.eval.run_eval --fake     # 不加载 pkl 的快速版
```

门禁阈值：意图 0.9 / 引用 0.9 / 拒答 1.0 / 升级 1.0 / 对账 1.0 / p95 8s。
不达标 `exit 1`，可直接挂 CI。
