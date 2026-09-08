import json

import pytest

from fantasy_yolo.creds import Credentials, load_credentials, redact

CREDS = Credentials(espn_s2="SECRET_S2_VALUE", swid="{ABC-123}")


def test_cookies_use_uppercase_swid():
    assert CREDS.cookies() == {"espn_s2": "SECRET_S2_VALUE", "SWID": "{ABC-123}"}


def test_member_id_keeps_the_braces():
    assert CREDS.member_id() == "{ABC-123}"


def test_member_id_adds_missing_braces():
    assert Credentials(espn_s2="x", swid="ABC-123").member_id() == "{ABC-123}"


def test_redact_removes_the_session_cookie():
    assert "SECRET_S2_VALUE" not in redact("cookie=SECRET_S2_VALUE bad", CREDS)


def test_redact_removes_the_swid():
    assert "ABC-123" not in redact("swid {ABC-123} here", CREDS)


def test_redact_is_a_noop_without_credentials():
    assert redact("plain text", None) == "plain text"


def test_load_credentials_rejects_a_world_readable_file(tmp_path):
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({"espn_s2": "a", "swid": "{b}"}))
    p.chmod(0o644)
    with pytest.raises(PermissionError, match="0600"):
        load_credentials(p)


def test_load_credentials_reads_a_private_file(tmp_path):
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({"espn_s2": "a", "swid": "{b}"}))
    p.chmod(0o600)
    assert load_credentials(p).espn_s2 == "a"
