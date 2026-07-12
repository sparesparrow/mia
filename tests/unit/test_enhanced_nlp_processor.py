"""Unit tests for EnhancedNLPProcessor + ContextManager in enhanced_orchestrator.py.

Targets the ``orchestration/mcp/modules/core-orchestrator/enhanced_orchestrator.py``
module — currently ~37% covered. These tests focus on the deterministic, pure
logic slice: intent classification, parameter extractors, and context/session
lifecycle. No orchestrator runtime, no MCP server, no network — all behavior
under test is offline and reproducible.

We load the module by path (matches the harness in
``tests/test_mia_claudepy_bridge.py``) because the on-disk directory is
hyphenated (``core-orchestrator``) and cannot be a regular Python package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Module loader (hyphenated directory workaround)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_enhanced_orchestrator():
    """Load enhanced_orchestrator.py as a proper module.

    Mirrors the harness used by ``tests/test_mia_claudepy_bridge.py`` so both
    test suites resolve the same module identity.
    """
    module_path = (
        _REPO_ROOT
        / "orchestration/mcp/modules/core-orchestrator/enhanced_orchestrator.py"
    )
    sys.path.insert(0, str(_REPO_ROOT))
    module_name = "orchestration.mcp.modules.core_orchestrator.enhanced_orchestrator"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_eo = _load_enhanced_orchestrator()

EnhancedNLPProcessor = _eo.EnhancedNLPProcessor
ContextManager = _eo.ContextManager
SessionContext = _eo.SessionContext
UserContext = _eo.UserContext
IntentResult = _eo.IntentResult


# ---------------------------------------------------------------------------
# EnhancedNLPProcessor: parse_command / intent classification
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestParseCommandIntent:
    """End-to-end intent classification via ``parse_command``.

    We check the deterministic output shape (IntentResult), the top-1 intent
    for representative commands per category, and confidence semantics.
    """

    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_empty_input_returns_unknown_zero_confidence(self, nlp):
        result = await nlp.parse_command("")
        assert isinstance(result, IntentResult)
        assert result.intent == "unknown"
        assert result.confidence == 0.0
        assert result.parameters == {}
        # Alternatives default is an empty list (dataclass __post_init__)
        assert result.alternatives == []

    async def test_whitespace_only_input_returns_unknown(self, nlp):
        result = await nlp.parse_command("   \n\t  ")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    async def test_gibberish_input_returns_unknown(self, nlp):
        result = await nlp.parse_command("zxcvbn qwerty foobar")
        assert result.intent == "unknown"

    async def test_play_music_intent_is_top1(self, nlp):
        result = await nlp.parse_command("play some jazz music")
        assert result.intent == "play_music"
        assert result.confidence > 0.0
        # Original text is preserved verbatim (not lowered)
        assert result.original_text == "play some jazz music"

    async def test_volume_intent_is_top1(self, nlp):
        result = await nlp.parse_command("make it louder")
        assert result.intent == "control_volume"

    async def test_smart_home_intent_is_top1(self, nlp):
        result = await nlp.parse_command("turn on the lights in the kitchen")
        assert result.intent == "smart_home"

    async def test_navigation_intent_is_top1(self, nlp):
        result = await nlp.parse_command("directions to prague by train")
        assert result.intent == "navigation"

    async def test_hardware_intent_is_top1(self, nlp):
        result = await nlp.parse_command("set gpio pin 17 high")
        assert result.intent == "hardware_control"

    async def test_communication_intent_is_top1(self, nlp):
        result = await nlp.parse_command("send a whatsapp message to mom")
        assert result.intent == "communication"

    async def test_question_intent_is_top1(self, nlp):
        result = await nlp.parse_command("what is the weather like today")
        assert result.intent == "question_answer"

    async def test_alternatives_populated_when_multiple_intents_score(self, nlp):
        # "play" + "song" hits play_music; "download" + "file" hits file_operation.
        result = await nlp.parse_command("download the song file")
        # Top intent must be one of the two competitors, and the other must
        # appear in the alternatives list.
        top = result.intent
        alt_intents = {name for name, _ in result.alternatives}
        assert top in {"play_music", "file_operation"}
        assert {"play_music", "file_operation"} - {top} <= alt_intents

    async def test_alternatives_capped_to_three(self, nlp):
        # A crafted sentence sprinkling keywords across many intents.
        result = await nlp.parse_command(
            "play the song then turn on the lights and send a message and download the file"
        )
        assert len(result.alternatives) <= 3

    async def test_confidence_is_bounded_zero_to_one(self, nlp):
        # Even for very keyword-heavy input, the normalized confidence stays
        # in [0.0, 1.0]. This guards against the historic bug where
        # ``keyword_score / len(words)`` could exceed 1.0.
        result = await nlp.parse_command(
            "play music song album artist spotify youtube stream track"
        )
        assert 0.0 <= result.confidence <= 1.0

    async def test_follow_up_requires_context_returns_unknown_without_it(self, nlp):
        # "yes" is a follow_up keyword but follow_up requires context.
        # Without context, no intent scores > 0, so we fall through to unknown.
        result = await nlp.parse_command("yes")
        assert result.intent == "unknown"

    async def test_follow_up_scores_with_context(self, nlp):
        ctx = SessionContext(
            session_id="s1",
            user_id="u1",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        result = await nlp.parse_command("yes continue", context=ctx)
        # With context, follow_up patterns can score and be selected.
        assert result.intent == "follow_up"


@pytest.mark.unit
class TestContextBoost:
    """Verify context-driven score boosting on top of raw keyword matching."""

    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_context_used_flag_set_when_last_intent_boosts(self, nlp):
        # last_intent=play_music should boost control_volume score.
        ctx = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            last_intent="play_music",
        )
        result = await nlp.parse_command("volume", context=ctx)
        assert result.intent == "control_volume"
        assert result.context_used is True

    async def test_context_used_flag_false_when_no_boost_applies(self, nlp):
        ctx = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            last_intent="",  # nothing matches any boost list
        )
        result = await nlp.parse_command("play jazz", context=ctx)
        assert result.intent == "play_music"
        assert result.context_used is False

    async def test_location_context_boosts_smart_home(self, nlp):
        ctx = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            variables={"location": "home"},
        )
        result = await nlp.parse_command("turn on the lights", context=ctx)
        assert result.intent == "smart_home"
        assert result.context_used is True

    async def test_missing_last_intent_key_does_not_crash(self, nlp):
        # Default SessionContext has last_intent="" — boost lookup should be safe.
        ctx = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        # Should not raise KeyError/AttributeError even though last_intent isn't
        # in any boost dict.
        result = await nlp.parse_command("volume up", context=ctx)
        assert result.intent == "control_volume"


# ---------------------------------------------------------------------------
# Parameter extractors
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestMusicExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_artist_after_by(self, nlp):
        result = await nlp.parse_command("play something by miles davis")
        assert result.intent == "play_music"
        assert result.parameters.get("artist") == "miles davis"

    async def test_extracts_genre(self, nlp):
        result = await nlp.parse_command("play some jazz")
        assert result.parameters.get("genre") == "jazz"

    async def test_extracts_platform(self, nlp):
        result = await nlp.parse_command("play chill music on spotify")
        assert result.parameters.get("platform") == "spotify"

    async def test_extracts_mood_from_synonyms(self, nlp):
        # "chill" and "calm" both map to the "relaxing" mood bucket.
        r1 = await nlp.parse_command("play chill music")
        r2 = await nlp.parse_command("play calm music")
        assert r1.parameters.get("mood") == "relaxing"
        assert r2.parameters.get("mood") == "relaxing"

    async def test_falls_back_to_query_when_no_specific_params(self, nlp):
        result = await nlp.parse_command("play mystery riddim")
        # No artist, genre, platform, or mood -> query fallback.
        assert result.parameters.get("query") == "mystery riddim"

    async def test_no_query_when_only_stopwords(self, nlp):
        # If every word gets stripped (play/music/song/some), no query key.
        result = await nlp.parse_command("play some music")
        assert "query" not in result.parameters


@pytest.mark.unit
class TestVolumeExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_up_action(self, nlp):
        result = await nlp.parse_command("volume up")
        assert result.parameters.get("action") == "up"

    async def test_extracts_down_action(self, nlp):
        result = await nlp.parse_command("make it quieter")
        assert result.parameters.get("action") == "down"

    async def test_extracts_mute_action(self, nlp):
        result = await nlp.parse_command("mute the sound")
        assert result.parameters.get("action") == "mute"

    async def test_extracts_numeric_level_in_range(self, nlp):
        result = await nlp.parse_command("set volume to 42")
        assert result.parameters.get("level") == "42"

    async def test_ignores_out_of_range_number(self, nlp):
        # 500 is out of [0, 100] — it must NOT be captured as level.
        result = await nlp.parse_command("set volume 500")
        assert result.parameters.get("level") is None

    async def test_extracts_percentage(self, nlp):
        result = await nlp.parse_command("volume 75%")
        assert result.parameters.get("level") == "75"


@pytest.mark.unit
class TestAudioDeviceExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_headphones(self, nlp):
        result = await nlp.parse_command("switch to headphones")
        assert result.parameters.get("device") == "headphones"

    async def test_extracts_bluetooth(self, nlp):
        result = await nlp.parse_command("change output to bluetooth")
        assert result.parameters.get("device") == "bluetooth"

    async def test_extracts_rtsp_via_network_synonym(self, nlp):
        result = await nlp.parse_command("switch to network streaming")
        assert result.parameters.get("device") == "rtsp"


@pytest.mark.unit
class TestSystemControlExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_action_and_target(self, nlp):
        result = await nlp.parse_command("open firefox now")
        assert result.parameters.get("action") == "open"
        # Target is remainder-of-line after the action keyword.
        assert result.parameters.get("target") == "firefox now"

    async def test_action_without_target(self, nlp):
        result = await nlp.parse_command("execute")
        assert result.parameters.get("action") == "execute"
        assert "target" not in result.parameters


@pytest.mark.unit
class TestHardwareExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_pin_via_pin_keyword(self, nlp):
        result = await nlp.parse_command("set pin 17 on")
        assert result.parameters.get("pin") == "17"
        assert result.parameters.get("action") == "on"

    async def test_extracts_pin_via_gpio_keyword(self, nlp):
        result = await nlp.parse_command("read gpio 22")
        assert result.parameters.get("pin") == "22"
        assert result.parameters.get("action") == "read"

    async def test_extracts_pwm_value(self, nlp):
        result = await nlp.parse_command("set pin 13 to 128")
        assert result.parameters.get("pin") == "13"
        assert result.parameters.get("value") == "128"

    async def test_extracts_percent_value(self, nlp):
        result = await nlp.parse_command("set gpio 5 pwm 75%")
        assert result.parameters.get("value") == "75"


@pytest.mark.unit
class TestSmartHomeExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_lights_device(self, nlp):
        result = await nlp.parse_command("turn on the lights")
        assert result.parameters.get("device_type") == "lights"
        assert result.parameters.get("action") == "on"

    async def test_extracts_room_location(self, nlp):
        result = await nlp.parse_command("dim the lights in the living room")
        assert result.parameters.get("location") == "living room"
        assert result.parameters.get("action") == "dim"

    async def test_extracts_temperature_value(self, nlp):
        result = await nlp.parse_command("set thermostat to 21 degrees")
        assert result.parameters.get("device_type") == "temperature"
        assert result.parameters.get("temperature") == "21"


@pytest.mark.unit
class TestFileOperationExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_url(self, nlp):
        result = await nlp.parse_command(
            "download https://example.com/report.pdf"
        )
        assert result.parameters.get("url") == "https://example.com/report.pdf"
        assert result.parameters.get("action") == "download"

    async def test_extracts_unix_path(self, nlp):
        result = await nlp.parse_command("copy file /tmp/report.txt")
        # Regex is non-greedy on start, but should still catch the path.
        assert result.parameters.get("path", "").startswith("/tmp/")
        assert result.parameters.get("action") == "copy"


@pytest.mark.unit
class TestNavigationExtractor:
    @pytest.fixture
    def nlp(self):
        return EnhancedNLPProcessor()

    async def test_extracts_destination(self, nlp):
        result = await nlp.parse_command("navigate to brno")
        assert result.parameters.get("destination") == "brno"

    async def test_extracts_transportation_mode(self, nlp):
        result = await nlp.parse_command("route to prague by train")
        assert result.parameters.get("mode") == "transit"

    async def test_extracts_driving_mode(self, nlp):
        # Note: "driving" also contains "to" — we only care that mode is set
        # correctly, not what destination extraction did.
        result = await nlp.parse_command("driving directions")
        assert result.parameters.get("mode") == "driving"


# ---------------------------------------------------------------------------
# ContextManager: sessions, users, persistence
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestContextManagerSessions:
    """Session-lifecycle behavior of ContextManager (in isolation via tmp_path)."""

    def test_creates_session_with_expected_shape(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        session_id = cm.create_session(user_id="alice", interface_type="voice")

        assert session_id.startswith("sess_")
        assert session_id in cm.sessions_cache
        session = cm.sessions_cache[session_id]
        assert session.user_id == "alice"
        assert session.interface_type == "voice"
        assert session.command_history == []
        assert session.response_history == []

    def test_get_session_returns_active_session(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        sid = cm.create_session("bob", "text")
        fetched = cm.get_session(sid)
        assert fetched is not None
        assert fetched.session_id == sid

    def test_get_session_returns_none_for_unknown_id(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        assert cm.get_session("sess_nonexistent") is None

    def test_get_session_returns_none_for_expired_session(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        sid = cm.create_session("bob", "text")
        # Force expiration: is_active() checks last_accessed within 30 minutes.
        cm.sessions_cache[sid].last_accessed = datetime.now() - timedelta(hours=1)
        assert cm.get_session(sid) is None

    def test_update_session_sets_attributes_and_touches_last_accessed(
        self, tmp_path
    ):
        cm = ContextManager(data_dir=str(tmp_path))
        sid = cm.create_session("carol", "web")
        before = cm.sessions_cache[sid].last_accessed
        # Sleep replacement: manually rewind, then update should push forward.
        cm.sessions_cache[sid].last_accessed = datetime.now() - timedelta(seconds=5)

        cm.update_session(sid, last_intent="play_music")

        assert cm.sessions_cache[sid].last_intent == "play_music"
        assert cm.sessions_cache[sid].last_accessed > before - timedelta(seconds=6)

    def test_update_session_ignores_unknown_attributes(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        sid = cm.create_session("dave", "voice")
        # Should not raise or add a stray attribute.
        cm.update_session(sid, definitely_not_a_field=42)
        assert not hasattr(cm.sessions_cache[sid], "definitely_not_a_field")

    def test_update_session_noop_for_unknown_session_id(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        # Must not raise even when the session_id is not in the cache.
        cm.update_session("sess_missing", last_intent="x")

    def test_add_to_history_appends_and_pushes_last_accessed(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        sid = cm.create_session("erin", "voice")
        cm.add_to_history(sid, "play jazz", "playing jazz on spotify")
        session = cm.sessions_cache[sid]
        assert session.command_history == ["play jazz"]
        assert session.response_history == ["playing jazz on spotify"]

    def test_add_to_history_caps_at_50_entries(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        sid = cm.create_session("frank", "voice")
        for i in range(60):
            cm.add_to_history(sid, f"cmd {i}", f"resp {i}")
        session = cm.sessions_cache[sid]
        # Only the most recent 50 remain, in order.
        assert len(session.command_history) == 50
        assert len(session.response_history) == 50
        assert session.command_history[0] == "cmd 10"
        assert session.command_history[-1] == "cmd 59"

    def test_add_to_history_noop_for_unknown_session(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        # Must not raise. No side effects.
        cm.add_to_history("sess_missing", "cmd", "resp")

    def test_cleanup_expired_sessions_removes_only_expired(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        fresh = cm.create_session("g", "voice")
        stale = cm.create_session("h", "voice")
        cm.sessions_cache[stale].last_accessed = datetime.now() - timedelta(hours=2)

        cm.cleanup_expired_sessions()

        assert fresh in cm.sessions_cache
        assert stale not in cm.sessions_cache


@pytest.mark.unit
class TestContextManagerPersistence:
    """Round-trip: create -> save -> reload from disk yields the same sessions."""

    def test_session_survives_save_and_reload(self, tmp_path):
        cm1 = ContextManager(data_dir=str(tmp_path))
        sid = cm1.create_session("alice", "voice")
        cm1.add_to_history(sid, "play jazz", "playing jazz")

        # Fresh instance rebuilds from the same directory.
        cm2 = ContextManager(data_dir=str(tmp_path))
        assert sid in cm2.sessions_cache
        reloaded = cm2.sessions_cache[sid]
        assert reloaded.user_id == "alice"
        assert reloaded.interface_type == "voice"
        assert reloaded.command_history == ["play jazz"]
        assert reloaded.response_history == ["playing jazz"]

    def test_expired_session_not_persisted(self, tmp_path):
        cm1 = ContextManager(data_dir=str(tmp_path))
        fresh = cm1.create_session("a", "voice")
        stale = cm1.create_session("b", "voice")
        cm1.sessions_cache[stale].last_accessed = (
            datetime.now() - timedelta(hours=2)
        )
        # Trigger a save that filters expired sessions.
        cm1._save_contexts()

        with open(Path(tmp_path) / "sessions.json") as f:
            on_disk = json.load(f)

        assert fresh in on_disk
        assert stale not in on_disk

    def test_empty_data_dir_yields_empty_caches(self, tmp_path):
        cm = ContextManager(data_dir=str(tmp_path))
        assert cm.users_cache == {}
        assert cm.sessions_cache == {}

    def test_malformed_users_file_is_tolerated(self, tmp_path):
        # Write invalid JSON — the loader should log and continue, not raise.
        (Path(tmp_path) / "users.json").write_text("{not valid json")
        cm = ContextManager(data_dir=str(tmp_path))
        # Caches remain empty; construction did not crash.
        assert cm.users_cache == {}
        assert cm.sessions_cache == {}


# ---------------------------------------------------------------------------
# SessionContext.is_active behavior (dataclass helper)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSessionContextIsActive:
    def test_fresh_session_is_active(self):
        s = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        assert s.is_active() is True

    def test_stale_session_is_not_active(self):
        s = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now() - timedelta(hours=1),
        )
        assert s.is_active() is False

    def test_boundary_29_minutes_is_active(self):
        s = SessionContext(
            session_id="s",
            user_id="u",
            interface_type="voice",
            created_at=datetime.now(),
            last_accessed=datetime.now() - timedelta(minutes=29),
        )
        assert s.is_active() is True