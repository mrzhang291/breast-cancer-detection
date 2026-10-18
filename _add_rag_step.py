import io, sys
sys.stdout.reconfigure(encoding="utf-8")
p = "deploy/deploy-euleros.sh"
s = io.open(p, encoding="utf-8").read()
anchor = 'echo "==> 5/9 写入 systemd 服务"'
addition = ('echo "==> 4.5/9 构建 RAG 索引"\n'
            '.venv/bin/python -m agent.rag.build >/dev/null 2>&1 || \\\n'
            '  .venv/bin/python -m agent.rag.build\n\n')
if "构建 RAG 索引" not in s:
    s = s.replace(anchor, addition + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("部署脚本已加入索引构建")
else:
    print("已存在")
