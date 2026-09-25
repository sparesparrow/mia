"""Source-level proof that the ESP32 listen-only build cannot transmit on CAN.

The firmware selects its bus mode with the ``MIA_TWAI_LISTEN_ONLY`` macro. These
tests strip comments, walk the preprocessor conditionals and assert that every
``twai_transmit(`` call sits in a branch that is compiled out when the macro is
set, while the passive branch still receives and emits frames. CI additionally
checks the listen-only ELF for the ``twai_transmit`` symbol.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_DIR = ROOT / "apps" / "esp32" / "firmware-obd"
OBD_SOURCE = FIRMWARE_DIR / "components" / "ai_servis_obd" / "ai_servis_obd.c"

_TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.DOTALL)
_MACRO = "MIA_TWAI_LISTEN_ONLY"


def _strip_comments(source):
    """Remove C comments, keeping string literals and line numbering intact."""

    def replace(match):
        token = match.group(0)
        if token.startswith("/"):
            return "\n" * token.count("\n")
        return token

    return _TOKEN.sub(replace, source)


def _classify_lines(source):
    """Yield (line, mode) where mode is 'active', 'passive' or None.

    'active' means the line is only compiled when MIA_TWAI_LISTEN_ONLY is 0,
    'passive' means only when it is 1, None means both (or undecidable).
    """
    stack = []
    for line in _strip_comments(source).splitlines():
        directive = line.strip()
        if re.match(rf"#\s*if\s+!\s*{_MACRO}\b", directive):
            stack.append("active")
        elif re.match(rf"#\s*if\s+{_MACRO}\b", directive):
            stack.append("passive")
        elif re.match(r"#\s*(if|ifdef|ifndef)\b", directive):
            stack.append(None)
        elif re.match(r"#\s*elif\b", directive):
            stack[-1] = None
        elif re.match(r"#\s*else\b", directive):
            stack[-1] = {"active": "passive", "passive": "active"}.get(stack[-1])
        elif re.match(r"#\s*endif\b", directive):
            stack.pop()
        modes = {mode for mode in stack if mode}
        yield line, (modes.pop() if len(modes) == 1 else None)


def _firmware_sources():
    return sorted(p for p in FIRMWARE_DIR.rglob("*") if p.suffix in {".c", ".h", ".cpp"} and "build" not in p.parts)


def test_every_transmit_call_is_compiled_out_of_the_listen_only_build():
    calls = []
    for path in _firmware_sources():
        for line, mode in _classify_lines(path.read_text(encoding="utf-8")):
            if re.search(r"\btwai_transmit\s*\(", line):
                calls.append((path.name, mode))
    assert calls, "expected the normal build to transmit OBD requests"
    assert all(mode == "active" for _, mode in calls), calls


def test_passive_build_receives_and_emits_frames():
    passive = [line for line, mode in _classify_lines(OBD_SOURCE.read_text(encoding="utf-8")) if mode == "passive"]
    passive_source = "\n".join(passive)
    assert "TWAI_MODE_LISTEN_ONLY" in passive_source
    assert re.search(r"\btwai_receive\s*\(", passive_source)
    assert re.search(r"\bemit_passive_can_frame\s*\(", passive_source)


def test_classifier_handles_else_branches():
    source = "#if MIA_TWAI_LISTEN_ONLY\npassive();\n#else\nactive(); // twai_transmit(\n#endif\nboth();\n"
    modes = dict(_classify_lines(source))
    assert modes["passive();"] == "passive"
    assert modes["active(); "] == "active"
    assert modes["both();"] is None
