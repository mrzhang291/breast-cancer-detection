import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
i = o.find("def _node_persist")
print("=== _node_persist ===")
print(o[i:i+700])
j = o.find("db.update_run(ctx.run_id,")
print("\n=== run() 里的 update_run ===")
print(o[j:j+400])
