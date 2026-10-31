"""Fixtures shared by the rpi_backend unit tests."""

import sys

import pytest


def _zmq_names():
    return [n for n in sys.modules if n == "zmq" or n.startswith("zmq.")]


@pytest.fixture
def real_zmq(real_zmq_modules):
    """The real pyzmq, even when another test module replaced ``sys.modules["zmq"]`` with a MagicMock.

    ``tests/unit/orchestration`` does that at import time and never undoes it. The modules captured by
    tests/conftest.py before that happened are put back for the test and the previous ones restored after.
    Returns ``(zmq, zmq.asyncio)``.
    """
    saved = {n: sys.modules[n] for n in _zmq_names()}
    for name in saved:
        del sys.modules[name]
    sys.modules.update(real_zmq_modules)
    try:
        yield sys.modules["zmq"], sys.modules["zmq.asyncio"]
    finally:
        for name in _zmq_names():
            del sys.modules[name]
        sys.modules.update(saved)
