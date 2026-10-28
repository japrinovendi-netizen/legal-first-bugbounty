"""
Uji unit untuk logika pencocokan scope engagement_guard (fungsi murni, tanpa I/O).

Menutup:
  - F-001: entri wildcard `*.example.com` (sub-domain saja, bukan apex).
  - F-002: entri label-tunggal/TLD (`com`, `*.com`) TIDAK boleh meloloskan seluruh
           TLD (fail-OPEN) — hanya exact match untuk label tunggal (`localhost`).
  - F-010: normalisasi input/entri (skema, port, userinfo, trailing-dot).
  - Regresi: scope hanya menyempit ke bawah (apex/induk TIDAK terotorisasi).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from engagement_guard import _host_matches_scope, _normalize_host  # noqa: E402


# ───────────────────────── _normalize_host (F-010) ─────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("app.target.com", "app.target.com"),
    ("App.Target.COM", "app.target.com"),
    ("https://app.target.com:8443/path", "app.target.com"),
    ("http://user:pass@app.target.com/x", "app.target.com"),
    ("127.0.0.1:8099", "127.0.0.1"),
    ("app.target.com.", "app.target.com"),          # FQDN trailing-dot
    ("app.target.com/", "app.target.com"),
    ("", ""),
    (None, ""),
])
def test_normalize_host(raw, expected):
    assert _normalize_host(raw) == expected


# ───────────────────────── exact & sub-domain (dasar) ─────────────────────────
def test_exact_match():
    assert _host_matches_scope("app.target.com", ["app.target.com"])


def test_subdomain_authorized():
    assert _host_matches_scope("api.app.target.com", ["app.target.com"])


def test_unrelated_host_blocked():
    assert not _host_matches_scope("evil.example", ["app.target.com"])


# ───────────────────────── regresi: tidak melebar ke atas ─────────────────────────
def test_apex_not_authorized():
    # in_scope sub-domain TIDAK mengotorisasi induk/apex-nya
    assert not _host_matches_scope("target.com", ["app.target.com"])


# ───────────────────────── F-002: bare-TLD fail-OPEN ─────────────────────────
def test_bare_tld_does_not_authorize_whole_tld():
    assert not _host_matches_scope("victim.com", ["com"])
    assert not _host_matches_scope("anything.com", ["com"])


def test_bare_label_exact_match_still_ok():
    # label tunggal valid (mis. localhost) tetap boleh EXACT match
    assert _host_matches_scope("localhost", ["localhost"])
    assert not _host_matches_scope("evil.localhost", ["localhost"])


def test_ip_scope_exact_and_sub():
    assert _host_matches_scope("127.0.0.1", ["127.0.0.1"])
    assert not _host_matches_scope("127.0.0.2", ["127.0.0.1"])


# ───────────────────────── F-001: wildcard ─────────────────────────
def test_wildcard_authorizes_subdomains():
    assert _host_matches_scope("a.example.com", ["*.example.com"])
    assert _host_matches_scope("x.y.example.com", ["*.example.com"])


def test_wildcard_does_not_authorize_apex():
    assert not _host_matches_scope("example.com", ["*.example.com"])


def test_wildcard_over_bare_tld_rejected():
    # *.com TIDAK boleh meloloskan seluruh .com
    assert not _host_matches_scope("victim.com", ["*.com"])


# ───────────────────────── F-010: entri/host ber-port & URL ─────────────────────────
def test_entry_with_scheme_and_port_matches():
    assert _host_matches_scope("app.target.com", ["https://app.target.com:8443"])


def test_host_with_port_matches_bare_entry():
    assert _host_matches_scope("app.target.com:8443", ["app.target.com"])


def test_trailing_dot_fqdn_matches():
    assert _host_matches_scope("app.target.com.", ["app.target.com"])


# ───────────────────────── higiene ─────────────────────────
def test_empty_scope_blocks():
    assert not _host_matches_scope("app.target.com", [])
    assert not _host_matches_scope("app.target.com", None)


def test_empty_entries_ignored():
    assert not _host_matches_scope("app.target.com", ["", "   "])
