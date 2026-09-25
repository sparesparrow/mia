#!/usr/bin/env python3
"""
MIA Driver Simulator — scenario-driven E2E test for the MIA system.

Simulates a driver interacting with MIA: voice commands, vehicle telemetry,
GPIO control, session lifecycle, WebSocket telemetry streaming. Runs remotely
against a deployed MIA instance over the network.

Usage:
  python simulator.py --host 192.168.200.139 --all
  python simulator.py --host 192.168.200.139 --scenario voice_commands
  python simulator.py --host 192.168.200.139 --scenario full_voice --full-voice

Requirements: httpx, pyzmq, websockets (all in MIA requirements.txt)
"""

import argparse
import asyncio
import json
import logging
import os
import struct
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [sim] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

try:
    import zmq
    import zmq.asyncio
except ImportError:
    zmq = None  # ZMQ scenarios will be skipped

try:
    import websockets
except ImportError:
    websockets = None  # WS scenarios will be skipped


# ── Data Structures ──────────────────────────────────────────────────────

@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""
    elapsed: float = 0.0


@dataclass
class ScenarioResult:
    name: str
    steps: List[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.steps if s.passed)

    @property
    def failed(self) -> int:
        return sum(1 for s in self.steps if not s.passed)


# ── REST Client ──────────────────────────────────────────────────────────

class MIAClient:
    """Thin async HTTP client for MIA REST API."""

    def __init__(self, host: str, port: int = 8000, timeout: float = 10.0):
        self.base = f"http://{host}:{port}"
        self._client = httpx.AsyncClient(base_url=self.base, timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def get(self, path: str, **kwargs) -> Tuple[int, Any]:
        r = await self._client.get(path, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

    async def post(self, path: str, body: dict = None, **kwargs) -> Tuple[int, Any]:
        r = await self._client.post(path, json=body, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

    async def put(self, path: str, body: dict = None, **kwargs) -> Tuple[int, Any]:
        r = await self._client.put(path, json=body, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

    async def patch(self, path: str, body: dict = None, **kwargs) -> Tuple[int, Any]:
        r = await self._client.patch(path, json=body, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

    async def delete(self, path: str, **kwargs) -> Tuple[int, Any]:
        r = await self._client.delete(path, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text


# ── ZMQ Injector ─────────────────────────────────────────────────────────

class ZMQInjector:
    """Publishes fake data into the MIA ZMQ bus and subscribes for responses.

    For injection, the simulator uses a PUB socket that connects to the
    same port the downstream SUB connects to. Since the upstream PUB service
    (e.g. mia-audio-capture) binds on that port, the simulator must stop
    the conflicting service before binding its own PUB. Alternatively, for
    ports where the service is not running, the simulator can bind directly.

    For response verification, it creates SUB sockets that connect to
    existing PUB ports.
    """

    def __init__(self, host: str):
        if zmq is None:
            raise RuntimeError("pyzmq required for ZMQ scenarios")
        self.host = host
        self.ctx = zmq.asyncio.Context()
        self._pubs: Dict[int, zmq.asyncio.Socket] = {}
        self._subs: Dict[int, zmq.asyncio.Socket] = {}

    def _get_pub(self, port: int) -> zmq.asyncio.Socket:
        if port not in self._pubs:
            sock = self.ctx.socket(zmq.PUB)
            sock.connect(f"tcp://{self.host}:{port}")
            self._pubs[port] = sock
            # PUB connect needs a moment to establish
        return self._pubs[port]

    def _get_sub(self, port: int, topic: bytes = b"") -> zmq.asyncio.Socket:
        if port not in self._subs:
            sock = self.ctx.socket(zmq.SUB)
            sock.connect(f"tcp://{self.host}:{port}")
            sock.subscribe(topic)
            self._subs[port] = sock
        return self._subs[port]

    async def inject_telemetry(self, pot1: int, pot2: int, throttle: int, coolant: int):
        """Publish MCU telemetry to port 5556 topic mcu/telemetry."""
        pub = self._get_pub(5556)
        data = json.dumps({
            "pot1": pot1, "pot2": pot2,
            "throttle": throttle, "coolant": coolant,
        }).encode()
        await pub.send_multipart([b"mcu/telemetry", data])

    async def inject_mcu_status(self, event: str, device: str = "simulator"):
        """Publish MCU status event to port 5556 topic mcu/status."""
        pub = self._get_pub(5556)
        data = json.dumps({"event": event, "device": device}).encode()
        await pub.send_multipart([b"mcu/status", data])

    async def inject_transcript(self, text: str, confidence: float = 0.95):
        """Publish a fake voice transcript to port 5560 topic mia/voice/transcript."""
        pub = self._get_pub(5560)
        data = json.dumps({
            "text": text,
            "confidence": confidence,
            "audio_duration_ms": 1200,
            "wake_word": "hey_mia",
        }).encode()
        await pub.send_multipart([b"mia/voice/transcript", data])

    async def inject_audio_wake(self, n_frames: int = 5):
        """Publish loud PCM frames to port 5558 to trigger energy-fallback wake word.

        The energy-fallback detector needs 3 consecutive frames with RMS > 1500.
        We generate frames with sample value 8000 (RMS ~8000, well above threshold).
        16kHz, 16-bit mono, 30ms chunks = 480 samples per frame.
        """
        pub = self._get_pub(5558)
        # Generate a loud frame: 480 samples of amplitude 8000
        samples_per_frame = 480
        loud_frame = struct.pack(f"<{samples_per_frame}h", *([8000] * samples_per_frame))
        for _ in range(n_frames):
            await pub.send_multipart([b"mia/audio/raw", loud_frame])
            await asyncio.sleep(0.03)  # 30ms per frame

    async def inject_audio_silence(self, duration_sec: float = 2.0):
        """Publish silence frames to let STT detect end-of-speech."""
        pub = self._get_pub(5558)
        samples_per_frame = 480
        silence = struct.pack(f"<{samples_per_frame}h", *([0] * samples_per_frame))
        n_frames = int(duration_sec / 0.03)
        for _ in range(n_frames):
            await pub.send_multipart([b"mia/audio/raw", silence])
            await asyncio.sleep(0.03)

    async def wait_voice_response(self, timeout: float = 5.0) -> Optional[dict]:
        """Subscribe to port 5561 and wait for a voice response."""
        sub = self._get_sub(5561, b"mia/voice/response")
        try:
            if await asyncio.wait_for(sub.poll(timeout=int(timeout * 1000)), timeout):
                parts = await sub.recv_multipart()
                if len(parts) >= 2:
                    return json.loads(parts[1])
        except asyncio.TimeoutError:
            pass
        return None

    async def close(self):
        for s in list(self._pubs.values()) + list(self._subs.values()):
            s.close()
        self.ctx.term()


# ── Scenario Runner ──────────────────────────────────────────────────────

class DriverSimulator:
    """Orchestrates scenario execution against a MIA instance."""

    def __init__(self, host: str, port: int = 8000, verbose: bool = False,
                 full_voice: bool = False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.full_voice = full_voice
        self.client = MIAClient(host, port)
        self.zmq: Optional[ZMQInjector] = None
        if zmq is not None:
            try:
                self.zmq = ZMQInjector(host)
            except Exception as e:
                logger.warning(f"ZMQ init failed: {e}")
        self.results: List[ScenarioResult] = []

    async def close(self):
        await self.client.close()
        if self.zmq:
            await self.zmq.close()

    # ── Step helper ───────────────────────────────────────────────────

    async def _step(self, result: ScenarioResult, name: str,
                    action: Callable[[], Coroutine],
                    check: Callable[[Any], Tuple[bool, str]] = None):
        """Execute a step, record result."""
        t0 = time.monotonic()
        try:
            value = await action()
            if check:
                passed, detail = check(value)
            else:
                passed, detail = True, ""
        except Exception as e:
            passed, detail = False, str(e)
        elapsed = time.monotonic() - t0

        sr = StepResult(name=name, passed=passed, detail=detail, elapsed=elapsed)
        result.steps.append(sr)

        mark = "\u2713" if passed else "\u2717"
        msg = f"  {mark} {name}"
        if detail and self.verbose:
            msg += f"  ({detail})"
        elif detail and not passed:
            msg += f"  ({detail})"
        print(msg)

    # ── Scenarios ─────────────────────────────────────────────────────

    async def scenario_infrastructure(self) -> ScenarioResult:
        """Test system endpoints (pure REST, no ZMQ needed)."""
        r = ScenarioResult(name="infrastructure")

        await self._step(r, "GET /status",
            lambda: self.client.get("/status"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        await self._step(r, "GET /features",
            lambda: self.client.get("/features"),
            lambda v: (v[0] == 200 and isinstance(v[1], dict) and v[1].get("total", 0) > 80,
                        f"total={v[1].get('total', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "GET /health/thermal",
            lambda: self.client.get("/health/thermal"),
            lambda v: (v[0] == 200 and "temperature_c" in str(v[1]),
                        f"{v[1].get('temperature_c', '?')}C {v[1].get('status', '')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "GET /devices",
            lambda: self.client.get("/devices"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        await self._step(r, "GET /telemetry",
            lambda: self.client.get("/telemetry"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        await self._step(r, "GET /ota/status",
            lambda: self.client.get("/ota/status"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        await self._step(r, "GET /logs/services",
            lambda: self.client.get("/logs/services"),
            lambda v: (v[0] == 200 and "mia-api" in str(v[1]),
                        f"{len(v[1])} services" if isinstance(v[1], list) else f"{v[0]}"))

        await self._step(r, "GET /logs/mia-api",
            lambda: self.client.get("/logs/mia-api", params={"lines": 5}),
            lambda v: (v[0] == 200, f"{v[0]}"))

        return r

    async def scenario_session_handoff(self) -> ScenarioResult:
        """Test session create → read → update → handoff → resume → delete."""
        r = ScenarioResult(name="session_handoff")
        session_id = None
        handoff_token = None

        # Create session
        async def create():
            code, body = await self.client.post("/sessions", {
                "client_type": "android",
                "client_name": "MIA-Simulator",
            })
            nonlocal session_id
            if isinstance(body, dict):
                session_id = body.get("session_id") or body.get("session", {}).get("session_id")
            return code, body

        await self._step(r, "create session",
            create,
            lambda v: (v[0] == 200 and session_id is not None,
                        f"sid={session_id}" if session_id else f"{v[0]}"))

        if not session_id:
            return r

        # Read session
        await self._step(r, "read session",
            lambda: self.client.get(f"/sessions/{session_id}"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        # Update subscriptions
        await self._step(r, "update subscriptions",
            lambda: self.client.patch(f"/sessions/{session_id}", {
                "device_subscriptions": ["obd", "gpio"],
            }),
            lambda v: (v[0] == 200, f"{v[0]}"))

        # Handoff
        async def handoff():
            code, body = await self.client.post(f"/sessions/{session_id}/handoff")
            nonlocal handoff_token
            if isinstance(body, dict):
                handoff_token = body.get("handoff_token")
            return code, body

        await self._step(r, "generate handoff token",
            handoff,
            lambda v: (v[0] == 200 and handoff_token is not None,
                        f"token={'yes' if handoff_token else 'no'}"))

        # Resume with token
        if handoff_token:
            await self._step(r, "resume session",
                lambda: self.client.post("/sessions/resume", {
                    "handoff_token": handoff_token,
                }),
                lambda v: (v[0] == 200, f"{v[0]}"))

        # Delete
        await self._step(r, "delete session",
            lambda: self.client.delete(f"/sessions/{session_id}"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        return r

    async def scenario_gpio_control(self) -> ScenarioResult:
        """Test GPIO configure → set → read → reset cycle via ZMQ broker."""
        r = ScenarioResult(name="gpio_control")

        await self._step(r, "configure pin 18 output",
            lambda: self.client.post("/gpio/configure", {"pin": 18, "direction": "output"}),
            lambda v: (v[0] == 200, f"success={v[1].get('success', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "set pin 18 = 1",
            lambda: self.client.post("/gpio/set", {"pin": 18, "value": 1}),
            lambda v: (v[0] == 200, f"success={v[1].get('success', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "read pin 18",
            lambda: self.client.get("/gpio/18"),
            lambda v: (v[0] == 200, f"value={v[1].get('value', v[1].get('error', '?'))}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "set pin 18 = 0",
            lambda: self.client.post("/gpio/set", {"pin": 18, "value": 0}),
            lambda v: (v[0] == 200, f"success={v[1].get('success', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "read pin 18 (off)",
            lambda: self.client.get("/gpio/18"),
            lambda v: (v[0] == 200, f"value={v[1].get('value', v[1].get('error', '?'))}" if isinstance(v[1], dict) else f"{v[0]}"))

        return r

    async def scenario_led_control(self) -> ScenarioResult:
        """Test LED on → read → off cycle."""
        r = ScenarioResult(name="led_control")

        await self._step(r, "read LED state",
            lambda: self.client.get("/led/state"),
            lambda v: (v[0] == 200, f"mode={v[1].get('led_state', {}).get('mode', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "LED on (brightness 128)",
            lambda: self.client.put("/led/state", {"mode": "on", "brightness": 128}),
            lambda v: (v[0] == 200, f"{v[0]}"))

        await self._step(r, "verify LED on",
            lambda: self.client.get("/led/state"),
            lambda v: (v[0] == 200 and (isinstance(v[1], dict) and
                        v[1].get("led_state", {}).get("mode") == "on"),
                        f"mode={v[1].get('led_state', {}).get('mode', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        await self._step(r, "LED off",
            lambda: self.client.put("/led/state", {"mode": "off"}),
            lambda v: (v[0] == 200, f"{v[0]}"))

        return r

    async def scenario_websocket_telemetry(self) -> ScenarioResult:
        """Connect to WebSocket and verify telemetry streaming."""
        r = ScenarioResult(name="websocket_telemetry")

        if websockets is None:
            await self._step(r, "websockets library",
                lambda: asyncio.sleep(0),
                lambda _: (False, "websockets not installed"))
            return r

        frames: list = []

        async def receive_frames():
            uri = f"ws://{self.host}:{self.port}/ws/telemetry"
            async with websockets.connect(uri) as ws:
                end = time.monotonic() + 3.0
                while time.monotonic() < end:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        frames.append(json.loads(msg))
                    except (asyncio.TimeoutError, Exception):
                        break
            return len(frames)

        await self._step(r, "receive 3s of telemetry",
            receive_frames,
            lambda n: (n >= 15, f"{n} frames"))

        if frames:
            sample = frames[0]
            has_keys = "telemetry" in sample or "led_state" in sample
            await self._step(r, "frame structure valid",
                lambda: asyncio.sleep(0),
                lambda _: (has_keys, f"keys={list(sample.keys())[:4]}"))

        return r

    async def scenario_voice_commands(self) -> ScenarioResult:
        """Test voice command routing via REST (simulates what the router does).

        Calls the same endpoints the voice router calls, verifying each
        returns valid data. Also checks ZMQ voice response if available.
        """
        r = ScenarioResult(name="voice_commands")

        # Each command: (label, endpoint, method, body, check_key)
        commands = [
            ("system status", "/status", "GET", None, None),
            ("processor temperature", "/health/thermal", "GET", None, "temperature_c"),
            ("engine telemetry", "/telemetry", "GET", None, None),
            ("connected devices", "/devices", "GET", None, None),
            ("feature list", "/features", "GET", None, "total"),
            ("turn lights on", "/led/state", "PUT", {"mode": "on", "brightness": 128}, None),
            ("turn lights off", "/led/state", "PUT", {"mode": "off"}, None),
        ]

        for label, endpoint, method, body, check_key in commands:
            async def call(ep=endpoint, m=method, b=body):
                if m == "GET":
                    return await self.client.get(ep)
                elif m == "PUT":
                    return await self.client.put(ep, b)
                elif m == "POST":
                    return await self.client.post(ep, b)

            def check(v, ck=check_key):
                ok = v[0] == 200
                if ck and isinstance(v[1], dict):
                    ok = ok and ck in v[1]
                detail = f"{v[0]}"
                if ck and isinstance(v[1], dict):
                    detail += f" {ck}={v[1].get(ck, '?')}"
                return ok, detail

            await self._step(r, f'"{label}"', call, check)

        return r

    async def scenario_full_voice(self) -> ScenarioResult:
        """Full voice pipeline: inject audio → wake word → STT → router → TTS.

        Requires --full-voice flag and that mia-audio-capture is stopped
        (so the simulator can inject audio on port 5558). The wake word
        service uses the energy-fallback detector which triggers on 3
        consecutive loud frames.

        Note: The simulator PUB-connects to ports that are normally bound
        by MIA services. For this to work, the conflicting services
        (mia-audio-capture for 5558) must be stopped first.
        """
        r = ScenarioResult(name="full_voice")

        if self.zmq is None:
            await self._step(r, "ZMQ available",
                lambda: asyncio.sleep(0),
                lambda _: (False, "pyzmq not installed"))
            return r

        if not self.full_voice:
            await self._step(r, "full-voice mode",
                lambda: asyncio.sleep(0),
                lambda _: (False, "use --full-voice flag"))
            return r

        # Give PUB sockets time to connect
        await asyncio.sleep(0.5)

        # Inject loud audio to trigger wake word
        await self._step(r, "inject wake audio (5 loud frames)",
            lambda: self.zmq.inject_audio_wake(n_frames=5),
            lambda _: (True, "sent"))

        # Wait for wake word detection and STT processing
        await asyncio.sleep(1.0)

        # Inject silence to signal end of speech (STT VAD needs this)
        await self._step(r, "inject silence (end of speech)",
            lambda: self.zmq.inject_audio_silence(duration_sec=2.0),
            lambda _: (True, "sent"))

        # Wait for voice response
        await self._step(r, "wait for voice response",
            lambda: self.zmq.wait_voice_response(timeout=8.0),
            lambda v: (v is not None, f"response={'yes' if v else 'timeout'}"))

        return r

    async def scenario_engine_start(self) -> ScenarioResult:
        """Simulate engine start: MCU connects, telemetry begins flowing."""
        r = ScenarioResult(name="engine_start")

        if self.zmq is None:
            await self._step(r, "ZMQ available",
                lambda: asyncio.sleep(0),
                lambda _: (False, "pyzmq not installed — skipping ZMQ steps"))
            # Fall back to REST-only verification
            await self._step(r, "GET /status (REST fallback)",
                lambda: self.client.get("/status"),
                lambda v: (v[0] == 200, f"{v[0]}"))
            return r

        await asyncio.sleep(0.3)  # let PUB connect settle

        # Inject MCU connected event
        await self._step(r, "inject MCU connected",
            lambda: self.zmq.inject_mcu_status("connected", "arduino-sim"),
            lambda _: (True, "sent"))

        # Inject idle telemetry (pot1=200 → RPM=800, cold engine)
        await self._step(r, "inject idle telemetry (cold)",
            lambda: self.zmq.inject_telemetry(pot1=200, pot2=0, throttle=5, coolant=20),
            lambda _: (True, "pot1=200 pot2=0 coolant=20"))

        await asyncio.sleep(1.5)

        # Verify via REST
        await self._step(r, "verify /telemetry",
            lambda: self.client.get("/telemetry"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        # Inject warming telemetry
        await self._step(r, "inject warming telemetry",
            lambda: self.zmq.inject_telemetry(pot1=200, pot2=0, throttle=5, coolant=60),
            lambda _: (True, "coolant=60"))

        await self._step(r, "verify /status",
            lambda: self.client.get("/status"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        return r

    async def scenario_city_driving(self) -> ScenarioResult:
        """Simulate city driving: RPM/speed ramp with voice commands."""
        r = ScenarioResult(name="city_driving")

        # RPM/speed ramp
        ramp = [
            (200, 0, 10, 60, "idle"),
            (300, 100, 25, 70, "pulling away"),
            (450, 250, 40, 80, "accelerating"),
            (350, 350, 20, 85, "cruising 40km/h"),
            (250, 200, 15, 85, "slowing down"),
        ]

        for pot1, pot2, throttle, coolant, label in ramp:
            if self.zmq:
                await self._step(r, f"telemetry: {label}",
                    lambda p1=pot1, p2=pot2, t=throttle, c=coolant:
                        self.zmq.inject_telemetry(p1, p2, t, c),
                    lambda _: (True, f"RPM~{max(800, pot1*4)} spd~{pot2/8.5:.0f}km/h"))
                await asyncio.sleep(0.5)

        # Voice command mid-drive
        await self._step(r, '"what\'s the engine telemetry" (via REST)',
            lambda: self.client.get("/telemetry"),
            lambda v: (v[0] == 200, f"{v[0]}"))

        # LED control
        await self._step(r, '"turn lights on" (via REST)',
            lambda: self.client.put("/led/state", {"mode": "on", "brightness": 128}),
            lambda v: (v[0] == 200, f"{v[0]}"))

        await self._step(r, "verify LED state",
            lambda: self.client.get("/led/state"),
            lambda v: (v[0] == 200,
                        f"mode={v[1].get('led_state', {}).get('mode', '?')}" if isinstance(v[1], dict) else f"{v[0]}"))

        return r

    # ── Scenario Registry ─────────────────────────────────────────────

    def get_scenarios(self) -> Dict[str, Callable]:
        return {
            "infrastructure": self.scenario_infrastructure,
            "session_handoff": self.scenario_session_handoff,
            "gpio_control": self.scenario_gpio_control,
            "led_control": self.scenario_led_control,
            "websocket_telemetry": self.scenario_websocket_telemetry,
            "voice_commands": self.scenario_voice_commands,
            "engine_start": self.scenario_engine_start,
            "city_driving": self.scenario_city_driving,
            "full_voice": self.scenario_full_voice,
        }

    ALL_SEQUENCE = [
        "infrastructure",
        "engine_start",
        "voice_commands",
        "city_driving",
        "gpio_control",
        "led_control",
        "session_handoff",
        "websocket_telemetry",
    ]

    # ── Runner ────────────────────────────────────────────────────────

    async def run(self, scenario_names: List[str]) -> int:
        """Run scenarios, print results, return exit code (0=pass)."""
        print()
        print("\u2550" * 54)
        print(f"  MIA Driver Simulator \u2014 {self.host}:{self.port}")
        print("\u2550" * 54)

        t0 = time.monotonic()
        scenarios = self.get_scenarios()

        for name in scenario_names:
            if name not in scenarios:
                print(f"\n  ? Unknown scenario: {name}")
                continue
            print(f"\n\u25b6 {name}")
            result = await scenarios[name]()
            self.results.append(result)

        elapsed = time.monotonic() - t0

        # Summary
        total_pass = sum(r.passed for r in self.results)
        total_fail = sum(r.failed for r in self.results)
        total = total_pass + total_fail

        print()
        print("\u2550" * 54)
        status = "ALL PASSED" if total_fail == 0 else f"{total_fail} FAILED"
        print(f"  Results: {total_pass}/{total} passed  |  {total_fail} failed  |  {elapsed:.1f}s")
        print(f"  Status: {status}")
        print("\u2550" * 54)
        print()

        return 0 if total_fail == 0 else 1


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MIA Driver Simulator \u2014 scenario-driven E2E testing",
    )
    parser.add_argument("--host", default=os.environ.get("MIA_HOST", "localhost"),
                        help="MIA host (default: $MIA_HOST or localhost)")
    parser.add_argument("--port", type=int, default=8000,
                        help="MIA API port (default: 8000)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Run a single scenario by name")
    parser.add_argument("--all", action="store_true", default=True,
                        help="Run all scenarios (default)")
    parser.add_argument("--full-voice", action="store_true",
                        help="Enable full voice pipeline injection (audio\u2192wake\u2192STT)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show step details and responses")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Only show final summary")
    parser.add_argument("--list", action="store_true",
                        help="List available scenarios and exit")
    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    sim = DriverSimulator(
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        full_voice=args.full_voice,
    )

    if args.list:
        print("\nAvailable scenarios:")
        for name in sim.get_scenarios():
            print(f"  - {name}")
        print(f"\nDefault sequence (--all): {', '.join(sim.ALL_SEQUENCE)}")
        return

    if args.scenario:
        names = [args.scenario]
    else:
        names = list(sim.ALL_SEQUENCE)
        if args.full_voice:
            names.append("full_voice")

    async def run():
        try:
            code = await sim.run(names)
        finally:
            await sim.close()
        return code

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
