"""Request signing for the kiosk's local API (the kiosk verifies the same way).

key       = lowercase hex sha256(pairing token)
message   = METHOD "\\n" PATH "\\n" UNIX-SECONDS "\\n" lowercase hex sha256(body)
signature = lowercase hex HMAC-SHA256(key, message)

No Home Assistant imports, so tests/test_signing.py can load it on its own.
"""

from __future__ import annotations

import hashlib
import hmac


def signing_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sign(key: str, method: str, path: str, timestamp: int, body: bytes) -> str:
    message = f"{method}\n{path}\n{timestamp}\n{hashlib.sha256(body).hexdigest()}"
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
