"""Fixtures shared by the rpi_backend unit tests."""

import importlib
import sys
from unittest.mock import MagicMock

import pytest

# The real pyzmq modules, loaded once: a C extension cannot be imported twice, and a second copy of the
# module would have its own exception classes (``zmq.Again``) that the sockets never raise.
_REAL_ZMQ = {}


def _zmq_names():
    return [n for n in sys.modules if n == "zmq" or n.startswith("zmq.")]


@pytest.fixture
def real_zmq():
    """The real pyzmq, even when another test module replaced ``sys.modules["zmq"]`` with a MagicMock.

    ``tests/unit/orchestration`` does that at import time and never undoes it, so in a full run ``import zmq``
    at collection time can hand out a mock. The mock is put back after the test. Returns ``(zmq, zmq.asyncio)``.
    """
    names = _zmq_names()
    saved = {}
    if any(isinstance(sys.modules[n], MagicMock) for n in names):
        saved = {n: sys.modules.pop(n) for n in names}
        sys.modules.update(_REAL_ZMQ)
    try:
        zmq = importlib.import_module("zmq")
        zmq_asyncio = importlib.import_module("zmq.asyncio")
        _REAL_ZMQ.update({n: sys.modules[n] for n in _zmq_names()})
        yield zmq, zmq_asyncio
    finally:
        if saved:
            for name in _zmq_names():
                del sys.modules[name]
            sys.modules.update(saved)
