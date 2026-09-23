# Legal-First Bug Bounty Framework

A small, platform-agnostic **governance framework** that enforces one rule for security
research and bug-bounty work: **authorization before testing — enforced in code, not just
in prose.**

It was built after a real engagement was halted because extensive technical tooling had
been prepared against a target *before* anyone verified written authorization or the
presence of a safe-harbor clause. The lesson: a gate that exists only as a paragraph gets
skipped under momentum; a gate that tools actually check does not.

> **Scope of this repository.** This repo publishes the *governance layer only* — the
> authorization gate, the engagement schema, and the role-separated agent definitions.
> The active testing tools and any engagement-specific data (captures, reports, NDAs,
> credentials) are intentionally **kept private** and are not part of this repository.

---

## Core principle

- **Authorization-before-testing.** An NDA is a confidentiality agreement, *not* permission
  to test. Permission (Rules of Engagement / program policy), and safe-harbor, are separate
  things and must each be verified explicitly.
- **Fail-closed.** With no matching, human-approved engagement, every target is treated as
  unauthorized. There is no "silent yes."
- **Human-only go/no-go.** No automated agent may authorize testing; that decision is always
  made and recorded by a person.
- **Minimal impact, minimal data. Stop when in doubt.**

## Components

| Path | What it is |
|---|---|
| `tools/engagement_guard.py` | The enforcement layer. `is_authorized(host)` / `require_authorized(host)`, fail-closed. Every active tool must call it before its first request to a target. CLI: `engagement_guard.py check <host>` / `list`. |
| `engagements/_template.yaml` | Universal, platform-agnostic engagement schema — one file per program/target. Records written-authorization status, safe-harbor verification, scope, and a master `authorized` flag that stays `false` until a human sets `go`. |
| `.claude/agents/*.md` | Five role-separated [Claude Code](https://claude.com/claude-code) sub-agents, one per phase, each constrained so no single role can both authorize and act. |

### The gate (fail-closed criteria)

`engagement_guard.is_authorized(host)` returns `True` only when some engagement file
explicitly satisfies **all** of:

1. `gate.authorized == true`
2. `decision.go_no_go == "go"` (a human decision)
3. `gate.legal.written_authorization.present == true`
4. `host` matches an entry in `gate.scope.in_scope`
5. `program.status == "active"`

The `authorized` flag in a YAML file is only *intent* — the guard is what enforces it, and
it refuses regardless of that flag if any condition above is unmet.

### The agent team (phase-gated, role-separated)

| Agent | Phase | Constraint |
|---|---|---|
| `legal-gate` | Legal / authorization | Reads NDA/ToS/policy, verifies safe-harbor, fills the engagement file — but may **never** set `go_no_go` to anything but `pending`. |
| `recon-scout` | Recon / surface mapping | Checks the guard first; maps, never exploits. |
| `vuln-tester` | Testing | Hard-blocked by `require_authorized()`; one probe per hypothesis; must mark findings `INCONCLUSIVE` honestly rather than round up or down. |
| `report-writer` | Reporting | Drafts a disclosure report; never submits it — always human-reviewed first. |
| `engagement-archivist` | Post-program | Cleanup and status lock-down; never deletes or sends anything without explicit human approval. |

## Usage

```bash
pip install -r requirements.txt

# Check whether a host is authorized (fail-closed):
python3 tools/engagement_guard.py check target.example.com

# List all registered engagements and their gate state:
python3 tools/engagement_guard.py list
```

To onboard a new target: copy `engagements/_template.yaml`, have a person verify the legal
and scope fields, and only then — as a human decision — set `decision.go_no_go: go` and
`gate.authorized: true`. The guard refuses anything less.

See [`examples/`](examples/) for a runnable walkthrough that shows the guard **blocking** a
target even when someone has already flipped `gate.authorized: true` in the file — because the
flag is only intent, and the guard enforces the rest.

## Notes

- The in-code documentation and agent prompts are written in **Indonesian**; this README
  summarizes them in English.
- Requires Python 3; install dependencies with `pip install -r requirements.txt`.

## Responsible use

This framework exists to keep security research **inside** the bounds of explicit
authorization and responsible disclosure. It contains no exploitation capability. Use it
only for testing you are authorized to perform.

## License

MIT — see [LICENSE](LICENSE).
