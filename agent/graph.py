"""极简图执行引擎。

对标 LangGraph 的三件事：显式节点、条件边、检查点续跑。
刻意保持「确定性」：节点固定、边固定，只有节点内部的推理是自由的。
"""
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class Interrupt(Exception):
    """节点主动挂起，等待外部确认后从下一个节点继续。"""

    def __init__(self, node: str, payload: Dict):
        super().__init__('interrupted at %s' % node)
        self.node = node
        self.payload = payload or {}


class Graph:
    def __init__(self, name: str = 'graph'):
        self.name = name
        self._nodes: Dict[str, Callable] = {}
        self._edges: Dict[str, Tuple[str, Any, Dict]] = {}
        self._entry: Optional[str] = None

    # ---------------------------------------------------------------- 构建

    def add_node(self, name: str, fn: Callable) -> 'Graph':
        if name in self._nodes:
            raise ValueError('重复节点: %s' % name)
        self._nodes[name] = fn
        return self

    def add_edge(self, src: str, dst: str) -> 'Graph':
        self._edges[src] = ('static', dst, {})
        return self

    def add_conditional_edges(self, src: str, router: Callable, mapping: Dict[str, str]) -> 'Graph':
        self._edges[src] = ('cond', router, mapping)
        return self

    def set_entry(self, name: str) -> 'Graph':
        self._entry = name
        return self

    # ---------------------------------------------------------------- 执行

    def _next(self, node: str, state: Dict) -> Optional[str]:
        edge = self._edges.get(node)
        if edge is None:
            return None
        kind, target, mapping = edge
        if kind == 'static':
            return target
        key = target(state)
        if key is None:
            return None
        if key not in mapping:
            raise ValueError('条件边 %s 返回了未映射的键: %r' % (node, key))
        return mapping[key]

    def invoke(self, state: Dict, ctx: Any, checkpointer=None,
               emit: Optional[Callable] = None, start: Optional[str] = None,
               max_steps: int = 40) -> Dict:
        """执行图；遇到 Interrupt 或 max_steps 则返回挂起状态。"""
        current = start or self._entry
        steps: List[Dict] = []
        run_id = state.get('run_id', '')
        if start and state.get('status') == 'interrupted':
            state['status'] = 'ok'
        seq = 0

        while current and seq < max_steps:
            fn = self._nodes.get(current)
            if fn is None:
                raise ValueError('未知节点: %s' % current)

            seq += 1
            started = time.time()
            try:
                updates = fn(state, ctx)
                if isinstance(updates, dict):
                    state.update(updates)
                latency = int((time.time() - started) * 1000)
                step = {'seq': seq, 'node': current, 'latency_ms': latency, 'verdict': 'ok'}
                steps.append(step)
                if emit:
                    emit('node', {'seq': seq, 'node': current, 'ms': latency})

                nxt = self._next(current, state)
                if checkpointer and run_id:
                    checkpointer.save(run_id, seq, current, nxt, state)
                current = nxt

            except Interrupt as it:
                latency = int((time.time() - started) * 1000)
                step = {'seq': seq, 'node': current, 'latency_ms': latency,
                        'verdict': 'interrupted'}
                steps.append(step)
                if emit:
                    emit('interrupt', {'node': current, 'payload': it.payload,
                                       'seq': seq})
                nxt = self._next(current, state)
                if checkpointer and run_id:
                    checkpointer.save(run_id, seq, current, nxt, state, pending=it.payload)
                state['status'] = 'interrupted'
                return {'state': state, 'status': 'interrupted', 'steps': steps,
                        'resume_at': nxt, 'pending': it.payload}

            except Exception as exc:  # noqa: BLE001
                latency = int((time.time() - started) * 1000)
                steps.append({'seq': seq, 'node': current, 'latency_ms': latency,
                              'verdict': 'error', 'error': str(exc)[:200]})
                state['status'] = 'error'
                state['error'] = str(exc)
                if checkpointer and run_id:
                    checkpointer.save(run_id, seq, current, None, state)
                return {'state': state, 'status': 'error', 'steps': steps,
                        'error': str(exc)}

        return {'state': state, 'status': state.get('status', 'ok'), 'steps': steps}

    # ---------------------------------------------------------------- 描述

    def describe(self) -> Dict:
        nodes = []
        for name in self._nodes:
            edge = self._edges.get(name)
            if not edge:
                nodes.append({'name': name, 'next': None, 'kind': 'terminal'})
            elif edge[0] == 'static':
                nodes.append({'name': name, 'next': edge[1], 'kind': 'static'})
            else:
                nodes.append({'name': name, 'next': edge[2], 'kind': 'conditional'})
        return {'name': self.name, 'entry': self._entry, 'nodes': nodes}


class JsonCheckpointer:
    """把每步状态写进 agent.db，支持回放与从任意步骤续跑。"""

    def save(self, run_id: str, seq: int, node: str, nxt: Optional[str],
             state: Dict, pending: Optional[Dict] = None) -> None:
        from . import db
        db.save_checkpoint(run_id, seq, node, nxt, _clean(state), pending)

    def load(self, run_id: str) -> Optional[Dict]:
        from . import db
        return db.load_checkpoint(run_id)


def _clean(state: Dict) -> Dict:
    """去掉不可序列化的键，保证检查点可存档。"""
    out = {}
    for key, value in state.items():
        if key.startswith('_'):
            continue
        try:
            json.dumps(value, ensure_ascii=False)
            out[key] = value
        except Exception:
            out[key] = str(value)[:500]
    return out
