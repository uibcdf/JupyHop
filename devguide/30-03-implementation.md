# 30 — 0.3.0 implementation and acceptance

Status: implementation in progress, following [29](29-03-session-ux-design.md).
The 0.2.0 physical pilot is closed in [28](28-02-physical-client-pilot.md).
No 0.3.0 publication or complete feature acceptance is claimed yet.

## Read-only managed inventory foundation

The new internal inventory RPC uses wire 1.5 independently of registry schema
1.0. It validates current private records/runner hashes, observes server state
without readiness writes and reads only allowlisted archive identity fields.
It never reads settings or kernel recovery contents for presentation.

Active results retain the 128-record bound. History is paged at 64 entries with
bounded offsets 0–4096 and a probe deadline. Only a complete initial page provides
an exact archive count; later or truncated pages remain explicitly partial.
Concurrent changes can alter directory enumeration between pages. Unknown or
unavailable inventory produces unknown counters, not zero. This introduces no
remote package, daemon, registry migration or archive mutation.

Observed on development Python 3.14.10: 21 focused unit tests pass, strict mypy
passes all 22 installed-source modules, and two disposable direct/ProxyJump SSH
integration cases pass. They cover live → stopped → archived observations,
record/runner byte preservation, private symlink boundaries, bounded history,
secret allowlisting, parser refusal and the unchanged 64 KiB RPC input bound.
No real workstation/session was used.

CLI selection/completion, actionable diagnosis, public documentation, installed
candidate qualification and four-Python hosted acceptance remain to be completed.
