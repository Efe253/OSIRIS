"""security.py testleri — SSRF ve enjeksiyon korumaları."""

import pytest
from osiris.security import (
    assert_safe_url,
    cap_list,
    is_blocked_host,
    mask_secret,
    safe_title,
    sanitize_channel,
    sanitize_domain,
    sanitize_hostname,
    sanitize_irc_token,
)


def test_public_url_ok() -> None:
    assert assert_safe_url("https://example.com/a?q=1") == "https://example.com/a?q=1"


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data",
    "http://localhost:8000/x",
    "http://127.0.0.1/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://172.16.0.1/",
    "file:///etc/passwd",
    "ftp://x.com/f",
    "http://user:pass@example.com/",
    "http://abc.onion/",
    "http://example.com:99999/",
    "",
    "x" * 3000,
])
def test_blocked_urls(url: str) -> None:
    with pytest.raises(ValueError):
        assert_safe_url(url)


def test_onion_allowed_for_tor() -> None:
    assert assert_safe_url("http://abc.onion/", allow_onion=True)


def test_is_blocked_host() -> None:
    assert is_blocked_host("localhost")
    assert is_blocked_host("")
    assert is_blocked_host("10.1.2.3")
    # .invalid TLD asla çözülmez → fail-closed
    assert is_blocked_host("yok-boyle-host.invalid")


def test_sanitize_domain() -> None:
    assert sanitize_domain("Example.COM.") == "example.com"
    for bad in ["a\r\nBCC:x", "x y", "nodot", "a" * 300, "x/y", "-.com", ""]:
        with pytest.raises(ValueError):
            sanitize_domain(bad)


def test_sanitize_channel_and_nick() -> None:
    assert sanitize_channel("#osiris") == "#osiris"
    for bad in ["general", "#a\r\nJOIN #b", "#a,b", "", "x" * 100]:
        with pytest.raises(ValueError):
            sanitize_channel(bad)
    assert sanitize_irc_token("osiris-bot") == "osiris-bot"
    for bad in ["nick\r\nCMD", "a b", "a,b", "", "x" * 100]:
        with pytest.raises(ValueError):
            sanitize_irc_token(bad)


def test_sanitize_hostname() -> None:
    assert sanitize_hostname("Example.COM") == "example.com"
    for bad in ["", "a/b", "x" * 300, "a\rb"]:
        with pytest.raises(ValueError):
            sanitize_hostname(bad)


def test_safe_title() -> None:
    from bs4 import BeautifulSoup

    assert safe_title(None) is None
    assert safe_title(BeautifulSoup("<html></html>", "html.parser")) is None
    soup = BeautifulSoup("<html><head><title>Hi</title></head></html>", "html.parser")
    assert safe_title(soup) == "Hi"


def test_cap_list_and_mask() -> None:
    assert cap_list([1, 2, 3], 2) == [1, 2]
    assert cap_list("notalist", 2) == []
    assert mask_secret(None) == "***"
    assert mask_secret("abcdef") == "**cdef"
    assert mask_secret("ab") == "***"
