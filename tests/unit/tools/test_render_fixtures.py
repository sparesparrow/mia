"""tools/voice/render_fixtures.py: phrases, conversion and the manifest, with a fake synthesizer (REQ-VOICE-028).

No speech engine is needed or run.
"""

import importlib.util
import json
import math
import struct
import wave
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-VOICE-028")

TOOL = Path(__file__).resolve().parents[3] / "tools" / "voice" / "render_fixtures.py"
spec = importlib.util.spec_from_file_location("render_fixtures", TOOL)
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)


def fake_synth(rate=22050, channels=2, seconds=0.5):
    """A tone whose pitch depends on the text, as a WAV at an engine-like rate and channel count."""

    def synthesize(text, target):
        hz = 200 + 10 * len(text)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * hz * i / rate))) * channels
            for i in range(int(rate * seconds))
        )
        with wave.open(str(target), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(frames)

    return synthesize


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    # tmp_path is outside the repository; pretend the repository is elsewhere so the guard is exercised separately.
    return tmp_path / "fixtures"


def test_the_committed_phrase_list_is_valid_and_unique():
    phrases = rf.load_phrases(rf.DEFAULT_PHRASES)
    assert {"turn the lights off", "what is the status", "be quiet", "yes", "no", "cancel"} <= set(phrases)
    assert len({rf.slug(p) for p in phrases}) == len(phrases)


@pytest.mark.parametrize(
    "content, message",
    [
        ("phrases: []", "non-empty"),
        ("phrases: [yes, 5]", "non-empty string"),
        ("phrases: ['!!!']", "no letters"),
        ("phrases: ['Yes!', 'yes']", "both be yes.wav"),
        ("- yes", "non-empty 'phrases'"),
    ],
)
def test_a_bad_phrase_list_is_rejected(tmp_path, content, message):
    path = tmp_path / "p.yaml"
    path.write_text(content)
    with pytest.raises(rf.RenderError, match=message):
        rf.load_phrases(path)


def test_rendering_writes_16k_mono_wavs_and_a_matching_manifest(out_dir):
    manifest = rf.render(["be quiet", "yes"], out_dir, fake_synth(), engine="fake")
    assert sorted(manifest["files"]) == ["be_quiet.wav", "yes.wav"]
    with wave.open(str(out_dir / "be_quiet.wav"), "rb") as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (16000, 1, 2)
        assert wav.getnframes() == pytest.approx(8000, abs=2)  # 0.5 s resampled from 22.05 kHz
    saved = json.loads((out_dir / "manifest.json").read_text())
    assert saved == manifest
    entry = saved["files"]["yes.wav"]
    assert entry["phrase"] == "yes" and entry["sha256"] == rf.sha256_of(out_dir / "yes.wav")
    assert entry["seconds"] == pytest.approx(0.5, abs=0.01)
    assert rf.verify(out_dir) == []


def test_the_same_input_gives_the_same_hashes(tmp_path):
    first = rf.render(["cancel"], tmp_path / "a", fake_synth())
    second = rf.render(["cancel"], tmp_path / "b", fake_synth())
    assert first["files"] == second["files"]


def test_verify_reports_a_changed_or_missing_file(out_dir):
    rf.render(["no", "cancel"], out_dir, fake_synth())
    (out_dir / "no.wav").write_bytes(b"changed")
    (out_dir / "cancel.wav").unlink()
    assert sorted(rf.verify(out_dir)) == ["cancel.wav: missing", "no.wav: sha256 differs from the manifest"]
    assert rf.verify(out_dir / "nowhere")


def test_a_synthesizer_that_writes_nothing_is_an_error(out_dir):
    with pytest.raises(rf.RenderError, match="wrote nothing"):
        rf.render(["yes"], out_dir, lambda text, target: None)


def test_fixtures_cannot_be_rendered_into_the_repository():
    with pytest.raises(rf.RenderError, match="inside the repository"):
        rf.render(["yes"], rf.REPO_ROOT / "tests" / "fixtures" / "voice", fake_synth())


def test_without_an_engine_the_tool_stops_with_a_clear_error(monkeypatch, capsys, out_dir):
    monkeypatch.setattr(rf.shutil, "which", lambda name: None)
    assert rf.main(["--out", str(out_dir)]) == 2
    assert "install espeak-ng" in capsys.readouterr().err
    assert not out_dir.exists()


def test_piper_needs_a_model(monkeypatch):
    monkeypatch.setattr(rf.shutil, "which", lambda name: f"/usr/bin/{name}")
    with pytest.raises(rf.RenderError, match="--piper-model"):
        rf.pick_engine("piper", None)
    assert rf.pick_engine("auto", None)[0] == "espeak-ng"
    assert rf.pick_engine("auto", "voice.onnx")[0] == "piper"


def test_an_engine_that_is_installed_is_called_with_the_text(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(rf.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)))
    rf.espeak_synthesizer("/usr/bin/espeak-ng")("be quiet", tmp_path / "x.wav")
    assert calls[0][0][-2:] == ["--", "be quiet"] and "-w" in calls[0][0]
    rf.piper_synthesizer("/usr/bin/piper", "v.onnx")("yes", tmp_path / "y.wav")
    assert calls[1][1]["input"] == b"yes"
