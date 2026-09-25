from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "apps/esp32/firmware-obd/components/ai_servis_obd/ai_servis_obd.c"


def test_transmit_is_compile_time_excluded():
    source = FIRMWARE.read_text()
    assert source.count("twai_transmit(") == 1
    tx = source.index("twai_transmit(")
    guard = source.index("#if !MIA_TWAI_LISTEN_ONLY")
    end = source.index("#endif", guard)
    assert guard < tx < end


def test_passive_build_emits_frames_without_transmit():
    source = FIRMWARE.read_text()
    assert "TWAI_MODE_LISTEN_ONLY" in source
    assert "twai_receive(&message" in source
    assert "emit_passive_can_frame" in source
