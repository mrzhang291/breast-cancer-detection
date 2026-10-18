"""看 run_llm_agent 与 stream_llm_agent 当前实现。"""
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = io.open('agent/llm_agent.py', encoding='utf-8').read()
i = s.find('def run_llm_agent')
print(s[i:i + 2400])
