"""Frozen-only compatibility: Gradio's developer .pyi generation is unnecessary.

Patch at module load, before ComponentMeta constructs the component classes.
This preserves a read-only/signed bundle without modifying installed Gradio.
"""

import importlib.abc
import importlib.util
import sys


class _Loader(importlib.abc.Loader):
    def __init__(self, original):
        self.original = original

    def create_module(self, spec):
        return self.original.create_module(spec)

    def exec_module(self, module):
        self.original.exec_module(module)
        module.create_or_modify_pyi = lambda *_args, **_kwargs: None


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != "gradio.component_meta":
            return None
        sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(fullname)
        finally:
            sys.meta_path.insert(0, self)
        if spec is not None and spec.loader is not None:
            spec.loader = _Loader(spec.loader)
        return spec


sys.dont_write_bytecode = True
sys.meta_path.insert(0, _Finder())
