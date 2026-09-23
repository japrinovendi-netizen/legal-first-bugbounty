# Examples — the gate in action

This folder shows the authorization gate refusing to authorize a target, so you can
see the **fail-closed** behavior without setting anything up against a real host.

`demo-engagement.yaml` is a **fictional** example (target `demo.example.com`, a reserved
example domain per RFC 2606 — not a real system). It deliberately sets `gate.authorized: true`
in the file, yet the guard **still blocks it**, because the other required conditions
(`decision.go_no_go: go`, `program.status: active`, a verified written authorization) are not
met. The point: the flag in the file is only *intent* — the guard is what enforces.

## Try it

```bash
# From the repo root, copy the example into the live engagements/ folder:
cp examples/demo-engagement.yaml engagements/demo.yaml

# List what the guard sees:
python3 tools/engagement_guard.py list

# Ask whether the demo host is authorized:
python3 tools/engagement_guard.py check demo.example.com

# Clean up:
rm engagements/demo.yaml
```

## What you get (actual output)

```text
$ python3 tools/engagement_guard.py list
- Demo Program (CONTOH — bukan target nyata) [engagements/demo.yaml]
    status=draft  decision=pending  authorized=True
    in_scope=['demo.example.com']

$ python3 tools/engagement_guard.py check demo.example.com
✘ BLOCKED: demo.example.com
Host 'demo.example.com' TIDAK cocok dengan engagement manapun yang aktif & authorized.
Engagement yang diperiksa:
  - Demo Program (CONTOH — bukan target nyata) (engagements/demo.yaml): status=draft, decision=pending, authorized=True
Untuk mengizinkan: buat/copy dari engagements/_template.yaml, lengkapi GATE-0/GATE-1, set
program.status=active, decision.go_no_go=go, gate.authorized=true — dan pastikan itu benar-benar
keputusan MANUSIA, bukan asumsi agent.
```

Exit code is `1` (blocked), so the guard fails a script/tool the moment it is called against an
unauthorized host. A host with no engagement at all is blocked the same way — fail-closed by
default. Only when a human completes the legal/scope checks and sets `status: active`,
`go_no_go: go`, and a verified written authorization does `check` return `✔ AUTHORIZED` (exit `0`).

> Note: in-code comments are in Indonesian; see the top-level `README.md` for an English summary.
