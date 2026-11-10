# JupyHop Development Guide

> **Status: M0–M6 local and GitHub CI acceptance passed.** SSH diagnostics, existing-server access, managed
> lifecycle/reconnection, profiles, multi-host inventory and archive ship.
> Real Unix account isolation and test-fixture cleanup are verified. OS logout
> policy, physical reboot and wider compatibility are bounded in the reports.
> See the milestone reports below for exact acceptance evidence and limits.
> The [0.2.0 operational stabilization candidate](22-02-stabilization.md) is prepared,
> with [observed progress](23-02-stabilization-evidence.md) for real-site,
> native SSH passwords/keys, endurance and installed-upgrade acceptance.
> [Conda distribution status](31-03-conda-publication.md) is tracked separately;
> no PyPI publication is included.
> Published **0.3.0** adds the post-pilot session/diagnostic UX. Its
> [implementation acceptance](30-03-implementation.md) and
> [Conda publication](31-03-conda-publication.md) retain their exact source and artifact identities.

JupyHop is a lightweight, SSH-native tool to launch, discover, manage, and reconnect to remote Jupyter sessions without deploying JupyterHub.

## Documents

1. [Product scope](01-product-scope.md) — audiences, workflows, MVP and non-goals
2. [Architecture](02-architecture.md) — responsibilities, components, state and execution
3. [CLI and configuration](03-cli-and-configuration.md) — proposed interface and settings
4. [Security and reliability](04-security-and-reliability.md) — threat model and failure handling
5. [Testing and quality](05-testing-and-quality.md) — tests, CI and release requirements
6. [Roadmap](06-roadmap.md) — sequential milestones and acceptance criteria
7. [Decisions](07-decisions.md) — agreed constraints and unresolved questions
8. [Scenario catalogue](08-scenarios-and-acceptance.md) — real network, user and failure cases with acceptance gates
9. [Session lifecycle and authentication](09-session-lifecycle-and-auth.md) — independent lifetimes, discovery, reconnection and process-manager choices
10. [Remote runtime and protocol](10-remote-runtime-and-protocol.md) — bootstrap, helper alternatives, schema and version compatibility
11. [Discovery and connectivity](11-discovery-and-connectivity.md) — detection, routing, tunnels, IPv6, URLs and authentication limitations
12. [User experience](12-user-experience.md) — low-configuration workflow, CLI selection, diagnosis and advanced use

## Product promise

From an authorized computer, reconnect to your own Jupyter session running on an SSH-accessible remote host, without remembering ports or manually managing tunnels.

## Principles

- Reuse OpenSSH aliases, keys, known hosts, and ProxyJump.
- Keep notebooks, kernels, data, and Python environments on the remote host.
- Require no central, always-on JupyHop service for the initial version.
- Preserve Jupyter authentication and remote OS permissions.
- Keep remote sessions alive across client disconnections.
- Avoid hard-coded lab hostnames, IPs, or sensitive configuration.
- Prefer standard components and a narrow scope over reimplementing JupyterHub.

## Definition of the first useful release

A user can discover and open an already-running, authorized Jupyter Server over SSH, without manual forwarding; then start a managed Jupyter session, disconnect, reconnect from another authorized client, list sessions, and explicitly stop a managed session. Discovery is best-effort and must never imply cross-user visibility or control. Local ports are allocated as needed; remote servers remain loopback-only and authenticated.

JupyHop is developed by UIBCDF and is licensed under the [MIT License](../LICENSE).

The MVP's nonnegotiable workflows are an existing-server open through ProxyJump (M2) and a managed-server restart-free reconnect from another client (M4). Run M0 feasibility spikes before freezing helper, discovery, token handoff, process-manager, and tunnel designs.

This directory is the project's design source of truth. Update specifications and decisions when findings from prototypes change the plan.

## Milestone evidence

- [M0 validation and ADR](13-m0-validation.md): isolated feasibility experiments,
  selected baseline, and explicit deferred evidence.
- [Acceptance ledger](14-acceptance-ledger.md): every scenario's release gate and
  test target; feasibility is distinct from shipped acceptance.
- [M1 foundations](15-m1-foundations.md): implemented CLI/transport/protocol,
  tests, packaging and limitations.
- [M2 existing-server access](16-m2-existing-servers.md): discovery, verified
  forwarding, normal Jupyter login, browser/Conda tests and remaining limits.
- [M3 managed launch](17-m3-managed-launch.md): private tmux, native password auth,
  versioned per-host state, launch readiness/failures and M4 boundaries.
- [M4 lifecycle and reconnection](18-m4-lifecycle.md): pinned graceful stop,
  interrupted requests, independent clients/browser kernel continuity, legacy
  runners, four-version results and OS/cleanup limits.
- [M5 scientific and multi-host workflows](19-m5-scientific-workflows.md): local
  profiles, route inventory, simultaneous scientific kernels, safe archive/name
  reuse and two real Unix accounts; privileged test-fixture instructions.
- [M6 beta readiness](20-m6-beta-readiness.md): native server-version evidence,
  internal security review, interrupted probe/input/atomic-read hardening,
  sustained data/authentication gates and reviewed unpublished beta artifacts.
- [M6 GitHub CI follow-up](21-m6-github-ci.md): direct pushes to main, deterministic
  background-computation acceptance, complete hosted-runner matrix, actual account
  cleanup and independent CI artifact/source/checksum verification.
- [0.2.0 operational stabilization](22-02-stabilization.md): scoped acceptance
  gates, SSH/OS support decisions, safe real-site pilot and installed-client
  upgrade evidence and the explicit boundaries for pre-1.0 stabilization.
- [0.2.0 evidence](23-02-stabilization-evidence.md): observed site workflows,
  stale-metadata correction, native SSH terminal authentication and exact limits.
- [Conda distribution](24-conda-publication.md): shared UIBCDF actions, exact-file
  staging/installed qualification/promotion, Linux support and publication evidence.
- [Public documentation](25-public-documentation.md): Sphinx/MyST guides, current CLI
  reference, browser/link acceptance and Pages artifact deployment.
- [Documentation review](26-documentation-review.md): remote onboarding, JSON/state
  contracts, client updates, executable examples and observed publication checks.
- [Documentation precision](27-documentation-precision.md): isolated Python,
  observation/registry scope, multi-kernel ownership and continuous example checks.
- [Physical home-client pilot](28-02-physical-client-pilot.md): operator-observed
  managed/manual access through a real gateway, same-kernel recovery, concurrent
  servers, selected-only stop and explicit archival completion.
- [0.3.0 session UX proposal](29-03-session-ux-design.md): names/choosers,
  inventory/history visibility, confirmed stop-and-archive and actionable diagnosis;
  historical proposal, with the implemented contract recorded separately.
- [0.3.0 implementation](30-03-implementation.md): observed source acceptance,
  kept separate from the proposed contract and Conda publication.
- [0.3.0 Conda publication](31-03-conda-publication.md): exact qualified source,
  one archive, four installed clients, promotion and independent public receiving.
