"""运行时桥接。

agent 层不 import app（避免循环依赖），由 app.py 在启动时把底层能力注入进来：

    runtime.bind(predict=..., explain=..., fetch_records=..., fetch_stats=...)

这样同一套工具既能被 Web 路由用，也能被测试单独驱动。
"""
from typing import Any, Callable, Dict, Optional


class Runtime:
    def __init__(self) -> None:
        self.predict: Optional[Callable] = None       # (features: list[float]) -> dict
        self.explain: Optional[Callable] = None       # (features, prediction, confidence) -> dict
        self.fetch_records: Optional[Callable] = None  # (user_id, page, size, filter) -> dict
        self.fetch_stats: Optional[Callable] = None    # (user_id) -> dict
        self.rag: Any = None
        self.render_report: Optional[Callable] = None  # (kind, payload) -> dict

    def bind(self, **kwargs) -> 'Runtime':
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError('未知的运行时能力: %s' % key)
            setattr(self, key, value)
        return self

    def require(self, *names: str) -> None:
        missing = [n for n in names if getattr(self, n, None) is None]
        if missing:
            raise RuntimeError('运行时能力未注入: %s' % ', '.join(missing))

    def status(self) -> Dict[str, bool]:
        return {k: getattr(self, k) is not None
                for k in ('predict', 'explain', 'fetch_records', 'fetch_stats',
                          'rag', 'render_report')}


_RUNTIME = Runtime()


def get() -> Runtime:
    return _RUNTIME
