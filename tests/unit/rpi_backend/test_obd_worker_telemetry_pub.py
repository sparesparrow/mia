"""The OBD worker publishes obd/telemetry on its own PUB socket, only when an endpoint is configured.

Before this fix the publish loop sent on the SUB socket that listens to the serial bridge (port 5556).
ZeroMQ refuses that with ENOTSUP, so the loop logged an error every 100 ms and never published anything.
"""

import importlib.util
import json
import logging
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

pytestmark = pytest.mark.req("REQ-AUTO-001")

MODULE = Path(__file__).resolve().parents[3] / "apps" / "rpi-backend" / "py-api" / "services" / "obd_worker.py"
ENV = "OBD_TELEMETRY_PUB_ENDPOINT"
PAYLOAD_KEYS = {"engine_rpm", "speed_kmh", "coolant_temp_c", "device_id", "timestamp", "adapter_capabilities"}
PUBLISH_ERROR = "Error in telemetry publish loop"


@pytest.fixture
def obd(real_zmq):
    """obd_worker loaded from its hyphenated path, bound to the real pyzmq."""
    spec = importlib.util.spec_from_file_location("obd_worker_under_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def make_worker(obd):
    """Build workers on private inproc endpoints and tear their sockets and contexts down afterwards."""
    workers = []

    def make(**kwargs):
        worker = obd.MIAOBDWorker(
            broker_url="inproc://obd-test-broker", telemetry_url="inproc://obd-test-serial-bridge", **kwargs
        )
        workers.append(worker)
        return worker

    yield make
    for worker in workers:
        worker.running = False
        for sock in (worker.broker_socket, worker.telemetry_socket):
            if sock is not None:
                sock.close(0)
        worker.context.term()


def _subscribed_sub(worker, zmq):
    """A real SUB socket like the one start() makes, connected to where the serial bridge would publish."""
    sub = worker.context.socket(zmq.SUB)
    sub.connect(worker.telemetry_url)
    sub.subscribe("mcu/telemetry")
    sub.subscribe("mcu/status")
    worker.telemetry_socket = sub
    return sub


def _run_publish_loop(worker, seconds):
    worker.running = True
    thread = threading.Thread(target=worker._telemetry_publish_loop, daemon=True)
    thread.start()
    time.sleep(seconds)
    worker.running = False
    thread.join(timeout=2)
    assert not thread.is_alive(), "the publish loop did not stop"


def test_without_an_endpoint_the_loop_never_sends_on_the_sub_socket_or_logs_errors(
    make_worker, real_zmq, monkeypatch, caplog
):
    zmq, _ = real_zmq
    monkeypatch.delenv(ENV, raising=False)
    worker = make_worker()
    _subscribed_sub(worker, zmq)
    worker.telemetry_socket = mock.Mock(wraps=worker.telemetry_socket)

    with caplog.at_level(logging.DEBUG):
        _run_publish_loop(worker, 0.5)

    worker.telemetry_socket.send_multipart.assert_not_called()
    worker.telemetry_socket.send.assert_not_called()
    # Only the publish loop is under test: other start-up errors (CI has no ELM327-emulator) are not its concern.
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING and "publish" in r.getMessage()]
    assert not [r for r in caplog.records if "Operation not supported" in r.getMessage()]


def test_start_without_an_endpoint_skips_the_publish_thread_and_says_so_once(
    make_worker, obd, monkeypatch, caplog
):
    monkeypatch.delenv(ENV, raising=False)
    monkeypatch.setattr(obd, "ELM327_AVAILABLE", True)
    worker = make_worker()
    monkeypatch.setattr(worker, "_start_elm_emulator", lambda: None)
    publish_loop = mock.Mock()
    monkeypatch.setattr(worker, "_telemetry_publish_loop", publish_loop)

    with caplog.at_level(logging.INFO):
        assert worker.start() is True
    worker.running = False

    publish_loop.assert_not_called()
    off = [r for r in caplog.records if "OBD telemetry publishing is off" in r.getMessage()]
    assert len(off) == 1
    assert off[0].levelno == logging.INFO


def test_with_an_endpoint_obd_telemetry_arrives_on_its_own_pub_socket(make_worker, real_zmq, monkeypatch, caplog):
    zmq, _ = real_zmq
    endpoint = "inproc://obd-test-telemetry-pub"
    monkeypatch.setenv(ENV, endpoint)
    worker = make_worker()
    serial_sub = _subscribed_sub(worker, zmq)
    worker.telemetry_socket = mock.Mock(wraps=serial_sub)
    worker._active_protocol = "ISO 15765-4 CAN 11-bit 500kbps"
    worker._elm_initialized = True

    consumer = worker.context.socket(zmq.SUB)
    consumer.connect(endpoint)
    consumer.subscribe("obd/telemetry")
    worker.running = True
    thread = threading.Thread(target=worker._telemetry_publish_loop, daemon=True)
    try:
        with caplog.at_level(logging.DEBUG):
            thread.start()
            assert consumer.poll(5000), "no obd/telemetry message arrived"
            topic, body = consumer.recv_multipart()
    finally:
        worker.running = False
        thread.join(timeout=2)
        consumer.close(0)

    assert not thread.is_alive()
    assert topic == b"obd/telemetry"
    payload = json.loads(body)
    assert set(payload) == PAYLOAD_KEYS
    assert payload["device_id"] == "obd_worker"
    assert payload["engine_rpm"] == worker.car_state.get_rpm()
    worker.telemetry_socket.send_multipart.assert_not_called()
    assert not [r for r in caplog.records if PUBLISH_ERROR in r.getMessage()]


def test_the_throttle_logs_a_repeated_error_at_most_once_per_window(obd, caplog):
    now = [1000.0]
    log = logging.getLogger("obd-throttle-test")
    throttle = obd.ErrorLogThrottle(log, window_sec=60.0, clock=lambda: now[0])

    with caplog.at_level(logging.ERROR, logger="obd-throttle-test"):
        for _ in range(600):  # ten minutes' worth at one error per 100 ms would be 6000; 600 inside one window
            throttle.error("Error in telemetry publish loop: Operation not supported")
            now[0] += 0.09
        assert len(caplog.records) == 1  # 54 s in: only the first occurrence

        now[0] += 10.0  # past the 60 s window
        throttle.error("Error in telemetry publish loop: Operation not supported")
        assert len(caplog.records) == 2
        assert "599" in caplog.records[1].getMessage()  # the repeats suppressed in between

        throttle.error("Error in telemetry publish loop: Operation not supported")
        assert len(caplog.records) == 2


def test_the_publish_loop_throttles_a_failing_send(make_worker, real_zmq, monkeypatch, caplog):
    zmq, _ = real_zmq
    monkeypatch.setenv(ENV, "inproc://obd-test-telemetry-pub-failing")
    worker = make_worker()
    _subscribed_sub(worker, zmq)
    monkeypatch.setattr(worker, "_telemetry_payload", mock.Mock(side_effect=RuntimeError("boom")))

    with caplog.at_level(logging.ERROR):
        _run_publish_loop(worker, 0.6)

    assert worker._telemetry_payload.call_count >= 3  # it kept trying, and failed each time
    assert len([r for r in caplog.records if PUBLISH_ERROR in r.getMessage()]) == 1
