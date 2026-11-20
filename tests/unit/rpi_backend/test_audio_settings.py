"""The Pi owns where the microphone comes from and where replies are heard, and says what it cannot do (REQ-VOICE-030)."""

import json

import pytest
from api import main as api_main
from api.routers import audio_settings
from fastapi.testclient import TestClient

pytestmark = pytest.mark.req("REQ-VOICE-030")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("MIA_AUTH_DISABLED", "1")
    monkeypatch.setattr(audio_settings, "bluetooth_audio_available", lambda: False)
    return TestClient(api_main.app)


def test_defaults_are_wifi_microphone_and_pi_speaker_and_bluetooth_is_reported_unavailable(client):
    body = client.get("/audio/settings").json()
    assert (body["mic_transport"], body["reply_output"]) == ("wifi", "pi_speaker")
    caps = body["capabilities"]
    assert caps["bt_audio_available"] is False
    assert caps["mic_transport"] == {"wifi": True, "bluetooth": False}
    assert caps["reply_output"] == {"pi_speaker": True, "bluetooth_phone": False, "phone_speaker": False}


@pytest.mark.parametrize(
    "payload",
    [{"mic_transport": "bluetooth"}, {"reply_output": "bluetooth_phone"}, {"reply_output": "phone_speaker"}],
)
def test_an_unavailable_choice_is_refused_and_not_stored(client, tmp_path, payload):
    response = client.put("/audio/settings", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "unavailable"
    assert not (tmp_path / audio_settings.FILE_NAME).exists()
    assert client.get("/audio/settings").json()["reply_output"] == "pi_speaker"


def test_an_unknown_value_is_a_client_error(client):
    assert client.put("/audio/settings", json={"mic_transport": "carrier_pigeon"}).status_code == 422


def test_an_available_choice_is_stored_and_read_back(client, tmp_path):
    response = client.put("/audio/settings", json={"mic_transport": "wifi", "reply_output": "pi_speaker"})
    assert response.status_code == 200
    stored = json.loads((tmp_path / audio_settings.FILE_NAME).read_text())
    assert stored == {"mic_transport": "wifi", "reply_output": "pi_speaker"}


def test_it_never_touches_the_voice_settings_file(client, tmp_path):
    voice = tmp_path / "voice_settings.json"
    voice.write_text('{"verbosity": "quiet"}')
    client.put("/audio/settings", json={"reply_output": "pi_speaker"})
    assert voice.read_text() == '{"verbosity": "quiet"}'


def test_a_damaged_file_gives_the_defaults(client, tmp_path):
    (tmp_path / audio_settings.FILE_NAME).write_text("{not json")
    assert client.get("/audio/settings").json()["mic_transport"] == "wifi"


def test_a_stored_choice_the_pi_can_no_longer_serve_is_reported_not_followed(client, tmp_path):
    (tmp_path / audio_settings.FILE_NAME).write_text(
        json.dumps({"mic_transport": "wifi", "reply_output": "bluetooth_phone"})
    )
    body = client.get("/audio/settings").json()
    assert body["reply_output"] == "bluetooth_phone"
    assert body["effective"]["reply_output"] == "pi_speaker"


def test_the_probe_finds_no_bluetooth_audio_without_a_daemon(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_settings.shutil, "which", lambda name: None)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert audio_settings.bluetooth_audio_available() is False
    (tmp_path / "pipewire-0").touch()
    assert audio_settings.bluetooth_audio_available() is True
