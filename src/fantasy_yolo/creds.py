"""Credential loading and redaction.

espn_s2 is a full ESPN/Disney session cookie, not a scoped fantasy token, so
leaking it is account compromise. It is read from a file rather than a config
literal (M-09) and scrubbed from everything leaving the process (J-03).
"""

from __future__ import annotations

import json
import stat
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

REDACTED = "[redacted]"


class Credentials(BaseModel):
    espn_s2: str
    swid: str

    def cookies(self) -> dict[str, str]:
        """Uppercase SWID. Public repos disagree; the design standardises on it."""
        return {"espn_s2": self.espn_s2, "SWID": self.swid}

    def member_id(self) -> str:
        """The braced SWID, as the write envelope's memberId expects."""
        value = self.swid
        if not value.startswith("{"):
            value = "{" + value
        if not value.endswith("}"):
            value = value + "}"
        return value

    def secrets(self) -> list[str]:
        return [self.espn_s2, self.swid, self.swid.strip("{}")]


def load_credentials(path: Path) -> Credentials:
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PermissionError(f"{path} is group- or world-readable; chmod 0600 it")
    return Credentials.model_validate(json.loads(path.read_text()))


def captured_at(path: Path) -> datetime:
    """When cookies were last supplied. ESPN publishes no expiry to read (A-05)."""
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone()


def redact(text: str, creds: Credentials | None) -> str:
    """Scrub credentials from any string leaving the process (J-03)."""
    if creds is None:
        return text
    for secret in creds.secrets():
        if secret:
            text = text.replace(secret, REDACTED)
    return text
