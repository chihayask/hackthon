# -*- coding: utf-8 -*-
'''零依赖测试运行器：提供 pytest.raises 垫片，收集并执行 test_* 函数。

用法： python run_tests.py [tests/test_verify.py ...]
'''
from __future__ import annotations

import contextlib
import importlib.util
import os
import sys
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'src'))


class _RaisesContext:
    def __init__(self, expected):
        self.expected = expected

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError('没有抛出预期的异常: ' + str(self.expected))
        if issubclass(exc_type, self.expected):
            return True
        return False


def _install_pytest_shim():
    shim = types.ModuleType('pytest')
    class _Approx:
        def __init__(self, expected, rel=None, abs=None):
            self.expected = expected
            self.rel = rel
            self.abs = abs
        def __eq__(self, other):
            tol = self.abs if self.abs is not None else (self.rel or 1e-6) * max(abs(self.expected), 1e-300)
            return abs(other - self.expected) <= tol
        def __repr__(self):
            return 'approx(' + repr(self.expected) + ')'
    shim.approx = lambda expected, rel=None, abs=None: _Approx(expected, rel, abs)
    shim.raises = lambda expected, *a, **k: _RaisesContext(expected)
    shim.fail = lambda msg='': (_ for _ in ()).throw(AssertionError(msg))
    sys.modules['pytest'] = shim


def load_module(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv):
    _install_pytest_shim()
    targets = argv[1:]
    if not targets:
        tests_dir = os.path.join(HERE, 'tests')
        targets = [os.path.join(tests_dir, f) for f in sorted(os.listdir(tests_dir))
                   if f.startswith('test_') and f.endswith('.py')]
    passed = 0
    failed = 0
    for path in targets:
        module = load_module(path)
        names = [n for n in dir(module) if n.startswith('test_')]
        for name in names:
            fn = getattr(module, name)
            if not callable(fn):
                continue
            try:
                fn()
                passed += 1
                print('PASS  ' + os.path.basename(path) + '::' + name)
            except Exception:
                failed += 1
                print('FAIL  ' + os.path.basename(path) + '::' + name)
                traceback.print_exc()
    # 测试用的临时目录（契约测试、隔离测试会在这里放副本）。各测试自己清理子目录，
    # 但父目录会留下来变成工作区噪声——这里统一收尾，且只删空目录，绝不误删有内容的目录。
    import shutil
    for name in ('_contract_tmp', '_isolation_tmp', '_adversarial_tmp'):
        path = os.path.join(HERE, name)
        if os.path.isdir(path) and not os.listdir(path):
            try:
                shutil.rmtree(path)
            except OSError:
                pass

    print('')
    print('total %d, passed %d, failed %d' % (passed + failed, passed, failed))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))