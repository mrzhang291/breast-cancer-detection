"""轨迹记录：每一步都落库，支持事后回放。"""
import time
from contextlib import contextmanager

from . import db


def record_step(ctx, node: str, tool: str = '', args=None,
                result_digest: str = '', verdict: str = '', latency_ms: int = 0) -> dict:
    step = ctx.add_step(node=node, tool=tool, verdict=verdict,
                        latency_ms=latency_ms, result_digest=result_digest)
    if ctx.run_id:
        db.add_step(ctx.run_id, step['seq'], node, tool, args,
                    result_digest, verdict, latency_ms)
    return step


@contextmanager
def timed(ctx, node: str, tool: str = '', args=None):
    """计时上下文：with timed(ctx, 'tool', 'predict') as box: ..."""
    box = {'digest': '', 'verdict': ''}
    started = time.time()
    try:
        yield box
    finally:
        record_step(ctx, node, tool, args,
                    result_digest=box.get('digest', ''),
                    verdict=box.get('verdict', ''),
                    latency_ms=int((time.time() - started) * 1000))
