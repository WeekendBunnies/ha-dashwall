"""The integration signs requests exactly as the kiosk expects (a fixed vector the kiosk checks too).

Run: python tests/test_signing.py
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "signing", Path(__file__).parent.parent / "custom_components" / "dashwall" / "signing.py"
)
signing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(signing)

TOKEN = "0123456789abcdef" * 4
EXPECTED = "81c45d0c0257bcebfcebc208d12087ca2dfd2534e9042ff633bdd0836a59fbcd"


def test_known_vector() -> None:
    key = signing.signing_key(TOKEN)
    assert signing.sign(key, "POST", "/api/command", 1791370000, b'{"command":"wake"}') == EXPECTED


def test_any_change_changes_the_signature() -> None:
    key = signing.signing_key(TOKEN)
    base = signing.sign(key, "GET", "/api/state", 1, b"")
    assert base != signing.sign(key, "GET", "/api/events", 1, b"")
    assert base != signing.sign(key, "GET", "/api/state", 2, b"")
    assert base != signing.sign(key, "POST", "/api/state", 1, b"")
    assert base != signing.sign(signing.signing_key(TOKEN[::-1]), "GET", "/api/state", 1, b"")


if __name__ == "__main__":
    test_known_vector()
    test_any_change_changes_the_signature()
    print("signing tests passed")
