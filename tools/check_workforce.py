#!/usr/bin/env python3
"""Run the integrated workforce's offline tests; never launch a model or GUI."""
from pathlib import Path
import platform
import sys
import unittest


def main():
    if sys.version_info < (3, 11):
        try:
            import tomli  # Test-only backport; runtime adapters remain stdlib.
        except ImportError:
            print('Python 3.9/3.10 tests need: python -m pip install tomli==2.2.1', file=sys.stderr)
            return 2
    root = Path(__file__).resolve().parents[1]
    suite = unittest.TestSuite()
    for pattern in ('test_ghost*.py', 'test_interpreter*.py', 'test_fcp*.py'):
        tests = unittest.TestLoader().discover(str(root / 'tests'), pattern=pattern)
        count = tests.countTestCases()
        if not count:
            raise ValueError('Missing required test family: ' + pattern)
        print(pattern + ': ' + str(count) + ' tests', flush=True)
        suite.addTests(tests)
    print('Environment: ' + platform.system() + ' / Python ' + platform.python_version(), flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
