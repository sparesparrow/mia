"""One oracle for the voice pipeline: collect what it did, then check an ordered subsequence (REQ-VOICE-028).

A ``VoiceTrace`` is a list of normalized events ``{"t", "kind", ...}``. Kinds:

- ``state``      ``state`` (new resting state), optional ``previous``
- ``feedback``   ``state``, ``led``, ``tone``
- ``spoken``     ``text`` (the words), ``phrase`` (the key, when known), optional ``id``
- ``transcript`` ``text``, optional ``source``
- ``settings``   ``verbosity``, ``persona``, ``language``, ``personas``, ``languages``
- ``mic``        ``muted``

Only the stimulus and the tap differ between test layers (machine, router, API, Pi), so the same scenario
steps are checked everywhere. Taps: ``tap_sink`` (a Connection sink fed with envelopes), ``tap_zmq`` (SUB on
the router topics) and ``tap_ws`` (a /ws/voice client from starlette's TestClient). No tap here touches audio.
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

Event = Dict[str, Any]

KINDS = ("state", "feedback", "spoken", "transcript", "settings", "mic")
# A bare step ``{kind: value}`` compares the value with this field of the event.
PRIMARY_FIELD = {
    "state": "state",
    "feedback": "state",
    "spoken": "text",
    "transcript": "text",
    "settings": "language",
    "mic": "muted",
}
DEFAULT_TIMEOUT = 3.0


def normalize_text(text: Any) -> str:
    """Lower case, punctuation stripped, whitespace collapsed: how recognised or spoken text is compared."""
    return " ".join(re.sub(r"[^\w\s]", " ", str(text).lower()).split())


class ExpectationFailed(AssertionError):
    """The trace did not contain the expected steps in order. The message shows both."""


class VoiceTrace:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._t0 = clock()
        self._lock = threading.Lock()
        self._events: List[Event] = []

    # ── collecting ──────────────────────────────────────────────────────────

    def add(self, kind: str, **fields: Any) -> Event:
        if kind not in KINDS:
            raise ValueError(f"unknown event kind: {kind}")
        event: Event = {"t": round(self._clock() - self._t0, 3), "kind": kind, **fields}
        with self._lock:
            self._events.append(event)
        return event

    @property
    def events(self) -> List[Event]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    def add_domain_event(self, event: Any) -> None:
        """A decoded machine event (services.voice_fsm types) as a normalized event."""
        from services.voice_fsm import Feedback, Settings, Speak, StateChanged
        from services.voice_fsm.wire import Transcript

        if isinstance(event, StateChanged):
            self.add("state", state=event.current.value, previous=event.previous.value)
        elif isinstance(event, Feedback):
            self.add("feedback", state=event.state, led=event.led, tone=event.tone)
        elif isinstance(event, Speak):
            self.add("spoken", text=event.text, phrase=event.phrase, id=event.id)
        elif isinstance(event, Transcript):
            fields: Dict[str, Any] = {"text": event.text}
            source = getattr(event, "source", None)
            if source is not None:
                fields["source"] = getattr(source, "value", source)
            self.add("transcript", **fields)
        elif isinstance(event, Settings):
            self.add(
                "settings",
                verbosity=event.verbosity.value,
                persona=event.persona,
                language=event.language,
                personas=list(event.personas),
                languages=list(event.languages),
            )

    # ── taps ────────────────────────────────────────────────────────────────

    def feed_envelope_bytes(self, data: bytes) -> None:
        """One envelope as the wire carries it; replies (no payload) and garbled buffers are ignored."""
        from services.voice_fsm.wire import CodecError, Op, decode_envelope, decode_event

        try:
            envelope = decode_envelope(data)
            if envelope.op != Op.DATA or not envelope.payload:
                return
            self.add_domain_event(decode_event(envelope.payload))
        except CodecError:
            return

    def tap_sink(self) -> Callable[[bytes], None]:
        """A Connection sink (``EnvelopeRouter.connect(trace.tap_sink())``)."""
        return self.feed_envelope_bytes

    def feed_zmq(self, topic: bytes, payload: bytes) -> None:
        """One message from the router's topics (mia/voice/feedback, response, speaking, transcript)."""
        try:
            body = json.loads(payload)
        except ValueError:
            return
        if not isinstance(body, dict):
            return
        name = topic.decode(errors="replace")
        if name == "mia/voice/feedback":
            from services.voice_fsm import State

            self.add("feedback", state=body.get("state"), led=body.get("led"), tone=body.get("tone"))
            if body.get("state") in {s.value for s in State}:  # a resting state is also a state event
                self.add("state", state=body["state"])
        elif name == "mia/voice/response":
            self.add("spoken", text=str(body.get("text", "")), phrase=body.get("phrase", ""))
        elif name == "mia/voice/speaking":
            self.add("mic", muted=body.get("event") == "started", reason="speaking")
        elif name == "mia/voice/transcript":
            self.add("transcript", text=str(body.get("text", "")))

    def tap_zmq(self, endpoints: Iterable[str], topics: Sequence[bytes] = (b"mia/voice/",), context: Any = None):
        """Subscribe to the router's PUB sockets in a thread. Pass your own context or none; never reuse api.main's."""
        tap = ZmqTap(self, list(endpoints), list(topics), context)
        tap.start()
        return tap

    def tap_ws(self, ws: Any):
        """Read envelopes from a connected starlette TestClient websocket in a thread.

        Close the websocket first, then ``stop()`` the tap: the thread ends when the socket does.
        """
        tap = WsTap(self, ws)
        tap.start()
        return tap

    # ── checking ────────────────────────────────────────────────────────────

    def expect(self, steps: Sequence[Any], timeout: float = DEFAULT_TIMEOUT, **kwargs: Any) -> List[Event]:
        return expect(self, steps, timeout, **kwargs)


class ZmqTap:
    def __init__(self, trace: VoiceTrace, endpoints: List[str], topics: List[bytes], context: Any) -> None:
        self._trace = trace
        self._endpoints = endpoints
        self._topics = topics
        self._context = context
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="voice-zmq-tap", daemon=True)

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(5)

    def _run(self) -> None:
        import zmq

        context = self._context or zmq.Context()
        sock = context.socket(zmq.SUB)
        sock.setsockopt(zmq.LINGER, 0)
        for endpoint in self._endpoints:
            sock.connect(endpoint)
        for topic in self._topics:
            sock.setsockopt(zmq.SUBSCRIBE, topic)
        self._ready.set()
        try:
            while not self._stop.is_set():
                if sock.poll(50):
                    frames = sock.recv_multipart()
                    if len(frames) >= 2:
                        self._trace.feed_zmq(frames[0], frames[1])
        finally:
            sock.close()
            if self._context is None:
                context.term()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(5)


class WsTap:
    def __init__(self, trace: VoiceTrace, ws: Any) -> None:
        self._trace = trace
        self._ws = ws
        self._thread = threading.Thread(target=self._run, name="voice-ws-tap", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                data = self._ws.receive_bytes()
            except Exception:  # the socket closed (WebSocketDisconnect) or the portal went away
                return
            self._trace.feed_envelope_bytes(data)

    def stop(self, timeout: float = 5.0) -> None:
        self._thread.join(timeout)


# ── matching ──────────────────────────────────────────────────────────────────


def parse_step(step: Any) -> Tuple[str, Dict[str, Any], Optional[float]]:
    """Return ``(kind, constraints, timeout_or_None)`` for a step such as ``{"spoken": {"contains": "ok"}}``."""
    if not isinstance(step, Mapping):
        raise ValueError(f"a step is a mapping, got {step!r}")
    fields = dict(step)
    timeout = fields.pop("timeout", None)
    kinds = [k for k in fields if k in KINDS]
    if len(kinds) != 1 or len(fields) != 1:
        raise ValueError(f"a step names exactly one of {KINDS} (and optionally timeout): {step!r}")
    kind = kinds[0]
    value = fields[kind]
    constraints = dict(value) if isinstance(value, Mapping) else {PRIMARY_FIELD[kind]: value}
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout < 0):
        raise ValueError(f"timeout must be a non-negative number: {step!r}")
    return kind, constraints, timeout


def matches(event: Event, kind: str, constraints: Mapping[str, Any]) -> bool:
    """``contains`` looks in the normalized words and phrase key; ``text`` and ``phrase`` compare normalized."""
    if event.get("kind") != kind:
        return False
    for key, wanted in constraints.items():
        if key == "contains":
            haystack = normalize_text(event.get("text", "")) + " " + normalize_text(event.get("phrase", ""))
            if normalize_text(wanted) not in haystack:
                return False
        elif key in ("text", "phrase") and isinstance(wanted, str):
            if normalize_text(event.get(key, "")) != normalize_text(wanted):
                return False
        elif event.get(key) != wanted:
            return False
    return True


def describe_step(step: Any) -> str:
    try:
        kind, constraints, timeout = parse_step(step)
    except ValueError:
        return repr(step)
    body = ", ".join(f"{k}={v!r}" for k, v in constraints.items())
    return f"{kind}({body})" + (f" within {timeout:g}s" if timeout is not None else "")


def describe_event(event: Event) -> str:
    fields = ", ".join(f"{k}={v!r}" for k, v in event.items() if k not in ("t", "kind"))
    return f"{event['t']:7.3f}s {event['kind']}({fields})"


def format_diff(steps: Sequence[Any], matched: Sequence[int], seen: Sequence[Event], waited: float) -> str:
    failed = len(matched)
    lines = ["expected, in order:"]
    for i, step in enumerate(steps):
        mark = "ok  " if i < failed else ("FAIL" if i == failed else "    ")
        where = f" (trace #{matched[i]})" if i < failed else ""
        lines.append(f"  [{mark}] {i + 1}. {describe_step(step)}{where}")
    lines.append(f"step {failed + 1} did not appear within {waited:g}s. trace seen:")
    if seen:
        lines.extend(f"  #{i} {describe_event(e)}" for i, e in enumerate(seen))
    else:
        lines.append("  (empty)")
    return "\n".join(lines)


def expect(
    trace: VoiceTrace,
    steps: Sequence[Any],
    timeout: float = DEFAULT_TIMEOUT,
    start: int = 0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll: float = 0.02,
) -> List[Event]:
    """Check that ``steps`` occur in the trace in order, other events allowed in between.

    Each step waits up to its own ``timeout`` (default ``timeout``) from the moment the previous step matched.
    ``start`` is the trace index to begin at. Returns the matched events; raises ``ExpectationFailed`` otherwise.
    ``clock`` and ``sleep`` can be replaced, so a fake clock makes a timeout instant.
    """
    parsed = [parse_step(s) for s in steps]
    cursor = start
    matched: List[int] = []
    results: List[Event] = []
    for kind, constraints, step_timeout in parsed:
        limit = timeout if step_timeout is None else step_timeout
        deadline = clock() + limit
        while True:
            events = trace.events
            hit = next((i for i in range(cursor, len(events)) if matches(events[i], kind, constraints)), None)
            if hit is not None:
                matched.append(hit)
                results.append(events[hit])
                cursor = hit + 1
                break
            if clock() >= deadline:
                raise ExpectationFailed(format_diff(steps, matched, events, limit))
            sleep(poll)
    return results
