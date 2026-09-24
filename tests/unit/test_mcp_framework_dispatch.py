"""Unit tests for MCP Framework message dispatch, dataclasses, and transports.

Focus: pure/logic branches of ``orchestration.mcp.modules.shared.mcp_framework``
that are exercisable without network I/O. Complements the smoke tests in
``test_mcp_framework.py`` by covering the request dispatcher, error paths,
serialization round-trips, and the WebSocketTransport ``closed`` guard.

These tests intentionally avoid asserting on mocks: they assert on the
concrete ``MCPMessage`` values the code returns so a regression in dispatcher
routing or error codes is caught even if the message object is mutated.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from orchestration.mcp.modules.shared.mcp_framework import (
    HTTPTransport,
    MCPClient,
    MCPError,
    MCPMessage,
    MCPServer,
    MessageType,
    Prompt,
    Resource,
    Tool,
    WebSocketTransport,
    create_prompt,
    create_resource,
    create_tool,
)


# ---------------------------------------------------------------------------
# MCPMessage: serialization round-trips
# ---------------------------------------------------------------------------


class TestMCPMessage:
    def test_to_dict_omits_none_fields_but_keeps_jsonrpc(self):
        """to_dict must drop None fields (id/method/params/result/error) but
        always emit ``jsonrpc``. Sending explicit None keys would confuse
        JSON-RPC peers."""
        msg = MCPMessage(id="abc", method="ping")

        d = msg.to_dict()

        assert d == {"id": "abc", "method": "ping", "jsonrpc": "2.0"}
        assert "params" not in d
        assert "result" not in d
        assert "error" not in d

    def test_result_only_message_omits_method(self):
        msg = MCPMessage(id=7, result={"ok": True})
        d = msg.to_dict()
        assert d == {"id": 7, "result": {"ok": True}, "jsonrpc": "2.0"}
        assert "method" not in d

    def test_error_message_carries_error_dict(self):
        err = {"code": -32601, "message": "Method not found"}
        msg = MCPMessage(id=1, error=err)
        d = msg.to_dict()
        assert d["error"] == err
        assert "result" not in d

    def test_to_json_is_parseable_and_round_trips(self):
        original = MCPMessage(
            id="req-1", method="tools/list", params={"cursor": "x"}
        )
        raw = original.to_json()
        parsed = json.loads(raw)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "tools/list"
        assert parsed["params"] == {"cursor": "x"}

        rebuilt = MCPMessage.from_json(raw)
        assert rebuilt.id == original.id
        assert rebuilt.method == original.method
        assert rebuilt.params == original.params

    def test_from_dict_defaults_jsonrpc_when_missing(self):
        """A peer that forgot the ``jsonrpc`` key must still parse — the
        class documents 2.0 as the default so we lock the contract."""
        msg = MCPMessage.from_dict({"id": 1, "method": "ping"})
        assert msg.jsonrpc == "2.0"
        assert msg.id == 1
        assert msg.method == "ping"
        assert msg.params is None
        assert msg.result is None
        assert msg.error is None


# ---------------------------------------------------------------------------
# Dataclass to_dict shape (Tool / Resource / Prompt / MCPError)
# ---------------------------------------------------------------------------


class TestDataclassSerialization:
    def test_tool_to_dict_excludes_handler(self):
        """The ``handler`` field is a Python callable; it must never leak
        into wire payloads via ``to_dict``."""
        tool = Tool(
            name="search",
            description="Search things",
            inputSchema={"type": "object"},
            handler=lambda **kw: "x",
        )
        d = tool.to_dict()
        assert d == {
            "name": "search",
            "description": "Search things",
            "inputSchema": {"type": "object"},
        }
        assert "handler" not in d

    def test_resource_to_dict_includes_mime_when_present(self):
        r = Resource(uri="file://x", name="x", description="d", mimeType="text/plain")
        assert r.to_dict() == {
            "uri": "file://x",
            "name": "x",
            "description": "d",
            "mimeType": "text/plain",
        }

    def test_resource_to_dict_omits_mime_when_absent(self):
        r = Resource(uri="file://y", name="y", description="d")
        d = r.to_dict()
        assert "mimeType" not in d
        assert d == {"uri": "file://y", "name": "y", "description": "d"}

    def test_prompt_to_dict_optional_arguments(self):
        assert create_prompt("p1", "desc").to_dict() == {
            "name": "p1",
            "description": "desc",
        }
        args = [{"name": "q", "type": "string"}]
        assert create_prompt("p2", "d2", arguments=args).to_dict() == {
            "name": "p2",
            "description": "d2",
            "arguments": args,
        }

    def test_mcp_error_to_dict_without_data(self):
        err = MCPError(-32601, "Method not found")
        d = err.to_dict()
        assert d == {"code": -32601, "message": "Method not found"}
        # And ``str(err)`` should include both code and message
        assert "-32601" in str(err)
        assert "Method not found" in str(err)

    def test_mcp_error_to_dict_with_data(self):
        err = MCPError(-32000, "Boom", data={"detail": "why"})
        assert err.to_dict() == {
            "code": -32000,
            "message": "Boom",
            "data": {"detail": "why"},
        }


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


class TestFactoryHelpers:
    def test_create_tool_binds_handler(self):
        def handler(**kw):
            return "ok"

        tool = create_tool("t", "d", {"type": "object"}, handler)
        assert isinstance(tool, Tool)
        assert tool.handler is handler
        assert tool.inputSchema == {"type": "object"}

    def test_create_resource_default_mime_none(self):
        r = create_resource("mem://a", "a", "d")
        assert isinstance(r, Resource)
        assert r.mimeType is None

    def test_create_resource_passes_mime(self):
        r = create_resource("mem://b", "b", "d", mime_type="application/json")
        assert r.mimeType == "application/json"


# ---------------------------------------------------------------------------
# MCPServer registration and dispatcher
# ---------------------------------------------------------------------------


@pytest.fixture
def server_with_tools() -> MCPServer:
    """A server pre-populated with one sync tool, one async tool, one that
    raises, one tool with no handler, and one resource + one prompt."""
    server = MCPServer("t-server", "9.9.9")

    def sync_echo(text: str = "") -> str:
        return f"echo:{text}"

    async def async_add(a: int, b: int) -> int:
        return a + b

    def boom() -> None:
        raise RuntimeError("boom")

    server.add_tool(create_tool("sync_echo", "sync", {"type": "object"}, sync_echo))
    server.add_tool(create_tool("async_add", "async", {"type": "object"}, async_add))
    server.add_tool(create_tool("boom", "raises", {"type": "object"}, boom))
    # Tool registered without a handler (handler=None). ``create_tool``
    # forbids that path (Callable arg is required) so build directly.
    server.add_tool(
        Tool(name="no_handler", description="none", inputSchema={"type": "object"})
    )
    server.add_resource(create_resource("mem://res1", "res1", "r1"))
    server.add_prompt(create_prompt("prompt1", "p1"))
    return server


class TestServerRegistration:
    def test_add_tool_indexes_by_name(self):
        s = MCPServer("s")
        tool = create_tool("x", "d", {"type": "object"}, lambda **kw: 1)
        s.add_tool(tool)
        assert s.tools["x"] is tool

    def test_add_resource_indexes_by_uri(self):
        s = MCPServer("s")
        r = create_resource("mem://k", "k", "d")
        s.add_resource(r)
        assert s.resources["mem://k"] is r

    def test_add_prompt_indexes_by_name(self):
        s = MCPServer("s")
        p = create_prompt("greet", "d")
        s.add_prompt(p)
        # Prompts are stored as an ordered list; look up by name attribute.
        assert any(getattr(pr, "name", None) == "greet" and pr is p for pr in s.prompts)


class TestServerDispatch:
    """Every branch of ``MCPServer.handle_message``. Assertions target the
    ``result``/``error`` payloads on the returned ``MCPMessage`` — real
    behavior, not mock call counts."""

    @pytest.mark.asyncio
    async def test_initialize_flips_state_and_returns_capabilities(
        self, server_with_tools: MCPServer
    ):
        assert server_with_tools.initialized is False
        req = MCPMessage(id=1, method=MessageType.INITIALIZE)

        resp = await server_with_tools.handle_message(req)

        assert resp is not None
        assert resp.id == 1
        assert resp.error is None
        assert server_with_tools.initialized is True
        assert resp.result["protocolVersion"] == "2024-11-05"
        assert resp.result["serverInfo"] == {"name": "t-server", "version": "9.9.9"}
        assert "tools" in resp.result["capabilities"]

    @pytest.mark.asyncio
    async def test_tools_list_returns_registered_tools_without_handler_field(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(id=2, method=MessageType.TOOLS_LIST)
        resp = await server_with_tools.handle_message(req)

        assert resp.error is None
        names = {t["name"] for t in resp.result["tools"]}
        assert {"sync_echo", "async_add", "boom", "no_handler"} <= names
        for entry in resp.result["tools"]:
            assert "handler" not in entry
            assert set(entry.keys()) == {"name", "description", "inputSchema"}

    @pytest.mark.asyncio
    async def test_tools_call_dispatches_sync_handler(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(
            id=3,
            method=MessageType.TOOLS_CALL,
            params={"name": "sync_echo", "arguments": {"text": "hi"}},
        )
        resp = await server_with_tools.handle_message(req)

        assert resp.error is None
        content = resp.result["content"]
        assert content == [{"type": "text", "text": "echo:hi"}]

    @pytest.mark.asyncio
    async def test_tools_call_awaits_coroutine_handler(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(
            id=4,
            method=MessageType.TOOLS_CALL,
            params={"name": "async_add", "arguments": {"a": 2, "b": 40}},
        )
        resp = await server_with_tools.handle_message(req)

        assert resp.error is None
        # The dispatcher stringifies the result.
        assert resp.result["content"][0]["text"] == "42"

    @pytest.mark.asyncio
    async def test_tools_call_missing_params_returns_32602(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(id=5, method=MessageType.TOOLS_CALL, params=None)
        resp = await server_with_tools.handle_message(req)
        assert resp.result is None
        assert resp.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_tools_call_unknown_tool_returns_32602(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(
            id=6,
            method=MessageType.TOOLS_CALL,
            params={"name": "nope", "arguments": {}},
        )
        resp = await server_with_tools.handle_message(req)
        assert resp.error["code"] == -32602
        assert "nope" in resp.error["message"]

    @pytest.mark.asyncio
    async def test_tools_call_tool_without_handler_returns_32603(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(
            id=7,
            method=MessageType.TOOLS_CALL,
            params={"name": "no_handler", "arguments": {}},
        )
        resp = await server_with_tools.handle_message(req)
        assert resp.error["code"] == -32603
        assert "no_handler" in resp.error["message"]

    @pytest.mark.asyncio
    async def test_tools_call_handler_exception_becomes_32603(
        self, server_with_tools: MCPServer
    ):
        req = MCPMessage(
            id=8,
            method=MessageType.TOOLS_CALL,
            params={"name": "boom", "arguments": {}},
        )
        resp = await server_with_tools.handle_message(req)
        assert resp.error["code"] == -32603
        assert "boom" in resp.error["message"]

    @pytest.mark.asyncio
    async def test_resources_list_and_read(self, server_with_tools: MCPServer):
        lst = await server_with_tools.handle_message(
            MCPMessage(id=9, method=MessageType.RESOURCES_LIST)
        )
        assert lst.error is None
        uris = [r["uri"] for r in lst.result["resources"]]
        assert "mem://res1" in uris

        read = await server_with_tools.handle_message(
            MCPMessage(
                id=10,
                method=MessageType.RESOURCES_READ,
                params={"uri": "mem://res1"},
            )
        )
        assert read.error is None
        assert read.result["contents"][0]["uri"] == "mem://res1"
        # Default mimeType fallback when Resource has no mime type set.
        assert read.result["contents"][0]["mimeType"] == "text/plain"

    @pytest.mark.asyncio
    async def test_resources_read_missing_params(self, server_with_tools: MCPServer):
        resp = await server_with_tools.handle_message(
            MCPMessage(id=11, method=MessageType.RESOURCES_READ, params=None)
        )
        assert resp.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_resources_read_unknown_uri(self, server_with_tools: MCPServer):
        resp = await server_with_tools.handle_message(
            MCPMessage(
                id=12,
                method=MessageType.RESOURCES_READ,
                params={"uri": "mem://nope"},
            )
        )
        assert resp.error["code"] == -32602
        assert "nope" in resp.error["message"]

    @pytest.mark.asyncio
    async def test_prompts_list_and_get(self, server_with_tools: MCPServer):
        lst = await server_with_tools.handle_message(
            MCPMessage(id=13, method=MessageType.PROMPTS_LIST)
        )
        assert lst.error is None
        names = [p["name"] for p in lst.result["prompts"]]
        assert "prompt1" in names

        got = await server_with_tools.handle_message(
            MCPMessage(
                id=14,
                method=MessageType.PROMPTS_GET,
                params={"name": "prompt1"},
            )
        )
        assert got.error is None
        assert got.result["description"] == "p1"
        assert got.result["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_prompts_get_missing_params(self, server_with_tools: MCPServer):
        resp = await server_with_tools.handle_message(
            MCPMessage(id=15, method=MessageType.PROMPTS_GET, params=None)
        )
        assert resp.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_prompts_get_unknown_name(self, server_with_tools: MCPServer):
        resp = await server_with_tools.handle_message(
            MCPMessage(
                id=16, method=MessageType.PROMPTS_GET, params={"name": "unknown"}
            )
        )
        assert resp.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_ping_returns_empty_result(self, server_with_tools: MCPServer):
        resp = await server_with_tools.handle_message(
            MCPMessage(id=17, method=MessageType.PING)
        )
        assert resp.error is None
        assert resp.result == {}

    @pytest.mark.asyncio
    async def test_shutdown_flips_running_flag(self, server_with_tools: MCPServer):
        server_with_tools.running = True
        resp = await server_with_tools.handle_message(
            MCPMessage(id=18, method=MessageType.SHUTDOWN)
        )
        assert resp.error is None
        assert resp.result == {}
        assert server_with_tools.running is False

    @pytest.mark.asyncio
    async def test_unknown_method_returns_method_not_found(
        self, server_with_tools: MCPServer
    ):
        resp = await server_with_tools.handle_message(
            MCPMessage(id=19, method="something/unknown")
        )
        assert resp.result is None
        assert resp.error["code"] == -32601
        assert "something/unknown" in resp.error["message"]

    @pytest.mark.asyncio
    async def test_dispatcher_wraps_internal_exception_as_32603(self, monkeypatch):
        """If an internal handler raises unexpectedly (not an MCPError), the
        dispatcher must catch it and produce a JSON-RPC -32603 response
        instead of propagating."""
        s = MCPServer("s")

        async def _bad_handler(_msg):
            raise ValueError("kaboom internals")

        # Force the initialize branch to raise.
        monkeypatch.setattr(s, "_handle_initialize", _bad_handler)

        resp = await s.handle_message(
            MCPMessage(id=42, method=MessageType.INITIALIZE)
        )
        assert resp is not None
        assert resp.error is not None
        assert resp.error["code"] == -32603
        assert "kaboom internals" in resp.error["message"]


# ---------------------------------------------------------------------------
# WebSocketTransport: send/receive/close guard behavior
# ---------------------------------------------------------------------------


class _FakeWebSocket:
    """Minimal duck-typed stand-in. Records sent payloads and yields queued
    receives so we don't need a real websocket server."""

    def __init__(self, inbound=None):
        self.sent: list[str] = []
        self._inbound = list(inbound or [])
        self.close_called = False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if not self._inbound:
            raise AssertionError("recv called with empty inbound queue")
        return self._inbound.pop(0)

    async def close(self) -> None:
        self.close_called = True


class TestWebSocketTransport:
    @pytest.mark.asyncio
    async def test_send_serializes_message_to_json(self):
        ws = _FakeWebSocket()
        t = WebSocketTransport(ws)

        await t.send(MCPMessage(id=1, method="ping"))

        assert len(ws.sent) == 1
        payload = json.loads(ws.sent[0])
        assert payload["method"] == "ping"
        assert payload["id"] == 1
        assert payload["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_receive_parses_incoming_json(self):
        inbound = json.dumps({"jsonrpc": "2.0", "id": 5, "result": {"ok": True}})
        ws = _FakeWebSocket(inbound=[inbound])
        t = WebSocketTransport(ws)

        msg = await t.receive()

        assert isinstance(msg, MCPMessage)
        assert msg.id == 5
        assert msg.result == {"ok": True}

    @pytest.mark.asyncio
    async def test_send_after_close_raises_connection_closed_mcp_error(self):
        ws = _FakeWebSocket()
        t = WebSocketTransport(ws)
        await t.close()
        assert t.closed is True
        assert ws.close_called is True

        with pytest.raises(MCPError) as exc:
            await t.send(MCPMessage(id=1, method="ping"))
        assert exc.value.code == -32000

    @pytest.mark.asyncio
    async def test_receive_after_close_raises_connection_closed_mcp_error(self):
        ws = _FakeWebSocket()
        t = WebSocketTransport(ws)
        await t.close()

        with pytest.raises(MCPError) as exc:
            await t.receive()
        assert exc.value.code == -32000

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """Calling close twice must not raise and must not call the
        underlying websocket.close twice."""
        ws = _FakeWebSocket()
        t = WebSocketTransport(ws)

        await t.close()
        await t.close()  # second close must be a no-op

        assert t.closed is True
        # The underlying close should only have been invoked on the first call.
        # _FakeWebSocket.close_called is a boolean so we assert it via a
        # side counter here.
        # We didn't count calls, but we can assert the guard by re-checking
        # ws was not invoked while ``closed`` was already True: we verify by
        # patching the method after the first close.
        called = 0

        async def _counter():
            nonlocal called
            called += 1

        ws.close = _counter  # type: ignore[assignment]
        await t.close()
        assert called == 0

    @pytest.mark.asyncio
    async def test_send_wraps_unexpected_exception_as_internal_error(self):
        """A non-ConnectionClosed exception during send should surface as
        MCPError(-32603) (the ``Exception`` branch)."""

        class _BoomWS(_FakeWebSocket):
            async def send(self, data: str) -> None:  # noqa: D401
                raise RuntimeError("network hiccup")

        t = WebSocketTransport(_BoomWS())
        with pytest.raises(MCPError) as exc:
            await t.send(MCPMessage(id=1, method="ping"))
        assert exc.value.code == -32603
        assert "network hiccup" in exc.value.message


# ---------------------------------------------------------------------------
# HTTPTransport: receive is documented as unsupported
# ---------------------------------------------------------------------------


class TestHTTPTransport:
    @pytest.mark.asyncio
    async def test_receive_is_not_implemented(self):
        """HTTP is documented as request/response only; receive must raise
        NotImplementedError so callers don't silently hang."""
        # We can pass ``None`` for session and url because receive short-
        # circuits before touching them.
        t = HTTPTransport(session=None, url="http://example/mcp")  # type: ignore[arg-type]
        with pytest.raises(NotImplementedError):
            await t.receive()


# ---------------------------------------------------------------------------
# MCPClient: request-send guards
# ---------------------------------------------------------------------------


class TestMCPClientGuards:
    @pytest.mark.asyncio
    async def test_send_request_without_transport_raises_internal_error(self):
        """Calling any request-issuing method before ``connect`` must raise
        MCPError(-32603) rather than dereferencing a None transport."""
        client = MCPClient()
        assert client.transport is None
        assert client.connected is False

        with pytest.raises(MCPError) as exc:
            await client._send_request(
                MCPMessage(id=1, method=MessageType.PING), timeout=0.1
            )
        assert exc.value.code == -32603

    def test_next_id_is_monotonic(self):
        client = MCPClient()
        first = client._next_id()
        second = client._next_id()
        third = client._next_id()
        assert (first, second, third) == (1, 2, 3)

    @pytest.mark.asyncio
    async def test_send_request_times_out_and_cleans_pending(self):
        """When the transport swallows the send and never yields a response,
        ``_send_request`` should time out with MCPError(-32000) AND clear
        the pending future from the registry."""

        class _NoReplyTransport:
            async def send(self, message):
                # Pretend the message went out; never resolve the future.
                return None

            async def receive(self):  # pragma: no cover - not used in this path
                raise AssertionError("should not be called")

            async def close(self):  # pragma: no cover - not used in this path
                return None

        client = MCPClient()
        client.transport = _NoReplyTransport()  # type: ignore[assignment]
        client.connected = True

        req = MCPMessage(id=client._next_id(), method=MessageType.PING)
        with pytest.raises(MCPError) as exc:
            await client._send_request(req, timeout=0.05)
        assert exc.value.code == -32000
        assert req.id not in client.pending_requests

    @pytest.mark.asyncio
    async def test_handle_message_resolves_matching_pending_request(self):
        """The client's inbound message router must resolve the pending
        future keyed by response ``id`` and clear the entry."""
        client = MCPClient()
        pending_id = 123
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        client.pending_requests[pending_id] = fut

        response = MCPMessage(id=pending_id, result={"ok": True})
        await client._handle_message(response)

        assert fut.done()
        assert fut.result() is response
        assert pending_id not in client.pending_requests
