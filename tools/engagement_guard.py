#!/usr/bin/env python3
"""
engagement_guard.py — lapisan enforcement teknis untuk prinsip
"authorization-before-testing" secara UNIVERSAL, lintas platform bug bounty.

Filosofi (lihat engagements/_template.yaml untuk detail):
  - Fail-closed by default: kalau tidak ada engagement yang cocok & authorized,
    BLOKIR. Tidak ada "izin diam-diam".
  - Field `authorized: true` di file YAML cuma NIAT tertulis; modul inilah yang
    benar-benar MENOLAK (raise/return False) bila syarat gate tidak lengkap,
    terlepas dari apa yang ditulis di file.
  - Semua tool lain (cdp_capture.py, cdp_probe.py, idor_analyzer.py, dst) WAJIB
    panggil require_authorized(host) di awal sebelum request pertama ke host itu.

Pemakaian sebagai modul:
    from engagement_guard import is_authorized, require_authorized

    ok, reason = is_authorized("target.example.com")
    if not ok:
        print(f"BLOCKED: {reason}")

    require_authorized("target.example.com")  # raise EngagementNotAuthorized bila gagal

Pemakaian CLI:
    python3 engagement_guard.py check <host>
    python3 engagement_guard.py list
"""

import sys
import glob
import os
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    print("FATAL: PyYAML belum terinstall. Jalankan: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ENGAGEMENTS_DIR = Path(__file__).resolve().parent.parent / "engagements"


class EngagementNotAuthorized(Exception):
    """Dilempar saat require_authorized() gagal — dipakai untuk fail-fast di tool lain."""
    pass


def _load_all_engagements():
    """Baca semua *.yaml di engagements/ kecuali _template.yaml. Return list of dict."""
    results = []
    if not ENGAGEMENTS_DIR.exists():
        return results
    for path in sorted(glob.glob(str(ENGAGEMENTS_DIR / "*.yaml"))):
        if os.path.basename(path).startswith("_"):
            continue  # skip _template.yaml dan file lain berawalan underscore
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            if data:
                data["_source_file"] = path
                results.append(data)
        except Exception as e:
            print(f"WARNING: gagal parse {path}: {e}", file=sys.stderr)
    return results


def _normalize_host(raw) -> str:
    """Normalisasi input/entri scope menjadi hostname murni: lowercase, tanpa skema,
    port, userinfo, slash, atau trailing dot. Mengembalikan '' bila tak ada host.

    Contoh:
      'https://App.Target.com:8443/x' -> 'app.target.com'
      '127.0.0.1:8099'                -> '127.0.0.1'
      'app.target.com.'               -> 'app.target.com'  (FQDN trailing-dot)
    """
    if raw is None:
        return ""
    s = str(raw).strip().lower().rstrip("/")
    if not s:
        return ""
    try:
        # Tambah '//' agar host:port tanpa skema pun terurai oleh urlparse
        # (.hostname membuang port, userinfo, dan kurung IPv6).
        host = urlparse(s if "://" in s else "//" + s).hostname or ""
    except Exception:
        host = ""
    if not host:
        # fallback konservatif bila urlparse gagal
        host = s.split("/")[0].split("@")[-1].split(":")[0]
    return host.rstrip(".")


def _host_matches_scope(host: str, scope_list) -> bool:
    """Cek apakah `host` cocok salah satu entri in_scope.

    Aturan (fail-closed):
      - Scope hanya menyempit KE BAWAH: sebuah entri mengotorisasi DIRINYA SENDIRI dan
        SUB-DOMAIN di bawahnya, TAPI TIDAK PERNAH domain induk/apex di atasnya.
      - Entri wildcard `*.example.com` mengotorisasi sub-domain saja (BUKAN apex
        `example.com`).
      - Pencocokan sufiks (sub-domain) HANYA berlaku untuk entri yang punya titik
        (domain nyata). Entri label-tunggal tanpa titik — mis. `com` (TLD) atau
        `*.com` — DITOLAK sebagai basis sub-domain (fail-OPEN); label-tunggal hanya
        boleh EXACT match (mis. `localhost`). Ini menutup kebocoran "in_scope: ['com']
        meloloskan seluruh .com".
      - Input & entri dinormalisasi (skema/port/userinfo/trailing-dot dibuang).
    """
    host = _normalize_host(host)
    if not host:
        return False
    for raw_entry in scope_list or []:
        entry = str(raw_entry).strip().lower()
        if not entry:
            continue
        wildcard = entry.startswith("*.")
        base = _normalize_host(entry[2:] if wildcard else entry)
        if not base:
            continue
        base_has_dot = "." in base
        if wildcard:
            # *.example.com -> hanya sub-domain; wajib base ber-titik (tolak *.com)
            if base_has_dot and host.endswith("." + base):
                return True
        else:
            if host == base:
                return True
            if base_has_dot and host.endswith("." + base):
                return True
    return False


def is_authorized(host: str):
    """
    Cek apakah request ke `host` diperbolehkan berdasarkan seluruh engagement.yaml
    yang ada. Fail-closed: default False kecuali ADA engagement yang eksplisit
    memenuhi SEMUA syarat berikut:
      1. gate.authorized == True di file
      2. decision.go_no_go == "go"  (bukan "pending" atau "no-go")
      3. gate.legal.written_authorization.present == True
      4. host cocok salah satu gate.scope.in_scope
      5. program.status == "active"  (bukan halted/paused/completed/draft)

    Return: (bool authorized, str reason)
    """
    # Normalisasi penuh: buang skema, port, userinfo, trailing-dot. Tanpa ini,
    # `check http://127.0.0.1:8099/` menghasilkan host '127.0.0.1:8099' yang TIDAK
    # cocok entri '127.0.0.1' (false-negative; arah aman, tapi membingungkan operator).
    host = _normalize_host(host)

    engagements = _load_all_engagements()
    if not engagements:
        return False, (
            "Tidak ada engagement.yaml ditemukan di engagements/. "
            "Fail-closed: semua target dianggap TIDAK authorized sampai ada "
            "engagement yang eksplisit mengizinkan."
        )

    candidates_checked = []
    for eng in engagements:
        src = eng.get("_source_file", "?")
        program_name = (eng.get("program") or {}).get("name", "?")
        status = (eng.get("program") or {}).get("status")
        decision = (eng.get("decision") or {}).get("go_no_go")
        gate = eng.get("gate") or {}
        authorized_flag = gate.get("authorized", False)
        legal = gate.get("legal") or {}
        written_auth = (legal.get("written_authorization") or {}).get("present")
        scope = gate.get("scope") or {}
        in_scope = scope.get("in_scope") or []
        exclusions_note = scope.get("exclusions") or []

        candidates_checked.append(f"{program_name} ({src}): status={status}, decision={decision}, authorized={authorized_flag}")

        if status != "active":
            continue
        if decision != "go":
            continue
        if not authorized_flag:
            continue
        if written_auth is not True:
            continue
        if not _host_matches_scope(host, in_scope):
            continue

        return True, (
            f"AUTHORIZED via engagement '{program_name}' ({src}). "
            f"Ingat exclusions yang tetap berlaku: {exclusions_note}"
        )

    detail = "\n  - ".join(candidates_checked) if candidates_checked else "(tidak ada)"
    return False, (
        f"Host '{host}' TIDAK cocok dengan engagement manapun yang aktif & authorized.\n"
        f"Engagement yang diperiksa:\n  - {detail}\n"
        f"Untuk mengizinkan: buat/copy dari engagements/_template.yaml, lengkapi GATE-0/GATE-1, "
        f"set program.status=active, decision.go_no_go=go, gate.authorized=true — "
        f"dan pastikan itu benar-benar keputusan MANUSIA, bukan asumsi agent."
    )


def require_authorized(host: str):
    """Sama seperti is_authorized(), tapi raise EngagementNotAuthorized bila gagal.
    Cocok dipakai di baris pertama tool aktif (cdp_probe, dst) untuk fail-fast."""
    ok, reason = is_authorized(host)
    if not ok:
        raise EngagementNotAuthorized(reason)
    return True


def _cli():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check":
        if len(sys.argv) < 3:
            print("Usage: engagement_guard.py check <host>")
            sys.exit(1)
        host = sys.argv[2]
        ok, reason = is_authorized(host)
        status = "✔ AUTHORIZED" if ok else "✘ BLOCKED"
        print(f"{status}: {host}\n{reason}")
        sys.exit(0 if ok else 1)

    elif cmd == "list":
        engagements = _load_all_engagements()
        if not engagements:
            print("Tidak ada engagement terdaftar.")
            return
        for eng in engagements:
            p = eng.get("program") or {}
            d = eng.get("decision") or {}
            g = eng.get("gate") or {}
            print(f"- {p.get('name', '?')} [{eng.get('_source_file')}]")
            print(f"    status={p.get('status')}  decision={d.get('go_no_go')}  authorized={g.get('authorized')}")
            print(f"    in_scope={((g.get('scope') or {}).get('in_scope'))}")
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
